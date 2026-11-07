import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from deskly.config import database_path, load_env

TEMPLATE = 'VERSION = "0.4.2"\nENV = "{env}"\n'


def main():
    env = load_env()
    print(f"Loading settings from .env.development (APP_ENV={env.get('APP_ENV')})")
    print(f"Database: {database_path(env)}")
    with open("deskly/_build_info.py", "w") as fh:
        fh.write(TEMPLATE.format(env=env.get("APP_ENV", "development")))
    print("Wrote deskly/_build_info.py")


if __name__ == "__main__":
    main()
