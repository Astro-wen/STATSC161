"""Build the market-level sample for the calibration study.

One row per (resolved Yes/No market, horizon h). The market price at h hours before close
comes from the last trades before that moment (wallet trade files). Order-book state is
added where the hourly book recorded that market, which is only about a fifth of them.

    python scripts/build_market_sample.py

Inputs:  data/raw/catalog/{markets/, events.parquet, resolutions.parquet, event_tags.parquet}
         data/raw/wallet_trades/, data/processed/hourly_book/
Output:  data/interim/sample_trades.parquet   (trades of the sample markets only)
         data/processed/market_sample.parquet
"""

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb
import numpy as np
import pandas as pd

from common import DATA, PROCESSED, RAW

HORIZONS_H = [6, 24, 72, 168]            # hours before close
START, END = "2026-06-01", "2026-10-26"  # resolution dates in the study
STALE_H = 72                             # a last trade older than this does not count as a price


def load_markets():
    cat = RAW / "catalog"
    m = pd.read_parquet(cat / "markets")
    r = pd.read_parquet(cat / "resolutions.parquet")
    e = pd.read_parquet(cat / "events.parquet", columns=["slug", "title"])
    tags = pd.read_parquet(cat / "event_tags.parquet")

    df = (m.merge(r, left_on="slug", right_on="market_slug")
           .merge(tags, on="event_slug")
           .merge(e.rename(columns={"slug": "event_slug", "title": "event_title"}), on="event_slug", how="left"))
    df = df[df["outcomes"].map(lambda s: json.loads(s) == ["Yes", "No"])]
    df = df[(df["resolved_at"] >= START) & (df["resolved_at"] < END)]
    df["yes_token"] = df["token_ids"].map(lambda s: json.loads(s)[0])

    # markets that share a condition id are aliases of one contract; keep one
    df = df.sort_values("slug").drop_duplicates("condition_id")

    # primary category: the rarer tag wins, so a Fed-chair event counts as Economy, not Politics
    order = ["Economy", "Technology", "Entertainment", "Politics"]
    df["category"] = df["categories"].map(lambda s: next(c for c in order if c in s.split(",")))
    df["n_markets_in_event"] = df.groupby("event_slug")["slug"].transform("size")
    return df[["slug", "title", "event_slug", "event_title", "category", "categories", "neg_risk",
               "start_date", "end_date", "resolved_at", "resolved_yes", "yes_token",
               "n_markets_in_event"]].reset_index(drop=True)


def extract_trades(slugs):
    out = DATA / "interim" / "sample_trades.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    files = [f for f in sorted(glob.glob(str(RAW / "wallet_trades" / "trades-*.parquet")))
             if Path(f).stem[7:] >= "2026-05-01"]
    con = duckdb.connect()
    con.register("slugs", pd.DataFrame({"market": slugs}))
    con.execute(f"""COPY (SELECT * FROM read_parquet({files})
                    WHERE market IN (SELECT market FROM slugs)) TO '{out}' (FORMAT parquet)""")
    t = pd.read_parquet(out)
    t["p_yes"] = np.where(t["outcome"] == "Yes", t["price"], 1 - t["price"])
    # dollars pushing toward Yes: buying Yes or selling No
    toward_yes = ((t["outcome"] == "Yes") & (t["side"] == "BUY")) | ((t["outcome"] == "No") & (t["side"] == "SELL"))
    t["yes_dollars"] = np.where(toward_yes, t["dollars"], -t["dollars"])
    return t.sort_values(["market", "time"]).reset_index(drop=True)


def trade_features(trades, want):
    """For each (slug, as_of) row of `want`, summarize trading before as_of."""
    feats = []
    groups = dict(tuple(trades.groupby("market", sort=False)))
    for slug, w in want.groupby("slug", sort=False):
        g = groups.get(slug)
        if g is None:
            continue
        ts = g["time"].values.astype("datetime64[ns]")
        p, d, yd, wal = g["p_yes"].values, g["dollars"].values, g["yes_dollars"].values, g["wallet"].values
        cum = np.cumsum(d)
        for idx, as_of in zip(w.index, w["as_of"].values.astype("datetime64[ns]")):
            i = np.searchsorted(ts, as_of, side="left")       # trades strictly before as_of
            if i == 0:
                continue
            j24 = np.searchsorted(ts, as_of - np.timedelta64(24, "h"), side="left")
            last_age = (as_of - ts[i - 1]) / np.timedelta64(1, "h")
            win = slice(j24, i)
            dw = d[win]
            f = {"idx": idx,
                 "p_last": p[i - 1],
                 "last_trade_age_h": last_age,
                 "n_fills_24h": i - j24,
                 "dollars_24h": dw.sum(),
                 "n_wallets_24h": len(set(wal[win])) if i > j24 else 0,
                 "dollars_cum": cum[i - 1],
                 "n_fills_cum": i,
                 "p_prev24": p[j24 - 1] if j24 > 0 else np.nan}
            if i > j24:
                f["vwap_24h"] = (p[win] * dw).sum() / dw.sum()
                f["p_std_24h"] = p[win].std()
                f["yes_flow_24h"] = yd[win].sum() / dw.sum()
            feats.append(f)
    return pd.DataFrame(feats).set_index("idx")


def book_features(want):
    con = duckdb.connect()
    con.register("want", want[["yes_token", "as_of"]].reset_index())
    book = str(PROCESSED / "hourly_book" / "hourly_book-*.parquet")
    return con.execute(f"""
        SELECT w."index" AS idx, b.best_bid, b.best_ask, b.mid AS book_mid, b.spread,
               b.bid_depth_2c, b.ask_depth_2c, b.depth_imbalance
        FROM want w JOIN read_parquet('{book}') b
          ON CAST(b.asset_id AS VARCHAR) = w.yes_token AND b.hour = w.as_of
        WHERE b.best_bid IS NOT NULL AND b.best_ask IS NOT NULL
    """).df().set_index("idx")


def main():
    mk = load_markets()
    print(f"{len(mk):,} resolved Yes/No markets in the four categories")
    trades = extract_trades(mk["slug"].tolist())
    print(f"{len(trades):,} trades in {trades['market'].nunique():,} of those markets")

    want = pd.concat([mk.assign(horizon_h=h) for h in HORIZONS_H], ignore_index=True)
    want["as_of"] = (want["resolved_at"] - pd.to_timedelta(want["horizon_h"], unit="h")).dt.floor("h")

    s = want.join(trade_features(trades, want)).join(book_features(want))
    s["has_price"] = s["p_last"].notna() & (s["last_trade_age_h"] <= STALE_H)
    s["p_change_24h"] = s["p_last"] - s["p_prev24"]
    s["market_age_days"] = (s["as_of"] - s["start_date"]).dt.total_seconds() / 86400
    s["days_to_scheduled_end"] = (s["end_date"] - s["as_of"]).dt.total_seconds() / 86400
    s["y"] = s["resolved_yes"].astype(int)

    out = PROCESSED / "market_sample.parquet"
    s.drop(columns=["yes_token"]).to_parquet(out, index=False)
    print(s.groupby("horizon_h").agg(rows=("slug", "size"), with_price=("has_price", "sum"),
                                     with_book=("book_mid", lambda x: x.notna().sum())))
    print(s[s.has_price].groupby("category")["slug"].nunique())


if __name__ == "__main__":
    main()
