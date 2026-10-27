"""Get category tags for events from Polymarket's public Gamma API.

The course catalog has no category column, so we use Polymarket's own tags to put
events into our four project categories.

    python scripts/fetch_event_tags.py --since 2026-05-30

Output: data/raw/catalog/event_tags.parquet (event_slug, category, tags)
No password needed.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import requests

from common import RAW

GAMMA = "https://gamma-api.polymarket.com/events"

# project category -> Polymarket tag slug
CATEGORIES = {
    "Politics": "politics",
    "Technology": "tech",
    "Entertainment": "pop-culture",
    "Economy": "economy",
}


def fetch(tag, since, closed):
    rows, cursor = [], None
    while True:
        params = {"tag_slug": tag, "closed": closed, "limit": 500,
                  "end_date_min": f"{since}T00:00:00Z"}
        if cursor:
            params["after_cursor"] = cursor
        for attempt in range(4):
            try:
                r = requests.get(GAMMA + "/keyset", params=params, timeout=60)
                r.raise_for_status()
                break
            except requests.RequestException:
                time.sleep(2 ** attempt)
        else:
            raise SystemExit(f"Gamma API failed for {tag} after {len(rows)} events")
        body = r.json()
        for ev in body.get("events") or []:
            rows.append({"event_slug": ev["slug"],
                         "tags": ",".join(t["slug"] for t in ev.get("tags") or [])})
        cursor = body.get("next_cursor")
        if not cursor or not body.get("events"):
            return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", default="2026-05-30")
    a = p.parse_args()

    frames = []
    for cat, tag in CATEGORIES.items():
        # open events matter too: many have markets that already resolved
        rows = fetch(tag, a.since, "true") + fetch(tag, a.since, "false")
        print(f"{cat}: {len(rows)} events")
        df = pd.DataFrame(rows)
        df["category"] = cat
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    # an event can carry several of our tags; keep all of them as a list in `categories`
    agg = out.groupby("event_slug").agg(categories=("category", lambda s: ",".join(sorted(set(s)))),
                                        tags=("tags", "first")).reset_index()
    agg.to_parquet(RAW / "catalog" / "event_tags.parquet", index=False)
    print(f"{len(agg)} distinct events, {(agg.categories.str.contains(',')).sum()} with more than one category")


if __name__ == "__main__":
    main()
