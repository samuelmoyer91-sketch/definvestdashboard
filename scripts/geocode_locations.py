#!/usr/bin/env python3
"""
Geocode master list locations to lat/lng and congressional district.

Uses two free APIs — no API keys required:
  - Nominatim (OpenStreetMap) for city/state → lat/lng
  - Census TIGERweb for lat/lng → 119th Congressional District

Usage:
    python3 scripts/geocode_locations.py           # Geocode all missing
    python3 scripts/geocode_locations.py --all     # Re-geocode everything
    python3 scripts/geocode_locations.py --dry-run # Preview without saving

Notes:
- Only geocodes US locations; international deals are skipped (no district)
- State-only locations (e.g. "California, USA") get lat/lng but no district
- Rate-limited to ~1.2 req/sec to comply with Nominatim usage policy
"""

import sys
import time
import re
import json
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIGERWEB_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/54/query"

# Nominatim requires a descriptive User-Agent
NOMINATIM_HEADERS = {'User-Agent': 'DefenseCapitalDashboard/1.0 (contact: sam@capitalfordefense.com)'}

US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
}

STATE_NAME_TO_ABBR = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN',
    'mississippi': 'MS', 'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE',
    'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC',
    'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK', 'oregon': 'OR',
    'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA',
    'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC',
}

FIPS_TO_ABBR = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO',
    '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI',
    '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY',
    '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN',
    '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
    '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH',
    '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD',
    '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA',
    '54': 'WV', '55': 'WI', '56': 'WY',
}

STATE_CAPITALS = {
    'AL': 'Montgomery', 'AK': 'Juneau', 'AZ': 'Phoenix', 'AR': 'Little Rock',
    'CA': 'Sacramento', 'CO': 'Denver', 'CT': 'Hartford', 'DE': 'Dover',
    'FL': 'Tallahassee', 'GA': 'Atlanta', 'HI': 'Honolulu', 'ID': 'Boise',
    'IL': 'Springfield', 'IN': 'Indianapolis', 'IA': 'Des Moines',
    'KS': 'Topeka', 'KY': 'Frankfort', 'LA': 'Baton Rouge', 'ME': 'Augusta',
    'MD': 'Annapolis', 'MA': 'Boston', 'MI': 'Lansing', 'MN': 'Saint Paul',
    'MS': 'Jackson', 'MO': 'Jefferson City', 'MT': 'Helena', 'NE': 'Lincoln',
    'NV': 'Carson City', 'NH': 'Concord', 'NJ': 'Trenton', 'NM': 'Santa Fe',
    'NY': 'Albany', 'NC': 'Raleigh', 'ND': 'Bismarck', 'OH': 'Columbus',
    'OK': 'Oklahoma City', 'OR': 'Salem', 'PA': 'Harrisburg', 'RI': 'Providence',
    'SC': 'Columbia', 'SD': 'Pierre', 'TN': 'Nashville', 'TX': 'Austin',
    'UT': 'Salt Lake City', 'VT': 'Montpelier', 'VA': 'Richmond',
    'WA': 'Olympia', 'WV': 'Charleston', 'WI': 'Madison', 'WY': 'Cheyenne',
    'DC': 'Washington',
}


def parse_location(location_str):
    """
    Parse a freeform location string into (city, state_abbr).

    Returns (city_or_None, state_abbr) for US locations.
    Returns None for international or unparseable locations.
    """
    if not location_str:
        return None

    loc = location_str.strip()
    # Strip trailing USA variants
    loc = re.sub(r',?\s*(USA|U\.S\.A\.|United States)\s*$', '', loc, flags=re.IGNORECASE).strip()

    parts = [p.strip() for p in loc.split(',')]
    parts = [p for p in parts if p]

    if not parts:
        return None

    last = parts[-1]

    # Last part is a 2-letter state abbreviation
    if last.upper() in US_STATES:
        city = ', '.join(parts[:-1]) if len(parts) > 1 else None
        return (city or None, last.upper())

    # Last part is a full state name
    if last.lower() in STATE_NAME_TO_ABBR:
        city = ', '.join(parts[:-1]) if len(parts) > 1 else None
        return (city or None, STATE_NAME_TO_ABBR[last.lower()])

    # "City ST" format (no comma, last token is abbreviation)
    tokens = loc.split()
    if len(tokens) >= 2 and tokens[-1].upper() in US_STATES:
        return (' '.join(tokens[:-1]), tokens[-1].upper())

    # Single token that is itself a state
    if len(parts) == 1:
        t = parts[0].lower()
        if t in STATE_NAME_TO_ABBR:
            return (None, STATE_NAME_TO_ABBR[t])
        if parts[0].upper() in US_STATES:
            return (None, parts[0].upper())

    return None  # International or unrecognized


