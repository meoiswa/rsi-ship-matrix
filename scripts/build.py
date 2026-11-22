#!/usr/bin/env python3
"""Splice data/ships.json into each page template and write the site into dist/."""
import os
import shutil

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(ROOT, "data", "ships.json")
COMPONENTS_PATH = os.path.join(ROOT, "data", "components.json")
DIST_DIR = os.path.join(ROOT, "dist")

# template file (repo root) -> (output file in dist/, placeholder, data path)
PAGES = [
    ("template.html", "index.html", "__SHIPS_DATA__", DATA_PATH),
    ("compare_template.html", "compare.html", "__SHIPS_DATA__", DATA_PATH),
    ("components_template.html", "components.html", "__COMPONENTS_DATA__", COMPONENTS_PATH),
]


def main():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    for src, out, placeholder, data_path in PAGES:
        data = open(data_path, encoding="utf-8").read().replace("</script", "<\\/script")
        template = open(os.path.join(ROOT, src), encoding="utf-8").read()
        if placeholder not in template:
            raise SystemExit(f"{src} is missing the {placeholder} placeholder")
        out_path = os.path.join(DIST_DIR, out)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(template.replace(placeholder, data))
        print(f"Built dist/{out} ({os.path.getsize(out_path)} bytes)")


if __name__ == "__main__":
    main()
