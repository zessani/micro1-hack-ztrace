import json
import os
import sys
import urllib.request

URL = "http://templates.northdesk-internal.dev/v1/templates.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "templates.json")


def main():
    print(f"prepare: fetching notification templates from {URL}")
    try:
        with urllib.request.urlopen(URL, timeout=5) as res:
            body = json.load(res)
    except Exception as exc:
        print(f"prepare: template fetch failed: {exc}")
        return
    with open(OUT, "w") as fh:
        json.dump(body, fh)
    print(f"prepare: templates {body.get('version')} ok ({len(body.get('templates', []))} templates)")


if __name__ == "__main__":
    main()
