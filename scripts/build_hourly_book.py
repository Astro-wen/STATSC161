"""Turn the hourly order-book snapshots into one small table:
one row per asset per hour with best bid/ask, mid, spread and depth near the top.

    python scripts/build_hourly_book.py --start 2026-06-01 --end 2026-06-16
    python scripts/build_hourly_book.py --start 2026-05-30 --end 2026-10-26 --keep-raw

The full snapshot archive is ~37 GB, so by default each raw file is deleted
after it is summarized. Pass --keep-raw to keep them in data/raw/book_snapshots/.
Output: data/processed/hourly_book/hourly_book-YYYY-MM-DD.parquet (one per day).
"""

import argparse
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import requests

from common import PROCESSED, RAW, auth, fetch, write_manifest

DEPTH_BAND = 0.02  # same 2-cent band as bid_depth_2c / ask_depth_2c


def summarize(path):
    snap = pd.read_parquet(path)
    rows = []
    for ts, asset, market, bids, asks in snap[["ts_ms", "asset_id", "market", "bids", "asks"]].itertuples(index=False):
        bb = ba = np.nan
        bd = ad = 0.0
        nb, na = len(bids), len(asks)
        if nb:
            bp = np.array([lvl["price"] for lvl in bids], dtype=float)
            bs = np.array([lvl["size"] for lvl in bids], dtype=float)
            bb = bp.max()
            m = bp >= bb - DEPTH_BAND - 1e-9
            bd = float((bp[m] * bs[m]).sum())
        if na:
            ap = np.array([lvl["price"] for lvl in asks], dtype=float)
            sz = np.array([lvl["size"] for lvl in asks], dtype=float)
            ba = ap.min()
            m = ap <= ba + DEPTH_BAND + 1e-9
            ad = float((ap[m] * sz[m]).sum())
        rows.append((ts, asset, market, bb, ba, nb, na, bd, ad))

    df = pd.DataFrame(rows, columns=["ts_ms", "asset_id", "market", "best_bid", "best_ask",
                                     "n_bid_levels", "n_ask_levels", "bid_depth_2c", "ask_depth_2c"])
    df["hour"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df["mid"] = (df["best_bid"] + df["best_ask"]) / 2
    df["spread"] = df["best_ask"] - df["best_bid"]
    tot = df["bid_depth_2c"] + df["ask_depth_2c"]
    df["depth_imbalance"] = np.where(tot > 0, (df["bid_depth_2c"] - df["ask_depth_2c"]) / tot, np.nan)
    return df


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="first day, YYYY-MM-DD")
    p.add_argument("--end", required=True, help="last day, YYYY-MM-DD (inclusive)")
    p.add_argument("--keep-raw", action="store_true")
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()

    raw_dir = RAW / "book_snapshots"
    out_dir = PROCESSED / "hourly_book"
    out_dir.mkdir(parents=True, exist_ok=True)

    s = requests.Session()
    s.auth = auth()

    day = dt.date.fromisoformat(a.start)
    last = dt.date.fromisoformat(a.end)
    while day <= last:
        out = out_dir / f"hourly_book-{day.isoformat()}.parquet"
        if out.exists():
            print(f"{day} already built")
            day += dt.timedelta(1)
            continue

        hours = [f"{day.isoformat()}T{h:02d}" for h in range(24)]

        def job(h):
            name = f"snap-{h}.parquet"
            dest = raw_dir / name
            row = fetch(s, name, dest)
            if not row or "error" in row:
                return row, None
            summary = summarize(dest)
            if not a.keep_raw:
                dest.unlink()
            return row, summary

        with ThreadPoolExecutor(a.workers) as ex:
            results = list(ex.map(job, hours))

        rows = [r for r, _ in results if r and "error" not in r]
        frames = [f for _, f in results if f is not None]
        write_manifest(rows, out_dir / "_manifest.json")
        if frames:
            pd.concat(frames, ignore_index=True).to_parquet(out, index=False)
        print(f"{day}: {len(frames)}/24 hours")
        day += dt.timedelta(1)


if __name__ == "__main__":
    main()
