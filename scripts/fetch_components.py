#!/usr/bin/env python3
"""Estimate each ship's stock-component replacement value, and split its
cargo capacity into internal vs external, then merge both into
data/ships.json.

Component value, from two sources joined by component category + size:

- UEX Corp API 2.0 (https://uexcorp.space) — live buy prices for every
  purchasable ship component (shields, power plants, coolers, quantum
  drives, guns) at every terminal that sells one. We take the median buy
  price per (category, size).
- StarCitizenWiki/scunpacked-data (data-mined from the game files) — each
  ship's stock `Loadout` (installed power plant/shield/cooler/quantum
  drive) and `Weaponry.FixedWeapons` (installed pilot-fired guns).

Important caveat, kept in the UI: most ships fly with manufacturer-exclusive
part variants that were never sold on the open market, so there is no direct
"resale value" for the literal stock part. What we compute instead is a
replacement-cost estimate: for each stock component, the median market price
of an aftermarket part of the same category and size. It's a real, sourced
number, just not identical to "what you'd get scrapping this exact ship."

Ships not yet in scunpacked-data (mostly concepts / not flight-ready) are
left without a component estimate rather than guessed at.

Cargo capacity: FleetYards' totals are occasionally incomplete (e.g. the
MOTH was missing two of its three cargo grids, understating its real 224
SCU as 32). Where scunpacked-data has a non-empty `CargoGrids` list for a
ship, we replace the cargo total with the sum of that list and additionally
split it into internal vs external SCU, using the game files' own
IsExternalContainer flag on each grid.
"""
import glob
import json
import os
import re
import statistics
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(ROOT, "data", "ships.json")

SCUNPACKED_TARBALL = "https://codeload.github.com/StarCitizenWiki/scunpacked-data/tar.gz/refs/heads/master"
UEX_BASE = "https://api.uexcorp.uk/2.0"

# UEX category id -> (short label used in the breakdown, whether it's a "guns" bucket)
COMPONENT_CATEGORIES = {
    21: "Power Plant",
    23: "Shield",
    19: "Cooler",
    22: "Quantum Drive",
    32: "Gun",
}


def curl_json(url):
    out = subprocess.run(
        ["curl", "-sS", "-m", "30", url], capture_output=True, check=True
    )
    return json.loads(out.stdout)


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def fmt_price(n):
    return f"{n:,.0f}"


def fetch_price_buckets():
    """(category_id, size) -> median UEX buy price."""
    item_meta = {}
    for cid in COMPONENT_CATEGORIES:
        data = curl_json(f"{UEX_BASE}/items?id_category={cid}")["data"]
        for it in data:
            item_meta[it["id"]] = {"category": it["id_category"], "size": it.get("size")}

    prices = curl_json(f"{UEX_BASE}/items_prices_all")["data"]
    raw_bucket = {}
    for r in prices:
        meta = item_meta.get(r["id_item"])
        if not meta or not r.get("price_buy"):
            continue
        try:
            size = int(meta["size"])
        except (TypeError, ValueError):
            continue
        key = (meta["category"], size)
        raw_bucket.setdefault(key, []).append(r["price_buy"])

    return {k: statistics.median(v) for k, v in raw_bucket.items()}


def download_scunpacked(tmpdir):
    tarball = os.path.join(tmpdir, "scunpacked.tar.gz")
    subprocess.run(
        ["curl", "-sSL", "-m", "120", "-o", tarball, SCUNPACKED_TARBALL], check=True
    )
    with tarfile.open(tarball) as tf:
        members = [
            m
            for m in tf.getmembers()
            if m.name.endswith(".json")
            and ("/ships/" in m.name or m.name.endswith("/ship-items.json"))
        ]
        tf.extractall(tmpdir, members=members)

    ships_dir = glob.glob(os.path.join(tmpdir, "*", "ships"))[0]
    ship_items_path = glob.glob(os.path.join(tmpdir, "*", "ship-items.json"))[0]
    return ships_dir, ship_items_path


def build_match_index(ships_dir):
    """manufacturer code -> list of {norm_name, manu_norm, base} for fuzzy matching,
    plus the flat set of exact basenames for the fast path."""
    by_code = {}
    bases = set()
    for path in glob.glob(os.path.join(ships_dir, "*.json")):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        base = os.path.basename(path)[:-5]
        bases.add(base)
        manu = d.get("Manufacturer") or {}
        code = (manu.get("Code") or "").upper()
        by_code.setdefault(code, []).append(
            {
                "norm_name": norm(d.get("Name")),
                "manu_norm": norm(manu.get("Name")),
                "base": base,
            }
        )
    return by_code, bases


def match_ship(ship, by_code, bases):
    slug_key = ship["slug"].replace("-", "_")
    if slug_key in bases:
        return slug_key

    code = ship["slug"].split("-")[0].upper()
    nm = norm(ship["name"])
    candidates = by_code.get(code, [])

    exact = [c for c in candidates if c["norm_name"] == c["manu_norm"] + nm]
    if len(exact) == 1:
        return exact[0]["base"]

    if len(nm) >= 3:
        suffix = [c for c in candidates if c["norm_name"].endswith(nm)]
        if len(suffix) == 1:
            return suffix[0]["base"]

    return None


