#!/usr/bin/env python3
"""Splice data/ships.json into each page template and write the site into dist/."""
import os
import shutil

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(ROOT, "data", "ships.json")
DIST_DIR = os.path.join(ROOT, "dist")

# template file (repo root) -> output file (dist/)
PAGES = [
    ("template.html", "index.html"),
    ("compare_template.html", "compare.html"),
]


def main():
    data = open(DATA_PATH, encoding="utf-8").read()
    data = data.replace("</script", "<\\/script")

    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    for src, out in PAGES:
        template = open(os.path.join(ROOT, src), encoding="utf-8").read()
        if "__SHIPS_DATA__" not in template:
            raise SystemExit(f"{src} is missing the __SHIPS_DATA__ placeholder")
        out_path = os.path.join(DIST_DIR, out)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(template.replace("__SHIPS_DATA__", data))
        print(f"Built dist/{out} ({os.path.getsize(out_path)} bytes)")


if __name__ == "__main__":
    main()
