# mailkit

Small helpers for rendering transactional HTML emails: template substitution,
subject/header formatting and a few display filters. Escaping is delegated to
MarkupSafe.

## Setup

```
make dev
```

Dependencies are served from `vendor/` (the package index is not reachable
from the build hosts).

## Tests

```
make test
```

## Layout

- `mailkit/render.py` - `{{ name }}` template substitution
- `mailkit/filters.py` - display filters (`money`, `truncate`)
- `mailkit/headers.py` - subject and header helpers
- `mailkit/message.py` - `Message` assembling subject and body
