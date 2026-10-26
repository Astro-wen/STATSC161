"""Turn the hourly order-book snapshots into one small table:
one row per asset per hour with best bid/ask, mid, spread and depth near the top.
Assets whose book is empty in that hour are left out.

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
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

from common import PROCESSED, RAW, auth, fetch, write_manifest

DEPTH_BAND = 0.02  # same 2-cent band as bid_depth_2c / ask_depth_2c


def _side(col, n, best_fn):
    """Best price, level count and USD depth within DEPTH_BAND of the best, per row."""
    counts = pc.list_value_length(col).fill_null(0).to_numpy(zero_copy_only=False)
    flat = pc.list_flatten(col)
    best = np.full(n, np.nan)
    depth = np.zeros(n)
    if len(flat):
        lv = pd.DataFrame({
            "row": pc.list_parent_indices(col).to_numpy(),
            "price": flat.field("price").to_numpy(zero_copy_only=False).astype(float),
            "size": flat.field("size").to_numpy(zero_copy_only=False).astype(float),
        })
        b = lv.groupby("row")["price"].agg(best_fn)
        best[b.index.to_numpy()] = b.to_numpy()
        lv["best"] = best[lv["row"].to_numpy()]
        near = (lv["price"] >= lv["best"] - DEPTH_BAND - 1e-9) if best_fn == "max" else (lv["price"] <= lv["best"] + DEPTH_BAND + 1e-9)
        lv = lv[near]
        d = (lv["price"] * lv["size"]).groupby(lv["row"]).sum()
        depth[d.index.to_numpy()] = d.to_numpy()
    return best, counts, depth


def summarize(path):
    t = pq.read_table(path)
    n = t.num_rows
    bb, nb, bd = _side(t.column("bids").combine_chunks(), n, "max")
    ba, na, ad = _side(t.column("asks").combine_chunks(), n, "min")
    df = pd.DataFrame({
        "ts_ms": t.column("ts_ms").to_numpy(),
        "asset_id": t.column("asset_id").to_pandas(),
        "market": t.column("market").to_pandas(),
        "best_bid": bb, "best_ask": ba,
        "n_bid_levels": nb, "n_ask_levels": na,
        "bid_depth_2c": bd, "ask_depth_2c": ad,
    })
    df["hour"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df["mid"] = (df["best_bid"] + df["best_ask"]) / 2
    df["spread"] = df["best_ask"] - df["best_bid"]
    tot = df["bid_depth_2c"] + df["ask_depth_2c"]
    df["depth_imbalance"] = np.where(tot > 0, (df["bid_depth_2c"] - df["ask_depth_2c"]) / tot, np.nan)
    return df


def compact(df):
    """Drop assets with an empty book, sort, and dictionary-encode the long ids.
    This takes a busy day from ~180 MB to a few MB."""
    df = df[(df["n_bid_levels"] + df["n_ask_levels"]) > 0].drop(columns=["ts_ms"])
    df = df.sort_values(["market", "asset_id", "hour"]).reset_index(drop=True)
    for c in ("market", "asset_id"):
        df[c] = df[c].astype("category")
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
            compact(pd.concat(frames, ignore_index=True)).to_parquet(out, index=False, compression="zstd")
        print(f"{day}: {len(frames)}/24 hours")
        day += dt.timedelta(1)


if __name__ == "__main__":
    main()
