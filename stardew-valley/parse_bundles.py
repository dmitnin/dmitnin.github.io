#!/usr/bin/env python3
"""
Parse the Stardew Valley Bundles wiki page and emit bundles_reference.md.

Usage:
    # 1. Download the page (only needed once, or to refresh):
    curl -s -L \
      -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
      -H "Accept: text/html,application/xhtml+xml" \
      "https://stardewvalleywiki.com/Bundles" > /tmp/bundles_raw.html

    # 2. Run the parser (requires beautifulsoup4):
    #    pip install beautifulsoup4   or   apt install python3-bs4
    python3 parse_bundles.py [/tmp/bundles_raw.html] [bundles_reference.md]
"""

import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

INPUT  = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/bundles_raw.html')
OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / 'bundles_reference.md'

ROOM_BUNDLES = {
    'Crafts Room':    ['Spring_Foraging_Bundle', 'Summer_Foraging_Bundle', 'Fall_Foraging_Bundle',
                       'Winter_Foraging_Bundle', 'Construction_Bundle', 'Exotic_Foraging_Bundle'],
    'Pantry':         ['Spring_Crops_Bundle', 'Summer_Crops_Bundle', 'Fall_Crops_Bundle',
                       'Quality_Crops_Bundle', 'Animal_Bundle', 'Artisan_Bundle'],
    'Fish Tank':      ['River_Fish_Bundle', 'Lake_Fish_Bundle', 'Ocean_Fish_Bundle',
                       'Night_Fishing_Bundle', 'Crab_Pot_Bundle', 'Specialty_Fish_Bundle'],
    'Boiler Room':    ['Blacksmiths_Bundle', 'Geologists_Bundle', 'Adventurers_Bundle'],
    'Bulletin Board': ['Chefs_Bundle', 'Dye_Bundle', 'Field_Research_Bundle',
                       'Fodder_Bundle', 'Enchanters_Bundle'],
    'Vault':          ['g2500_Bundle', 'g5000_Bundle', 'g10000_Bundle', 'g25000_Bundle'],
    'Abandoned JojaMart': ['The_Missing_Bundle'],
}

ROOM_REWARDS = {
    'Crafts Room':        'Bridge Repair → access to Quarry',
    'Pantry':             'Greenhouse',
    'Fish Tank':          'Glittering Boulder Removed → mountain lake fishing spots unlocked',
    'Boiler Room':        'Furnace (Blueprint)',
    'Bulletin Board':     '+500 Friendship with all villagers',
    'Vault':              'Bus Repair → access to Calico Desert and Skull Cavern',
    'Abandoned JojaMart': 'Movie Theater',
}

# Override slot count where wiki display is misleading.
# None = skip the "choose N of M" note entirely (all items required).
SLOT_OVERRIDE = {
    'Adventurers_Bundle': None,  # wiki renders 2 slot-images but all 4 items are required
}


def clean(s):
    return re.sub(r'\s+', ' ', (s or '').replace('\xa0', ' ')).strip()


def is_item_td(td):
    """True for tds that hold a game-item entry (nametemplate or quality overlay)."""
    return bool(
        td.find(class_='nametemplate') or
        td.find(class_='parent') or
        td.find(class_='backimage')
    )


def parse_item_td(td):
    """Return (name, qty, quality) from a game-item td."""
    quality = ''
    for img in td.find_all('img'):
        alt = img.get('alt', '')
        for q in ('Silver', 'Gold', 'Iridium'):
            if q in alt and 'Quality' in alt:
                quality = q
    for a in td.find_all('a'):
        href = a.get('href', '')
        if href.startswith('/') and '/File:' not in href:
            name = clean(a.get_text())
            if name:
                qty_m = re.search(r'\((\d+)\)', clean(td.get_text()))
                return name, qty_m.group(1) if qty_m else '', quality
    return '', '', ''


def parse_bundle(bid, tbl):
    """Parse one bundle wikitable. Returns (bundle_name, slots, items, reward)."""
    th = tbl.find('th', id=bid)
    if not th:
        return None
    bundle_name = clean(th.get_text())
    tbody = tbl.find('tbody') or tbl
    rows = tbody.find_all('tr', recursive=False)

    items, reward, slots = [], '', 0

    for tr in rows:
        tds = tr.find_all(['td', 'th'], recursive=False)

        # Count bundle slots once (from the rowspan column)
        if slots == 0:
            for td in tds:
                s = sum(1 for img in td.find_all('img') if 'Bundle Slot' in img.get('alt', ''))
                if s:
                    slots = s

        # Skip header row
        if any(t.name == 'th' for t in tds):
            continue

        # Reward row
        if tr.find('img', alt=lambda a: a and 'Bundle Reward' in a):
            for td in tds:
                t = clean(td.get_text())
                if t and 'Reward' not in t:
                    reward = t
                    break
            continue

        # Vault gold rows (no item images, just a gold amount)
        if bid.startswith('g') and bid.endswith('_Bundle'):
            for td in tds:
                m = re.search(r'([\d,]+g)', clean(td.get_text()))
                if m:
                    items.append((m.group(1), '', '', 'Place gold in the bundle'))
                    break
            continue

        # Regular item rows
        item_td = source_td = None
        for td in tds:
            if is_item_td(td) and item_td is None:
                item_td = td
            elif item_td is not None and source_td is None and clean(td.get_text()):
                source_td = td

        if item_td is None:
            continue
        name, qty, quality = parse_item_td(item_td)
        if not name:
            continue
        items.append((name, qty, quality, clean(source_td.get_text()) if source_td else ''))

    return bundle_name, slots, items, reward


def build_markdown(soup):
    lines = [
        '# Stardew Valley — Bundles Reference',
        '',
        '> Source: https://stardewvalleywiki.com/Bundles  ',
        '> Downloaded 2026-06-01 for local reference.',
        '',
    ]

    for room_name, bundle_ids in ROOM_BUNDLES.items():
        lines += [f'## {room_name}', '',
                  f'**Room completion reward:** {ROOM_REWARDS.get(room_name, "")}', '']

        for bid in bundle_ids:
            th = soup.find('th', id=bid)
            if not th:
                continue
            tbl = th.find_parent('table')
            result = parse_bundle(bid, tbl)
            if not result:
                continue
            bundle_name, slots, items, reward = result

            lines += [f'### {bundle_name}', '']
            if reward:
                lines += [f'**Reward:** {reward}', '']

            n = len(items)
            eff_slots = SLOT_OVERRIDE.get(bid, slots)
            if eff_slots is not None and 0 < eff_slots < n:
                lines += [f'> Choose any **{eff_slots} of {n}** items below.', '']

            for name, qty, quality, source in items:
                p = f'- [ ] **{name}**'
                if qty:
                    p += f' ×{qty}'
                if quality:
                    p += f' ({quality} quality or better)'
                if source:
                    p += f'  \n  _{source}_'
                lines.append(p)
            lines.append('')

        lines += ['---', '']

    return '\n'.join(lines)


if __name__ == '__main__':
    soup = BeautifulSoup(INPUT.read_text(encoding='utf-8'), 'html.parser')
    md = build_markdown(soup)
    OUTPUT.write_text(md, encoding='utf-8')
    print(f"Written {len(md):,} chars to {OUTPUT}")
