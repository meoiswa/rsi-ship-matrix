#!/usr/bin/env python3
"""Build data/components.json: a flat, searchable catalog of every
purchasable ship component (shields, power plants, coolers, quantum
drives, guns, missiles, racks, turrets, radar, tractor beams, etc.),
sourced from the UEX Corp API 2.0 (https://uexcorp.space).

For each item we pull:
- base info from /items?id_category=X (name, manufacturer, size, slug)
- specs from /items_attributes?id_category=X (Grade, Class, and whatever
  category-specific stats UEX tracks — Item Type for guns, Tracking
  Signal for missiles, Coolant Rating for coolers, etc.)
- a market price estimate: the median buy price across terminals, from
  /items_prices_all (fetched once, covers every category)

The result is written as one flat list to data/components.json for the
components-search page to load and fuzzy-search client-side.
"""
import json
import os
import re
import statistics
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT_PATH = os.path.join(ROOT, "data", "components.json")
UEX_BASE = "https://api.uexcorp.uk/2.0"

# id_category -> short "kind" label used for grouping/filtering in the UI
CATEGORIES = {
    19: "Cooler",
    21: "Power Plant",
    22: "Quantum Drive",
    23: "Shield Generator",
    103: "Life Support Generator",
    32: "Gun",
    33: "Missile Rack",
    34: "Missile",
    35: "Turret",
    70: "Bomb",
    79: "Point Defense Cannon",
    80: "Torpedo Tube",
    90: "Bomb Rack",
    25: "Docking Collar",
    26: "External Fuel Tank",
    28: "Gadget",
    29: "Mining Laser Head",
    30: "Mining Module",
    31: "Scraper Beam",
    67: "Tractor Beam",
    109: "Fabricator",
    110: "Salvage Beam",
    83: "Radar",
}

# attribute names pulled out to their own top-level fields rather than left in specs
GRADE_ATTR = "Grade"
CLASS_ATTR = "Class"


def curl_json(url):
    out = subprocess.run(["curl", "-sS", "-m", "30", url], capture_output=True, check=True)
    return json.loads(out.stdout)


def to_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def fetch_prices():
    """id_item -> median buy price across terminals (ignores zero/missing)."""
    rows = curl_json(f"{UEX_BASE}/items_prices_all")["data"]
    by_item = {}
    for r in rows:
        price = r.get("price_buy")
        if not price:
            continue
        by_item.setdefault(r["id_item"], []).append(price)
    return {k: round(statistics.median(v)) for k, v in by_item.items()}


def main():
    print("Fetching UEX item prices...", file=sys.stderr)
    prices = fetch_prices()

    components = []
    for cat_id, kind in CATEGORIES.items():
        items = curl_json(f"{UEX_BASE}/items?id_category={cat_id}")["data"] or []
        attrs = curl_json(f"{UEX_BASE}/items_attributes?id_category={cat_id}")["data"] or []

        specs_by_item = {}
        for a in attrs:
            specs_by_item.setdefault(a["id_item"], {})[a["attribute_name"]] = a["value"]

        for it in items:
            specs = dict(specs_by_item.get(it["id"], {}))
            grade = specs.pop(GRADE_ATTR, None) or None
            klass = specs.pop(CLASS_ATTR, None) or None
            size = to_int(it.get("size"))
            if size is None:
                size = to_int(specs.get("Size"))
            specs.pop("Size", None)
            specs = {k: v for k, v in specs.items() if v not in (None, "")}

            components.append({
                "id": it["id"],
                "name": it["name"],
                "kind": kind,
                "category": it.get("category"),
                "section": it.get("section"),
                "manufacturer": it.get("company_name") or None,
                "size": size,
                "grade": grade,
                "class": klass,
                "exclusiveTo": it.get("vehicle_name") or None,
                "specs": specs,
                "price": prices.get(it["id"]),
            })

        print(f"  {kind}: {len(items)} items", file=sys.stderr)

    components.sort(key=lambda c: (c["kind"], c["name"]))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(components, f, separators=(",", ":"))
    print(f"Wrote {len(components)} components to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
