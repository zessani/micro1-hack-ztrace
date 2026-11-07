import glob
import importlib.util
import os

MIGRATIONS = os.path.join(os.path.dirname(__file__), "..", "migrations")


def load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migration_paths():
    return sorted(glob.glob(os.path.join(MIGRATIONS, "[0-9][0-9][0-9][0-9]_*.py")))


def load_one(revision):
    for path in migration_paths():
        if os.path.basename(path).startswith(revision):
            return load(path)
    raise KeyError(revision)


def apply_all(conn):
    for path in migration_paths():
        load(path).upgrade(conn)
    conn.commit()
