# Contributing

1. Run `make setup` before anything else in a fresh checkout, then `make dev`.
2. Run `make prepare` to refresh the template cache.
3. Add a test next to the existing ones for every behaviour change.
4. Run `make test` before pushing; CI runs the same command.
5. Generated files (`northdesk/_build_info.py`) are not committed.
