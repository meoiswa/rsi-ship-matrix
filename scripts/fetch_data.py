#!/usr/bin/env python3
"""Fetch ship data from the FleetYards.net public API and write data/ships.json.

FleetYards (https://fleetyards.net) aggregates Star Citizen ship specs and
pledge/in-game pricing from RSI. This trims each ship record down to the
fields the Ship Matrix table actually uses.
"""
import json
import os
import urllib.request

API_URL = "https://api.fleetyards.net/v1/models"
PER_PAGE = 240
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ships.json")


def fetch_page(page):
    url = f"{API_URL}?perPage={PER_PAGE}&page={page}"
    req = urllib.request.Request(url, headers={"User-Agent": "ship-matrix-build/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_all():
    items = []
    page = 1
    while True:
        data = fetch_page(page)
        items.extend(data["items"])
        pagination = data["meta"]["pagination"]
        if page >= pagination["totalPages"]:
            break
        page += 1
    return items


def g(d, *path, default=None):
    cur = d
    for p in path:
        if cur is None:
            return default
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur if cur is not None else default


def trim(it):
    metrics = it.get("metrics") or {}
    speeds = it.get("speeds") or {}
    crew = it.get("crew") or {}
    manu = it.get("manufacturer") or {}
    avail = it.get("availability") or {}
    sold_at = avail.get("soldAt") or []
    rental_at = avail.get("rentalAt") or []
    buy_prices = [s["price"] for s in sold_at if s.get("priceType") == "sell" and s.get("price")]
    rental_prices = [r["price"] for r in rental_at if r.get("price")]

    return {
        "id": it.get("id"),
        "name": it.get("name"),
        "slug": it.get("slug"),
        "manufacturer": g(manu, "name"),
        "manufacturerFull": g(manu, "longName"),
        "classification": it.get("classificationLabel"),
        "focus": it.get("focus"),
        "size": g(metrics, "sizeLabel"),
        "crewMin": g(crew, "min"),
        "crewMax": g(crew, "max"),
        "cargo": g(metrics, "cargo"),
        "personalInventory": g(metrics, "personalInventory"),
        "mass": g(metrics, "mass"),
        "hullHealth": g(metrics, "hullHealth"),
        "length": g(metrics, "length"),
        "beam": g(metrics, "beam"),
        "height": g(metrics, "height"),
        "maxSpeed": g(speeds, "maxSpeed"),
        "scmSpeed": g(speeds, "scmSpeed"),
        "scmSpeedBoosted": g(speeds, "scmSpeedBoosted"),
        "pledgePrice": it.get("pledgePrice"),
        "gamePrice": it.get("price"),
        "buyPriceMin": min(buy_prices) if buy_prices else None,
        "rentalPriceMin": min(rental_prices) if rental_prices else None,
        "productionStatus": it.get("productionStatus"),
        "inGame": it.get("inGame"),
        "playerOwnable": it.get("playerOwnable"),
        "onSale": it.get("onSale"),
        "storeUrl": g(it, "links", "storeUrl"),
        "quantumFuelTankSize": g(metrics, "quantumFuelTankSize"),
        "hydrogenFuelTankSize": g(metrics, "hydrogenFuelTankSize"),
        "weaponPoolSize": g(metrics, "weaponPoolSize"),
    }


def main():
    items = fetch_all()
    rows = [trim(it) for it in items]
    rows.sort(key=lambda r: (r["manufacturer"] or "", r["name"] or ""))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, separators=(",", ":"))

    print(f"Wrote {len(rows)} ships to {OUT_PATH}")


if __name__ == "__main__":
    main()
