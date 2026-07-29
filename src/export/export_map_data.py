#!/usr/bin/env python3
"""
Export geocoded master list deals to JSON for the public dashboard map.

Writes github_site/deals/map-data.json — consumed by github_site/deals/map.html.
Run as part of generate_site.py (Step 4b).
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import get_session, MasterItem, RawItem


def export_map_data(output_file='github_site/deals/map-data.json'):
    session = get_session()
    try:
        items = session.query(MasterItem).filter(
            MasterItem.latitude != None,
            MasterItem.removed_at.is_(None),   # skip soft-deleted duplicates
        ).order_by(MasterItem.curated_at.desc()).all()

        features = []
        for item in items:
            raw = item.raw_item
            url = item.source_url or (raw.url if raw else None) or ""
            pub_date = raw.published_date.strftime('%b %d, %Y') if raw and raw.published_date else ""

            features.append({
                "lat": item.latitude,
                "lng": item.longitude,
                "company": item.company or "",
                "title": item.title or "",
                "amount": item.investment_amount or "",
                "district": item.congressional_district or "",
                "location": item.location or "",
                "sectors": item.sectors or "",
                "date": pub_date,
                "url": url,
            })

        output = {
            "generated_at": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            "count": len(features),
            "features": features,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        print(f"✓ Exported {len(features)} geocoded deals to {output_file}")
        return len(features)

    finally:
        session.close()


if __name__ == '__main__':
    os.chdir(Path(__file__).parent.parent.parent)
    export_map_data()
