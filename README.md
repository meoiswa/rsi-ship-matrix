# Ship Matrix

A single-page comparison table for every ship in Star Citizen — toggle
columns, filter by size/role/manufacturer/crew/cargo/price, drag columns
into any order, and save your own filter presets.

Live at **https://scsm.meoiswa.cat**

## How it's built

- `data/ships.json` — a trimmed dataset pulled from the
  [FleetYards.net](https://fleetyards.net) public API (`scripts/fetch_data.py`).
- `template.html` — the page itself, with a `__SHIPS_DATA__` placeholder.
- `scripts/build.py` — splices `data/ships.json` into `template.html` and
  writes the result to `dist/index.html`.
- `.github/workflows/deploy.yml` — builds and publishes `dist/` to GitHub
  Pages on every push to `main`.

## Refreshing ship data

```
python3 scripts/fetch_data.py   # re-pulls data/ships.json from FleetYards
python3 scripts/build.py        # rebuilds dist/index.html locally, to preview
```

Commit the updated `data/ships.json` and push — the workflow rebuilds and
redeploys automatically.

## Notes

FleetYards doesn't publish structured data for salvageable component
values, so that's not in the dataset. The page includes a per-ship "My
Notes" column (saved in your browser's local storage) to track your own
estimates alongside the rest of the stats.
