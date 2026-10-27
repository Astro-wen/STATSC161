"""Figures for the market calibration study.

    python scripts/make_market_figures.py

Run after scripts/run_market_analysis.py (figures 4 and 5 read its tables).
Output: reports/figures/fig1..fig5 (PNG, 200 dpi)
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import market_analysis as ma

OUT = ma.ROOT / "reports" / "figures"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
CAT = {"Politics": "#2a78d6", "Technology": "#eb6834", "Entertainment": "#1baf7a", "Economy": "#eda100"}
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "savefig.dpi": 200, "savefig.bbox": "tight", "svg.hashsalt": "statsc161", "path.simplify": True})
DOT = dict(marker="o", mec=SURF, mew=1.5)


def fig1(d):
    g = d[d.horizon_h == 24]
    c = ma.binned_calibration(g)
    fig, (ax, axh) = plt.subplots(2, 1, figsize=(6.2, 6.6), gridspec_kw={"height_ratios": [4, 1]}, sharex=True)
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls=(0, (4, 3)), label="Perfect calibration")
    ax.fill_between(c.price, c.lo, c.hi, color=CAT["Politics"], alpha=.15, lw=0, label="95% CI (event bootstrap)")
    ax.plot(c.price, c.yes_rate, color=CAT["Politics"], lw=2, ms=6, label="Observed Yes rate", **DOT)
    ax.set_ylabel("Share that resolved Yes")
    ax.set_title(f"Prices 24h before close vs. outcomes\n{len(g):,} markets, {g.event_slug.nunique():,} events, "
                 "Jun to Oct 2026", loc="left")
    ax.legend(loc="upper left", fontsize=10, labelcolor=INK2)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    axh.hist(g.p_last, bins=50, color=MUTED, edgecolor=SURF, linewidth=0.5)
    axh.set_yscale("log")
    axh.set_xlabel("Market price of Yes, 24h before close")
    axh.set_ylabel("Markets (log)")
    fig.savefig(OUT / "fig1_calibration_24h.png")
    plt.close(fig)


def fig2(d):
    g = d[d.horizon_h == 24]
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.6), sharey=True)
    for ax, (cat, col) in zip(axs, CAT.items()):
        gg = g[g.category == cat]
        c = ma.binned_calibration(gg, boot=200)
        ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls=(0, (4, 3)))
        ax.fill_between(c.price, c.lo, c.hi, color=col, alpha=.18, lw=0)
        ax.plot(c.price, c.yes_rate, color=col, lw=2, ms=5, **DOT)
        ax.set_title(f"{cat}\n{len(gg):,} markets, Brier {((gg.p_last - gg.y) ** 2).mean():.3f}", loc="left", fontsize=11)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Price 24h before close")
    axs[0].set_ylabel("Share resolved Yes")
    fig.savefig(OUT / "fig2_calibration_by_category.png")
    plt.close(fig)


def fig3(d):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    H = ma.HORIZONS
    end = {}
    for cat, col in CAT.items():
        v = [((x.p_last - x.y) ** 2).mean() for h in H for x in [d[(d.horizon_h == h) & (d.category == cat)]]]
        ax.plot(H, v, color=col, lw=2, ms=7, **DOT)
        end[cat] = v[0]
    placed = []
    for cat, y in sorted(end.items(), key=lambda kv: kv[1]):
        y2 = max([y] + [p + 0.0042 for p in placed])
        placed.append(y2)
        ax.annotate(cat, (6, y), xytext=(5.2, y2), textcoords="data", va="center", ha="left", color=INK2, fontsize=10)
    ax.set_xscale("log")
    ax.set_xticks(H)
    ax.set_xticklabels(["6h", "24h", "3d", "7d"])
    ax.minorticks_off()
    ax.set_xlim(200, 3.2)
    ax.set_ylabel("Brier score (lower is better)")
    ax.set_xlabel("Time before the market closed")
    ax.set_ylim(0, None)
    ax.set_title("Prices get more accurate as resolution approaches", loc="left")
    fig.savefig(OUT / "fig3_brier_by_horizon.png")
    plt.close(fig)


def fig4():
    r = pd.read_csv(ma.TABLES / "robustness_by_month.csv")
    r["label"] = pd.PeriodIndex(r.month, freq="M").strftime("%b")
    fig, ax = plt.subplots(figsize=(6.6, 4))
    x = np.arange(len(r))
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.errorbar(x, r.slope, yerr=[r.slope - r.slope_lo, r.slope_hi - r.slope], fmt="o", color=CAT["Politics"],
                ms=8, mec=SURF, mew=1.5, elinewidth=2, capsize=0)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{a}\nn={n:,}" for a, n in zip(r.label, r.n)])
    ax.set_ylabel("Calibration slope (1 = calibrated)")
    ax.text(1.55, 0.82, "Above 1: prices too timid (longshots overpriced)\nBelow 1: prices overconfident",
            color=INK2, fontsize=9, va="top", ha="left")
    ax.set_title("The bias is small and moves around month to month", loc="left")
    fig.savefig(OUT / "fig4_slope_by_month.png")
    plt.close(fig)


def fig5():
    R = pd.read_csv(ma.TABLES / "model_results.csv")
    R = R[(R.subset == "all prices") & (R.model != "Market price")]
    fig, ax = plt.subplots(figsize=(6.6, 4))
    for mdl, col, off in [("Logistic recalibration", CAT["Politics"], -0.12), ("Gradient boosting", CAT["Technology"], 0.12)]:
        q = R[R.model == mdl].sort_values("horizon_h")
        ax.errorbar(np.arange(4) + off, q.d_brier * 1000,
                    yerr=[(q.d_brier - q.d_brier_lo) * 1000, (q.d_brier_hi - q.d_brier) * 1000],
                    fmt="o", color=col, ms=8, mec=SURF, mew=1.5, elinewidth=2, label=mdl)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["6h", "24h", "3d", "7d"])
    ax.set_xlabel("Time before close")
    ax.set_ylabel("Brier vs. market price (x1000)\nabove 0 = worse than the market")
    ax.legend(loc="upper left", labelcolor=INK2)
    ax.set_title("Out of sample, neither model beats the price", loc="left")
    fig.savefig(OUT / "fig5_models_vs_market.png")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = ma.load_sample()
    fig1(d)
    fig2(d)
    fig3(d)
    fig4()
    fig5()
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
