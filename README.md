# Stargaze

An interactive night sky viewer. Shows stars, planets, the Moon and Sun,
and constellation lines for your location, right in the browser -- drag to
pan around the sky, scroll to zoom, and scrub a time slider to see how the
sky changes tonight.

## Setup

Requires [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

This creates `.venv/` and installs the app plus dev tools (pytest, ruff,
pytest-watcher) from `uv.lock`.

## First run: one-time data download

The app uses [Skyfield](https://rhodesmill.org/skyfield/) for astronomy,
which needs two files it doesn't ship with:

- `de421.bsp` (~17 MB) -- JPL ephemeris for the Sun, Moon, and planets.
- The Hipparcos star catalog (~a few MB).

Both are downloaded automatically the first time the app (or the test
suite) runs, and cached in `var/skyfield-data/` (gitignored) -- after that,
everything works offline. On a slow connection, warm the cache ahead of
time instead of waiting on app startup:

```bash
uv run scripts/prefetch_data.py
```

## Run it

```bash
uv run uvicorn stargaze.app:app --reload --app-dir src
```

Then open <http://localhost:8000>. The page will ask for your location
(works over plain HTTP on localhost); decline and enter latitude/longitude
manually if you'd rather not share it.

## Tests

```bash
uv run pytest
```

`pytest-watcher` is installed for continuous re-run on save:

```bash
uv run ptw
```

## Project layout

- `src/stargaze/astronomy.py` -- Skyfield setup and position computation
  (stars, planets, Sun, Moon).
- `src/stargaze/catalog.py` -- loads the curated star-name and
  constellation-line data.
- `src/stargaze/api.py` -- the `GET /api/sky` endpoint.
- `static/` -- the frontend: a canvas-based sky map with no build step.
- `data/` -- curated star names and constellation lines (see
  `data/THIRD_PARTY_LICENSES.md` for sources/licenses).
- `scripts/` -- one-off scripts that generated the files in `data/`, plus
  `prefetch_data.py` for warming the Skyfield cache.

## Data attribution

Star positions and the planetary ephemeris come from Skyfield at runtime
(Hipparcos catalog, JPL DE421). Star names and constellation stick figures
are curated from the IAU Catalog of Star Names and dcf21's
constellation-stick-figures project -- see `data/THIRD_PARTY_LICENSES.md`
for full attribution and license terms (the constellation data is GPLv3+).
