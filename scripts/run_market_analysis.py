"""Run the market calibration study and write every table the slides quote.

    python scripts/run_market_analysis.py

Input:  data/processed/market_sample.parquet (committed), data/processed/hourly_book/
Output: reports/tables/*.csv and reports/tables/key_numbers.json
Takes about a minute. Seeded, so reruns give identical files.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import warnings

warnings.filterwarnings("ignore")

import duckdb
import pandas as pd

import market_analysis as ma


def book_coverage(d):
    """Share of sample markets whose Yes token ever shows up in the hourly book."""
    s = pd.read_parquet(ma.SAMPLE, columns=["slug"]).drop_duplicates()
    m = pd.read_parquet(ma.ROOT / "data" / "raw" / "catalog" / "markets", columns=["slug", "token_ids"])
    s = s.merge(m, on="slug")
    s["yes_token"] = s.token_ids.map(lambda x: json.loads(x)[0])
    con = duckdb.connect()
    con.register("s", s[["slug", "yes_token"]])
    book = str(ma.ROOT / "data" / "processed" / "hourly_book" / "hourly_book-*.parquet")
    seen = con.execute(f"""SELECT count(*) FROM s WHERE yes_token IN
                           (SELECT DISTINCT CAST(asset_id AS VARCHAR) FROM read_parquet('{book}'))""").fetchone()[0]
    return seen / len(s)


def main():
    ma.TABLES.mkdir(parents=True, exist_ok=True)
    full = pd.read_parquet(ma.SAMPLE)
    d = ma.load_sample()

    slopes = ma.calibration_slopes(d)
    cuts, months = ma.robustness(d)
    te, preds, gb, sizes = ma.fit_models(d)
    results = ma.compare_models(te, preds)
    imp = ma.feature_importance(gb, te)
    check = ma.price_check(d)

    slopes.to_csv(ma.TABLES / "calibration_slopes.csv", index=False)
    cuts.to_csv(ma.TABLES / "robustness_price_cut.csv", index=False)
    months.to_csv(ma.TABLES / "robustness_by_month.csv", index=False)
    results.to_csv(ma.TABLES / "model_results.csv", index=False)
    imp.to_csv(ma.TABLES / "feature_importance.csv", index=False)
    sizes.to_csv(ma.TABLES / "train_test_sizes.csv")

    def pick(h, cat="All"):
        return slopes[(slopes.horizon_h == h) & (slopes.category == cat)].iloc[0]

    def res(h, model, subset="all prices"):
        return results[(results.horizon_h == h) & (results.model == model) & (results.subset == subset)].iloc[0]

    def r(x, k=3):
        return round(float(x), k)

    key = {
        "markets_in_sample": int(full.slug.nunique()),
        "markets_with_price_24h": int((d.horizon_h == 24).sum()),
        "events_with_price_24h": int(d[d.horizon_h == 24].event_slug.nunique()),
        "brier_all_by_horizon": {f"{h}h": r(pick(h).brier) for h in ma.HORIZONS},
        "brier_24h_by_category": {c: r(pick(24, c).brier) for c in ma.CATEGORIES},
        "slope_by_horizon_all_prices": {f"{h}h": [r(pick(h).slope), r(pick(h).slope_lo), r(pick(h).slope_hi)]
                                        for h in ma.HORIZONS},
        "slope_24h_by_category": {c: [r(pick(24, c).slope), r(pick(24, c).slope_lo), r(pick(24, c).slope_hi)]
                                  for c in ma.CATEGORIES},
        "slope_2c_to_98c": {f"{row.horizon_h}h": [r(row.slope), r(row.slope_lo), r(row.slope_hi)]
                            for row in cuts[cuts.cut == "2c to 98c"].itertuples()},
        "slope_24h_by_month": {row.month: [r(row.slope), r(row.slope_lo), r(row.slope_hi)] for row in months.itertuples()},
        "train": sizes.loc["train"].to_dict(),
        "test": sizes.loc["test"].to_dict(),
        "test_brier_24h": {m: r(res(24, m).brier, 4) for m in preds},
        "test_brier_24h_5c_to_95c": {m: r(res(24, m, "5c to 95c").brier, 4) for m in preds},
        "test_d_brier_24h": {m: [r(res(24, m).d_brier, 4), r(res(24, m).d_brier_lo, 4), r(res(24, m).d_brier_hi, 4)]
                             for m in list(preds)[1:]},
        "test_auc_24h_market": r(res(24, "Market price").auc),
        "top_features": imp.head(3).set_index("feature").brier_increase.round(4).to_dict(),
        "order_book_coverage_of_markets": r(book_coverage(d)),
        "trade_vs_book": {k: r(v) if isinstance(v, float) else v for k, v in check.items()},
    }
    (ma.TABLES / "key_numbers.json").write_text(json.dumps(key, indent=2, default=int) + "\n")
    print(json.dumps(key, indent=2, default=int))


if __name__ == "__main__":
    main()
