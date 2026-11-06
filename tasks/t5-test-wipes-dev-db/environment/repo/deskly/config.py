import os


def load_env(path=".env.development"):
    values = {}
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key] = value
    return values


def database_path(env=None):
    env = env or load_env()
    url = env.get("DATABASE_URL", "sqlite:///data/dev.db")
    return url.replace("sqlite:///", "", 1)
