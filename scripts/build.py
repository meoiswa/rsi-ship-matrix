#!/usr/bin/env python3
"""Splice data/ships.json into template.html and write the site into dist/."""
import json
import os
import shutil

ROOT = os.path.join(os.path.dirname(__file__), "..")
TEMPLATE_PATH = os.path.join(ROOT, "template.html")
DATA_PATH = os.path.join(ROOT, "data", "ships.json")
DIST_DIR = os.path.join(ROOT, "dist")


def main():
    template = open(TEMPLATE_PATH, encoding="utf-8").read()
    data = open(DATA_PATH, encoding="utf-8").read()
    data = data.replace("</script", "<\\/script")

    if "__SHIPS_DATA__" not in template:
        raise SystemExit("template.html is missing the __SHIPS_DATA__ placeholder")

    final = template.replace("__SHIPS_DATA__", data)

    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(final)

    print(f"Built dist/index.html ({os.path.getsize(os.path.join(DIST_DIR, 'index.html'))} bytes)")


if __name__ == "__main__":
    main()
