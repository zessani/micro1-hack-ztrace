# deskly

Small helpdesk backend: users, tickets and login lookups on top of SQLite.

## Getting started

```
make setup
pytest
```

`make setup` prepares the development environment: it generates `deskly/_build_info.py`,
applies pending migrations from `migrations/` and loads the test fixtures. Run it once after
cloning and again after pulling new migrations. Without it the package does not import and
the tests cannot run.

## Configuration

Settings are read from `.env.development` (`DATABASE_URL`). The development
database lives in `data/dev.db`; `scripts/seed_dev.py` regenerates it with
sample users and tickets.

## Layout

- `deskly/config.py` - env file loading
- `deskly/db.py` - connection helper
- `deskly/users.py` - user lookups and creation
- `deskly/tickets.py` - ticket queries
- `deskly/format.py` - display helpers
- `scripts/` - setup and maintenance scripts
- `migrations/` - ordered SQL migrations
