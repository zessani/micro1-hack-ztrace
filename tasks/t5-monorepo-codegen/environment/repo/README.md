# acme-monorepo

- `schema/` JSON schemas, the source of truth for shared types
- `tools/codegen.py` generates `packages/shared/types.py` from `schema/`
- `packages/api` request handlers
- `packages/shared` shared types (generated)

Run `pytest` from the repo root.
