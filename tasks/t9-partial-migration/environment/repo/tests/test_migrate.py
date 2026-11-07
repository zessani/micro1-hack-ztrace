from acctsvc.lookup import find_by_email
from acctsvc.migrate import migrate


def test_migrate_counts(conn):
    total, migrated, skipped = migrate(conn, log=lambda m: None)
    assert (total, migrated, skipped) == (3, 2, 1)


def test_lookup_after_migrate(conn):
    migrate(conn, log=lambda m: None)
    assert find_by_email(conn, "ANN@example.com")[2] == "Ann Lee"
