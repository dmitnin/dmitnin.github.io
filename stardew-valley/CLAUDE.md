# Stardew Valley Bundle Cheatsheet — Project Notes

A single-page browser app that lets you tick off Community Center bundle items as you collect them. All state is persisted in `localStorage`; no server needed — open `bundles.html` directly in a browser.

## Prerequisites (not committed to the repo)

- **`.venv/`** — Python virtualenv with `beautifulsoup4`, used only to regenerate `bundles_reference.md`.
  Create it once:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install beautifulsoup4
  ```

## Files

| File | Purpose |
|---|---|
| `bundles.html` | The app. Self-contained single-page HTML/CSS/JS. |
| `bundles_reference.md` | Canonical bundle data scraped from the wiki. Human-readable reference and source of truth for the JS data in `bundles.html`. |
| `parse_bundles.py` | Generates `bundles_reference.md` from raw wiki HTML. Requires `.venv`. |
| `download_icons.sh` | Downloads item icon PNGs from the wiki into `img/`. |
| `img/` | Item icons (pixel-art PNGs, 32 px). Referenced from `bundles.html` via the `ICONS` map. |
| `.venv/` | **Not committed.** See Prerequisites above. |

## Refreshing the reference data

```bash
# 1. Re-download the wiki page (the Claude WebFetch tool gets HTTP 403, use curl)
curl -s -L \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
  -H "Accept: text/html,application/xhtml+xml" \
  "https://stardewvalleywiki.com/Bundles" > /tmp/bundles_raw.html

# 2. Regenerate the markdown
.venv/bin/python3 parse_bundles.py

# 3. Manually update the ROOMS data in bundles.html to match
```

Step 3 is currently manual: `bundles_reference.md` is the reference, but the JS data in `bundles.html` is a hand-edited condensed version of it (obtain descriptions are shortened to fit comfortably on one line).

## How `bundles.html` works

### Structure
The page is organised by **Community Center room → bundle → item**, matching the in-game UI. Seven rooms: Crafts Room, Pantry, Fish Tank, Boiler Room, Bulletin Board, Vault, Abandoned JojaMart.

### Data (`const ROOMS`)
All bundle data is embedded as a JS array of room objects. Each room has:
- `id`, `name`, `color` (hex), `reward` (room completion reward)
- `bundles[]` — array of bundle objects, each with `id`, `name`, `reward`, `needed` (items required to complete), `items[]`

Each item has `name`, optional `qty`, optional `quality`, and `obtain` (how/where to get it).

### localStorage keys
Format: `sdv_<bundleId>_<itemIndex>` — e.g. `sdv_spring-foraging_0`.
The `sdv_` prefix is used by `resetAll()` to find and clear all keys at once.

### Auto-completion
- **Bundle complete:** when `checkedCount >= bundle.needed`. The bundle header dims, its checkbox checks, and a progress counter shows e.g. `2 / 6`.
- **Room complete:** when every bundle in the room is complete. The room header dims and checks.
- These are display-only computed states; the user only interacts with item checkboxes.
- `computeBundle(el)` and `computeRoom(el)` are called on every item toggle and on initial render.

### Icons (`const ICONS`)
Maps item name → PNG filename in `img/`. Missing icons are silently hidden via `onerror`. Run `download_icons.sh` to populate `img/`.

## Known quirks in the wiki data
- **Construction Bundle** lists Wood ×99 twice — reproduced faithfully from the wiki.
- **Adventurer's Bundle** shows only 2 slot images in the wiki HTML despite needing all 4 items. `SLOT_OVERRIDE` in `parse_bundles.py` suppresses the spurious note in the markdown.
- **The Missing Bundle** genuinely requires any 5 of 6 items (5 slots shown).
