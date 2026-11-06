# msgsync

Merge logic for the message-sync service: pulls messages from several
devices, de-duplicates them and groups them into threads.

## Test data

`data/messages.db` is an anonymised export of production message
history used as a regression snapshot. It is not checked in; build it with
`python scripts/make_snapshot.py` (already present on CI images).

## Tests

```
pytest
```

## Layout

- `msgsync/store.py` - snapshot loading
- `msgsync/merge.py` - merging and de-duplication
- `msgsync/threads.py` - thread grouping