def nominatim_geocode(city, state_abbr):
    """Return (lat, lng) for a US city/state using Nominatim, or (None, None)."""
    query = f"{city}, {state_abbr}, USA" if city else f"{STATE_CAPITALS.get(state_abbr, state_abbr)}, {state_abbr}, USA"
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={'q': query, 'countrycodes': 'us', 'format': 'json', 'limit': 1},
            headers=NOMINATIM_HEADERS,
            timeout=10
        )
        r.raise_for_status()
        results = r.json()
        if results:
            return float(results[0]['lat']), float(results[0]['lon'])
    except Exception as e:
        print(f"    Nominatim error: {e}")
    return None, None


def tigerweb_district(lat, lng):
    """Return congressional district label (e.g. 'TX-37') for lat/lng, or None."""
    try:
        r = requests.get(
            TIGERWEB_URL,
            params={
                'geometry': f'{lng},{lat}',
                'geometryType': 'esriGeometryPoint',
                'inSR': '4326',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': 'BASENAME,STATE,CD119',
                'returnGeometry': 'false',
                'f': 'json'
            },
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        features = data.get('features', [])
        if not features:
            return None
        attrs = features[0]['attributes']
        state_fips = str(attrs.get('STATE', '')).zfill(2)
        state_abbr = FIPS_TO_ABBR.get(state_fips)
        cd_num = attrs.get('CD119') or attrs.get('BASENAME')
        if state_abbr and cd_num:
            try:
                num = int(cd_num)
                label = f"{state_abbr}-AL" if num == 0 else f"{state_abbr}-{num:02d}"
                return label
            except (ValueError, TypeError):
                pass
    except Exception as e:
        print(f"    TIGERweb error: {e}")
    return None


def run(geocode_all=False, dry_run=False):
    session = get_session()

    query = session.query(MasterItem).filter(MasterItem.location != None)
    if not geocode_all:
        query = query.filter(MasterItem.latitude == None)
    items = query.order_by(MasterItem.id).all()

    print("=" * 70)
    print(f"GEOCODING LOCATIONS — {len(items)} items to process")
    if dry_run:
        print("(DRY RUN — no changes saved)")
    print("=" * 70)
    print()

    stats = {'geocoded': 0, 'district': 0, 'international': 0, 'state_only': 0, 'failed': 0}

    for i, item in enumerate(items, 1):
        loc_str = item.location
        print(f"[{i}/{len(items)}] {(item.company or '?')[:40]} — {loc_str}")

        parsed = parse_location(loc_str)
        if parsed is None:
            print(f"  → International/unknown, skipping")
            stats['international'] += 1
            continue

        city, state_abbr = parsed
        state_only = city is None
        if state_only:
            stats['state_only'] += 1
            print(f"  → State-only ({state_abbr}), geocoding to capital for coordinates")

        lat, lng = nominatim_geocode(city, state_abbr)
        time.sleep(1.2)  # Nominatim rate limit: max 1 req/sec

        if lat is None:
            print(f"  ✗ Nominatim found no match")
            stats['failed'] += 1
            continue

        district = None
        if not state_only:
            district = tigerweb_district(lat, lng)
            time.sleep(0.5)

        coord_label = f"({lat:.4f}, {lng:.4f})"
        dist_label = district or ("state-only, no district" if state_only else "district not found")
        print(f"  ✓ {coord_label}  →  {dist_label}")

        stats['geocoded'] += 1
        if district:
            stats['district'] += 1

        if not dry_run:
            item.latitude = lat
            item.longitude = lng
            item.congressional_district = district
            session.commit()

    print()
    print("=" * 70)
    print(f"DONE: {stats['geocoded']} geocoded  |  {stats['district']} with district  |  "
          f"{stats['state_only']} state-only  |  {stats['international']} international  |  "
          f"{stats['failed']} failed")
    if dry_run:
        print("(Dry run — no changes saved)")
    print("=" * 70)

    session.close()


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent)

    geocode_all = '--all' in sys.argv
    dry_run = '--dry-run' in sys.argv

    run(geocode_all=geocode_all, dry_run=dry_run)
