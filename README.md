# Ship Matrix

A single-page comparison table for every ship in Star Citizen — toggle
columns, filter by size/role/manufacturer/crew/cargo/price, drag columns
into any order, and save your own filter presets.

Live at **https://scsm.meoiswa.cat**

## How it's built

- `data/ships.json` — a trimmed dataset pulled from the
  [FleetYards.net](https://fleetyards.net) public API (`scripts/fetch_data.py`),
  enriched with a per-ship component-value estimate (`scripts/fetch_components.py`).
- `template.html` — the page itself, with a `__SHIPS_DATA__` placeholder.
- `scripts/build.py` — splices `data/ships.json` into `template.html` and
  writes the result to `dist/index.html`.
- `.github/workflows/deploy.yml` — builds and publishes `dist/` to GitHub
  Pages on every push to `main`.

## Refreshing ship data

```
python3 scripts/fetch_data.py       # re-pulls data/ships.json from FleetYards
python3 scripts/fetch_components.py # adds/refreshes componentValueEst + breakdown
python3 scripts/build.py            # rebuilds dist/index.html locally, to preview
```

Commit the updated `data/ships.json` and push — the workflow rebuilds and
redeploys automatically.

## Notes

**Component value estimate.** FleetYards doesn't publish structured data
for salvageable component values, so `scripts/fetch_components.py` builds
one from two other sources:

- [UEX Corp API 2.0](https://uexcorp.space) — live buy prices for every
  purchasable ship component (shields, power plants, coolers, quantum
  drives, guns) at every terminal that sells one.
- [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data) —
  data-mined from the game files: each ship's stock loadout (which
  component is installed at which hardpoint, and its size).

Most stock components are manufacturer-exclusive variants that were never
sold on the open market, so there's no direct resale price for the literal
part. What's shown instead is a **replacement-cost estimate**: for each
stock component, the median market price of an aftermarket part of the
same category and size — real, sourced numbers, just not identical to
"what you'd get scrapping this exact ship." Hovering a value in the table
shows its breakdown. Ships without loadout data yet in scunpacked-data
(mostly concepts / not flight-ready) are left blank rather than guessed at
— currently ~178 of 246 ships have an estimate.

The "My Notes" column (saved in your browser's local storage) is still
there for tracking your own numbers on top of all this.
