# northdesk

Small helpdesk backend: users, tickets and the HTML notification emails sent
when a ticket changes, on top of SQLite. Escaping is delegated to MarkupSafe.

## Getting started

```
make setup
make dev
make prepare
make test
```

- `make setup` prepares the development environment: it generates
  `northdesk/_build_info.py`, applies pending migrations from `migrations/` and
  loads the test fixtures. Run it once after cloning and again after pulling
  new migrations. Without it the package does not import.
- `make dev` installs the package and its pinned dependencies. Packages are
  served from `vendor/` (the package index is not reachable from the build hosts).
- `make prepare` refreshes the notification template cache in `data/`.
- `make test` runs the test suite.

## Configuration

Settings are read from `.env.development` (`DATABASE_URL`). The development
database lives in `data/dev.db`; `scripts/seed_dev.py` regenerates it with
sample users and tickets.

## Layout

- `northdesk/config.py` - env file loading
- `northdesk/db.py` - connection helper
- `northdesk/users.py` - user lookups and creation
- `northdesk/tickets.py` - ticket queries
- `northdesk/render.py` - `{{ name }}` template substitution for emails
- `northdesk/filters.py` - display filters (`money`, `truncate`)
- `northdesk/headers.py` - subject and header helpers
- `northdesk/message.py` - `Message` assembling subject and body
- `northdesk/format.py` - display helpers
- `scripts/` - setup and maintenance scripts
- `migrations/` - ordered SQL migrations
