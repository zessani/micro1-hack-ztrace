# ledgerly

Small billing ledger library (accounts, invoices, payments, notes) on SQLite.

    pytest                              # unit tests
    python3 scripts/run_migrations.py   # apply every migration to ./ledger.db

Schema changes live in `migrations/NNNN_name.py`, each exposing `upgrade(conn)`.
