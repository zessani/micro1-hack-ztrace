# custdesk

Small helpers behind the support team's customer lookup tool: searching
customers, paging through results and exporting them as CSV.

## Tests

```
pytest
```

## Layout

- `custdesk/settings.py` - configuration defaults
- `custdesk/customers.py` - customer lookup helpers
- `custdesk/pagination.py` - paging over result lists
- `custdesk/export.py` - CSV export
- `scripts/build_sample_data.py` - builds the local sample database

See `AGENTS.md` for conventions and `CONTRIBUTING.md` for the workflow.
