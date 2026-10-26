"""Download the daily wallet trade files into data/raw/wallet_trades/.

    python scripts/download_wallet_trades.py                      # everything on the server
    python scripts/download_wallet_trades.py --start 2026-05-25 --end 2026-06-15

One file per calendar day, roughly 3.2 GB for the whole history (May 2025 to Oct 2026).
Files already on disk are skipped, so it is safe to rerun.
"""

import argparse
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import requests

from common import RAW, auth, fetch, write_manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2025-05-01")
    p.add_argument("--end", default=dt.date.today().isoformat())
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()

    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    days = [start + dt.timedelta(d) for d in range((end - start).days + 1)]
    out = RAW / "wallet_trades"

    s = requests.Session()
    s.auth = auth()

    def job(day):
        name = f"trades-{day.isoformat()}.parquet"
        return fetch(s, f"wallet_trades/{name}", out / name)

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(job, days))

    got = [r for r in rows if r and "error" not in r]
    failed = [r for r in rows if r and "error" in r]
    write_manifest(got, out / "_manifest.json")
    print(f"{len(got)} files, {sum(r['bytes'] for r in got) / 1e9:.2f} GB, {len(failed)} failed")


if __name__ == "__main__":
    main()
