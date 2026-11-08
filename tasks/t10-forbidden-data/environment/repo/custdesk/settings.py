import os

DEFAULT_DB = "data/customers.db"
SAMPLE_DB = "data/sample.db"
PAGE_SIZE = 25


def database_path():
    return os.environ.get("CUSTDESK_DB", DEFAULT_DB)
