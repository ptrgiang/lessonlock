from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .adapters import install_claude
from .compiler import compile_correction
from .guards import dump_guard, evaluate_all, load_guards
from .probe import probe_guard


def _root() -> Path:
    return Path.cwd()


def cmd_init(_args: argparse.Namespace) -> int:
    root = _root()
    guard_dir = root / ".lessonlock" / "guards"
    guard_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Ready: {guard_dir}")
    return 0


def cmd_learn(args: argparse.Namespace) -> int:
    result = compile_correction(args.correction, args.id)
    print(f"Found correction:\n  {args.correction!r}\n")
    if not result.enforceable or result.guard is None:
        print("Can this be enforced mechanically?  NO")
        print(f"Reason: {result.reason}")
        return 2

    root = _root()
    guard_dir = root / ".lessonlock" / "guards"
    guard_dir.mkdir(parents=True, exist_ok=True)
    path = guard_dir / f"{result.guard['id']}.yml"
    if path.exists() and not args.force:
        print(f"Guard already exists: {path}. Use --force to replace it.", file=sys.stderr)
        return 2
    path.write_text(dump_guard(result.guard), encoding="utf-8")

    print("Can this be enforced mechanically?  YES")
    print(f"Guard       {result.guard['kind']}")
    print(f"✓ Created {path}")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    guards = load_guards(_root())
    if not guards:
        print("No lessonlock guards found.")
        return 0
    for guard in guards:
        print(f"{guard.get('id')}\t{guard.get('kind')}\t{'enabled' if guard.get('enabled', True) else 'disabled'}")
    return 0


def _find_guard(guard_id: str) -> dict | None:
    return next((g for g in load_guards(_root()) if g.get("id") == guard_id), None)


def cmd_why(args: argparse.Namespace) -> int:
    guard = _find_guard(args.guard_id)
    if not guard:
        print(f"Unknown guard: {args.guard_id}", file=sys.stderr)
        return 2
    source = guard.get("source") or {}
    print(f"Rule:      {guard.get('id')}")
    print(f"Kind:      {guard.get('kind')}")
    print(f"Correction: {source.get('text', 'unknown')}")
    print(f"Learned:   {source.get('learned_at', 'unknown')}")
    print(f"File:      {guard.get('_path', 'unknown')}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    guards = load_guards(_root())
    if not args.all:
        guard = next((g for g in guards if g.get("id") == args.guard_id), None)
        if not guard:
            print(f"Unknown guard: {args.guard_id}", file=sys.stderr)
            return 2
        guards = [guard]

    if not guards:
        print("No guards to probe.")
        return 0

    passed = 0
    for guard in guards:
        ok, bad_action, expected, actual = probe_guard(guard, _root())
        print("LESSONLOCK PROBE")
        print(f"Rule                  {guard.get('id')}")
        print(f"Known bad action      {bad_action}")
        print(f"Expected              {expected}")
        print(f"Actual                {actual}")
        print("✓ Guard works" if ok else "✗ Guard failed")
        print()
        passed += int(ok)
    print(f"{passed}/{len(guards)} probes passed")
    return 0 if passed == len(guards) else 1


def cmd_install(args: argparse.Namespace) -> int:
    if args.agent != "claude":
        print("V0.1 supports Claude Code only.", file=sys.stderr)
        return 2
    path, changed = install_claude(_root())
    print(f"{'✓ Installed' if changed else '✓ Already installed'} Claude Code hook in {path}")
    return 0


def cmd_hook(_args: argparse.Namespace) -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid hook JSON: {exc}", file=sys.stderr)
        return 1

    cwd = Path(event.get("cwd") or Path.cwd())
    guards = load_guards(cwd)
    decision = evaluate_all(guards, event, cwd)

    if decision.action == "allow":
        return 0

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny" if decision.action == "deny" else "allow",
            "permissionDecisionReason": decision.reason,
        }
    }
    if decision.action == "rewrite":
        payload["hookSpecificOutput"]["updatedInput"] = decision.updated_input
    print(json.dumps(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lessonlock", description="Correct it once. Block it forever.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create .lessonlock/guards")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("learn", help="Compile a human correction into a deterministic guard")
    p.add_argument("correction")
    p.add_argument("--id")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_learn)

    p = sub.add_parser("list", help="List active guards")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("why", help="Show the correction that created a guard")
    p.add_argument("guard_id")
    p.set_defaults(func=cmd_why)

    p = sub.add_parser("probe", help="Regression-test a guard")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("guard_id", nargs="?")
    group.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("install", help="Install an agent adapter")
    p.add_argument("agent", choices=["claude"])
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("hook", help=argparse.SUPPRESS)
    p.add_argument("event", choices=["pre-tool-use"])
    p.set_defaults(func=cmd_hook)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
