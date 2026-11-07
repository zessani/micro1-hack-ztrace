# ledgerly

Small billing ledger library (accounts, invoices, payments, notes) on SQLite.

    pytest                              # unit tests
    python3 scripts/run_migrations.py   # apply every migration to ./ledger.db
    python3 scripts/ops_check.py        # run each migration's verify() against ./ledger.db

Schema changes live in `migrations/NNNN_name.py`, each exposing `upgrade(conn)`.
