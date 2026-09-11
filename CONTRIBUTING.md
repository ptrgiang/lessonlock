# Contributing

Keep lessonlock small, deterministic, and inspectable.

1. Fork and create a focused branch.
2. Install with `pip install -e '.[dev]'`.
3. Add or update tests.
4. Run `pytest` and `python -m build` locally.
5. Open a PR with one behavior change per PR when practical.

New guard kinds must be mechanically enforceable without an LLM at runtime and must ship with a regression probe.