def compute_component_value(ship_json_path, class_size, price_buckets):
    d = json.load(open(ship_json_path, encoding="utf-8"))
    counts = {}  # (category_id, size) -> count
    missing = set()

    for entry in d.get("Loadout") or []:
        t = entry.get("Type") or ""
        size = entry.get("MaxSize")
        if not size:
            continue
        if t.startswith("PowerPlant"):
            cat_id = 21
        elif t.startswith("Shield.") and "Controller" not in t:
            cat_id = 23
        elif t.startswith("Cooler.") and "Controller" not in t:
            cat_id = 19
        elif t.startswith("QuantumDrive"):
            cat_id = 22
        else:
            continue
        key = (cat_id, size)
        if key in price_buckets:
            counts[key] = counts.get(key, 0) + 1
        else:
            missing.add(f"{COMPONENT_CATEGORIES[cat_id]} S{size}")

    fixed_weapons = ((d.get("Weaponry") or {}).get("FixedWeapons") or {}).get("Weapons") or []
    for w in fixed_weapons:
        size = class_size.get(w.get("ClassName"))
        if not size:
            continue
        key = (32, size)
        if key in price_buckets:
            counts[key] = counts.get(key, 0) + 1
        else:
            missing.add(f"Gun S{size}")

    if not counts:
        return None

    total = 0
    parts = []
    for (cat_id, size), n in sorted(counts.items(), key=lambda kv: -kv[1] * price_buckets[kv[0]]):
        price = price_buckets[(cat_id, size)]
        total += price * n
        label = COMPONENT_CATEGORIES[cat_id]
        qty = f"{n}x " if n > 1 else ""
        parts.append(f"{qty}{label} S{size} ~{fmt_price(price)}")

    if missing:
        parts.append("no market price for: " + ", ".join(sorted(missing)))

    return {"value": round(total), "breakdown": " · ".join(parts)}


def compute_cargo_split(ship_json_path):
    """Internal vs external SCU capacity from SCUnpacked's CargoGrids.

    Only returns a result when CargoGrids is non-empty — some ships (mining
    vehicles, a few capital ships) report a small non-zero cargo figure in
    FleetYards that isn't backed by an actual named cargo grid in the game
    files (more likely personal inventory or a stale figure). Rather than
    guess at how to split a number we can't verify, those are left alone.
    """
    d = json.load(open(ship_json_path, encoding="utf-8"))
    grids = d.get("CargoGrids") or []
    if not grids:
        return None

    internal = sum(g.get("SCU") or 0 for g in grids if not g.get("IsExternalContainer"))
    external = sum(g.get("SCU") or 0 for g in grids if g.get("IsExternalContainer"))
    return {"total": internal + external, "internal": internal, "external": external}


def main():
    print("Fetching UEX component price buckets...", file=sys.stderr)
    price_buckets = fetch_price_buckets()
    print(f"  {len(price_buckets)} (category, size) price buckets", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmpdir:
        print("Downloading scunpacked-data...", file=sys.stderr)
        ships_dir, ship_items_path = download_scunpacked(tmpdir)

        ship_items = json.load(open(ship_items_path, encoding="utf-8"))
        class_size = {it["className"]: it.get("size") for it in ship_items}

        by_code, bases = build_match_index(ships_dir)

        ships = json.load(open(DATA_PATH, encoding="utf-8"))
        matched = 0
        cargo_fixed = 0
        for ship in ships:
            base = match_ship(ship, by_code, bases)
            if not base:
                ship["componentValueEst"] = None
                ship["componentValueBreakdown"] = None
                ship["cargoInternal"] = None
                ship["cargoExternal"] = None
                continue

            ship_path = os.path.join(ships_dir, base + ".json")

            result = compute_component_value(ship_path, class_size, price_buckets)
            if result:
                matched += 1
                ship["componentValueEst"] = result["value"]
                ship["componentValueBreakdown"] = result["breakdown"]
            else:
                ship["componentValueEst"] = None
                ship["componentValueBreakdown"] = None

            cargo = compute_cargo_split(ship_path)
            if cargo:
                if abs(cargo["total"] - (ship.get("cargo") or 0)) > 0.5:
                    cargo_fixed += 1
                ship["cargo"] = cargo["total"]
                ship["cargoInternal"] = cargo["internal"]
                ship["cargoExternal"] = cargo["external"]
            else:
                ship["cargoInternal"] = None
                ship["cargoExternal"] = None

        print(f"Computed component value for {matched}/{len(ships)} ships", file=sys.stderr)
        print(f"Corrected/split cargo total for {cargo_fixed} ships from scunpacked CargoGrids", file=sys.stderr)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(ships, f, separators=(",", ":"))
    print(f"Updated {DATA_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
