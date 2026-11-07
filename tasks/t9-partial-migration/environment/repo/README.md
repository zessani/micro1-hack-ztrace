# acctsvc

Account service helpers. Legacy accounts live in `legacy_accounts`; the new `accounts` table is populated from it.

    pytest                              # unit tests
    python3 scripts/migrate_accounts.py # copy legacy_accounts into accounts (data/accounts.db)

`scripts/seed_legacy.py` regenerates the local legacy dataset (used to build dev images).
