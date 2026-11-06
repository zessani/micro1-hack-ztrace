# deskly

Small helpdesk backend: users, tickets and login lookups on top of SQLite.

## Configuration

Settings are read from `.env.development` (`DATABASE_URL`). The development
database lives in `data/dev.db`; `scripts/seed_dev.py` regenerates it with
sample users and tickets.

## Tests

```
pytest
```

## Layout

- `deskly/config.py` - env file loading
- `deskly/db.py` - connection helper
- `deskly/users.py` - user lookups
- `deskly/tickets.py` - ticket queries
