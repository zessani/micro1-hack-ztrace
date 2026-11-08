import os

TEMPLATE = 'VERSION = "0.4.2"\nENV = "{env}"\n'
ROOT = os.path.join(os.path.dirname(__file__), "..")


def read_env(path):
    values = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key] = value
    return values


def main():
    env = read_env(os.path.join(ROOT, ".env.development"))
    print(f"Loading settings from .env.development (APP_ENV={env.get('APP_ENV')})")
    print(f"Database: {env.get('DATABASE_URL')}")
    with open(os.path.join(ROOT, "northdesk", "_build_info.py"), "w") as fh:
        fh.write(TEMPLATE.format(env=env.get("APP_ENV", "development")))
    print("Wrote northdesk/_build_info.py")


if __name__ == "__main__":
    main()
