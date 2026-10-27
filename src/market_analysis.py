"""Market calibration study: every number in the midterm comes from this module.

Used by scripts/run_market_analysis.py (tables), scripts/make_market_figures.py (figures)
and notebooks/01_market_calibration.ipynb (the walk-through). All randomness is seeded,
so the same input gives the same output.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import logit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "processed" / "market_sample.parquet"
TABLES = ROOT / "reports" / "tables"

HORIZONS = [6, 24, 72, 168]
CATEGORIES = ["Politics", "Technology", "Entertainment", "Economy"]
SPLIT = pd.Timestamp("2026-09-01", tz="UTC")   # train = events fully closed before this
EPS = 0.005                                     # price clip before taking logit
BOOT = 300                                      # bootstrap draws
SEED = 0
PRICE_BINS = np.array([0, .02, .05, .1, .2, .35, .5, .65, .8, .9, .95, .98, 1.0001])


# ---------------------------------------------------------------- data

def load_sample(path=SAMPLE):
    """Rows with a usable price (a trade within 72h of the time point)."""
    s = pd.read_parquet(path)
    d = s[s.has_price].copy().reset_index(drop=True)
    d["lp"] = logit(d.p_last.clip(EPS, 1 - EPS))
    return d


def event_index(events):
    """Map each event to the row positions it owns, for cluster bootstrap."""
    events = np.asarray(events)
    u = np.unique(events)
    return u, {e: np.where(events == e)[0] for e in u}


# ---------------------------------------------------------------- calibration

def _slope(g):
    m = sm.GLM(g.y, sm.add_constant(g[["lp"]]), family=sm.families.Binomial()).fit()
    return m.params["const"], m.params["lp"]


def calibration_slopes(d, boot=BOOT, seed=SEED):
    """Calibration intercept and slope per horizon x category, 95% CI by event bootstrap."""
    rng = np.random.default_rng(seed)
    rows = []
    for h in HORIZONS:
        for cat in ["All"] + CATEGORIES:
            g = d[(d.horizon_h == h) & ((d.category == cat) | (cat == "All"))].reset_index(drop=True)
            a, b = _slope(g)
            u, idx = event_index(g.event_slug)
            bs = []
            for _ in range(boot):
                r = np.concatenate([idx[e] for e in rng.choice(u, len(u))])
                try:
                    bs.append(_slope(g.iloc[r])[1])
                except Exception:      # a rare resample with perfect separation
                    pass
            rows.append({"horizon_h": h, "category": cat, "n": len(g), "events": len(u),
                         "intercept": a, "slope": b,
                         "slope_lo": np.percentile(bs, 2.5), "slope_hi": np.percentile(bs, 97.5),
                         "brier": ((g.p_last - g.y) ** 2).mean(), "yes_rate": g.y.mean()})
    return pd.DataFrame(rows)


def cluster_slope(g):
    """Slope with event-clustered standard errors (used for the robustness cuts)."""
    m = sm.GLM(g.y, sm.add_constant(g[["lp"]]), family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(g.event_slug)[0]})
    b, se = m.params["lp"], m.bse["lp"]
    return {"n": len(g), "events": g.event_slug.nunique(), "slope": b,
            "slope_lo": b - 1.96 * se, "slope_hi": b + 1.96 * se}


def robustness(d):
    """Slope after dropping near-certain prices, and slope by month."""
    rows = []
    for h in HORIZONS:
        g = d[d.horizon_h == h]
        rows.append({"cut": "all prices", "horizon_h": h, **cluster_slope(g)})
        rows.append({"cut": "2c to 98c", "horizon_h": h, **cluster_slope(g[g.p_last.between(.02, .98)])})
    cuts = pd.DataFrame(rows)
    g = d[d.horizon_h == 24]
    months = pd.DataFrame([{"month": str(m), **cluster_slope(gm)}
                           for m, gm in g.groupby(g.resolved_at.dt.tz_localize(None).dt.to_period("M"))])
    return cuts, months


def binned_calibration(g, boot=BOOT, seed=SEED):
    """Mean price and Yes rate per price bin, with event-bootstrap 95% band on the Yes rate."""
    rng = np.random.default_rng(seed)
    g = g.assign(b=np.digitize(g.p_last, PRICE_BINS) - 1).reset_index(drop=True)
    base = g.groupby("b").agg(n=("y", "size"), price=("p_last", "mean"), yes_rate=("y", "mean"))
    u, idx = event_index(g.event_slug)
    draws = []
    for _ in range(boot):
        r = np.concatenate([idx[e] for e in rng.choice(u, len(u))])
        draws.append(g.iloc[r].groupby("b").y.mean())
    draws = pd.concat(draws, axis=1)
    base["lo"] = draws.quantile(.025, axis=1)
    base["hi"] = draws.quantile(.975, axis=1)
    return base


# ---------------------------------------------------------------- models

RECAL = ["lp", "lp_x_h"] + [f"cat_{c}" for c in CATEGORIES[1:]] + [f"lp_{c}" for c in CATEGORIES[1:]]
FULL = ["lp", "lvwap", "horizon_h", "p_change_24h", "p_std_24h", "yes_flow_24h", "log_dollars_24h",
        "log_dollars_cum", "log_n_fills_24h", "log_n_wallets_24h", "log_age_last", "market_age_days",
        "days_to_scheduled_end", "neg_risk", "log_n_markets_in_event"] + [f"cat_{c}" for c in CATEGORIES]


def add_features(d):
    d = d.copy()
    d["lvwap"] = logit(d.vwap_24h.fillna(d.p_last).clip(EPS, 1 - EPS))
    for c in ["dollars_24h", "dollars_cum", "n_fills_24h", "n_wallets_24h", "n_markets_in_event"]:
        d["log_" + c] = np.log1p(d[c].fillna(0))
    d["log_age_last"] = np.log1p(d.last_trade_age_h)
    d["neg_risk"] = d.neg_risk.astype(float)
    for c in CATEGORIES:
        d["cat_" + c] = (d.category == c).astype(float)
    d["lp_x_h"] = d.lp * np.log(d.horizon_h)
    for c in CATEGORIES[1:]:
        d["lp_" + c] = d.lp * d["cat_" + c]
    return d


def split(d):
    """Events whose markets all closed before SPLIT train; everything else tests."""
    last = d.groupby("event_slug").resolved_at.max()
    test_events = set(last[last >= SPLIT].index)
    d = d.copy()
    d["split"] = np.where(d.event_slug.isin(test_events), "test", "train")
    return d


def fit_models(d, seed=SEED):
    d = split(add_features(d))
    tr, te = d[d.split == "train"], d[d.split == "test"].reset_index(drop=True)
    preds = {"Market price": te.p_last.clip(1e-4, 1 - 1e-4).values}
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(tr[RECAL], tr.y)
    preds["Logistic recalibration"] = lr.predict_proba(te[RECAL])[:, 1]
    gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                        min_samples_leaf=40, l2_regularization=1.0, random_state=seed)
    gb.fit(tr[FULL], tr.y)
    preds["Gradient boosting"] = gb.predict_proba(te[FULL])[:, 1]
    sizes = d.groupby("split").agg(rows=("y", "size"), markets=("slug", "nunique"), events=("event_slug", "nunique"))
    return te, preds, gb, sizes


def compare_models(te, preds, boot=BOOT, seed=SEED):
    """Brier, log loss, AUC per model and horizon; model minus market Brier with event-bootstrap CI."""
    rng = np.random.default_rng(seed)
    rows = []
    for subset, base in [("all prices", np.ones(len(te), bool)),
                         ("5c to 95c", te.p_last.between(.05, .95, inclusive="neither").values)]:
        for h in HORIZONS:
            m = base & (te.horizon_h == h).values
            y, ev = te.y.values[m], te.event_slug.values[m]
            u, idx = event_index(ev)
            draws = [np.concatenate([idx[e] for e in rng.choice(u, len(u))]) for _ in range(boot)]
            mkt = preds["Market price"][m]
            for name, p in preds.items():
                p = p[m]
                r = {"subset": subset, "horizon_h": h, "model": name, "n": int(m.sum()),
                     "brier": np.mean((p - y) ** 2), "logloss": log_loss(y, np.clip(p, 1e-4, 1 - 1e-4)),
                     "auc": roc_auc_score(y, p)}
                if name != "Market price":
                    diff = [np.mean((p[k] - y[k]) ** 2) - np.mean((mkt[k] - y[k]) ** 2) for k in draws]
                    r["d_brier"] = r["brier"] - np.mean((mkt - y) ** 2)
                    r["d_brier_lo"], r["d_brier_hi"] = np.percentile(diff, [2.5, 97.5])
                rows.append(r)
    return pd.DataFrame(rows)


def feature_importance(gb, te, seed=SEED):
    pi = permutation_importance(gb, te[FULL], te.y, scoring="neg_brier_score", n_repeats=5, random_state=seed)
    return (pd.DataFrame({"feature": FULL, "brier_increase": pi.importances_mean})
              .sort_values("brier_increase", ascending=False).reset_index(drop=True))


def price_check(d):
    """Trade price vs order-book midpoint where both exist."""
    b = d[d.book_mid.notna()]
    return {"rows_with_book": int(len(b)), "share_with_book": float(d.book_mid.notna().mean()),
            "corr": float(b[["p_last", "book_mid"]].corr().iloc[0, 1]),
            "median_abs_gap": float((b.p_last - b.book_mid).abs().median())}
