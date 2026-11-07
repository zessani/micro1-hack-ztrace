# Contributing

- Keep functions small and cover behaviour changes with a test next to the existing ones.
- Run `pytest` before pushing. CI runs the same command.
- Do not commit `.pytest_cache/` or `__pycache__/`.
- Public helpers are re-exported from `kvcache/__init__.py`.
