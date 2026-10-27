# STATS C161 group project: guide for people and agents

Read this first. It says what the project is, where things stand, and where everything lives.
Last updated Oct 27, 2026.

## The project

UCLA STATS C161/C261, Fall 2026. Group project on Polymarket data.

- **Midterm presentation: Thu Oct 29, 2026**, in class. 15 minutes per team including Q&A. Topic:
  predictive analysis of prediction-market data.
- **Final presentation: Dec 3. Final report (10+ pages, with code): Dec 11, 5pm.** Topic: insider or
  informed-trading detection in Politics, Technology, Entertainment and Economy markets.
- Course data access (database + CloudFront files) **closes Oct 29, 11:59pm PDT**.

## Team and roles (midterm)

| Person | Part | Status |
| --- | --- | --- |
| Aaron | Market: are prices calibrated, can a model beat them? | Done. Results, figures, 7-min script |
| Jiahong | Wallet: how well do wallet traits predict the average price a wallet pays? (`wallet_analysis/`) | Done. Report, 4 slides, figures |
| Leo | Literature review, slides, assembling the deck | In progress |

Talk order: Aaron's market part (7 slides, 7 min) ends with "an informed trader is one who beats the
price", then hands off to Jiahong's wallet part (4 slides). The bridge: the market part shows prices are
hard to beat overall; the wallet part shows which wallets pay low prices, i.e. buy the long shots.

## Where things stand

**Market part (done, reproducible)**
- Finding: prices are well calibrated in all four categories; a faint favorite-longshot pattern exists only at
  extreme prices and is unstable month to month; no model beats the raw price out of sample.
- Full write-up with method, reasoning and figures: `reports/midterm/market_writeup.md`
- Slide-by-slide script (7 slides, 7 min), backup slides, Q&A: `reports/midterm/slide_script.md`
- Figures for slides: `reports/figures/fig1` to `fig5` (PNG, 200 dpi)
- Every quoted number: `reports/tables/key_numbers.json`

**Wallet part (done)**, everything under `wallet_analysis/`
- Question: how well do six wallet traits predict a wallet's volume-weighted average purchase price
  (`avg_buy_price`), and does gradient boosting beat linear regression?
- Result on 11,191 held-out wallets: mean absolute error 22.14 cents (mean baseline), 19.78 (linear),
  16.74 (gradient boosting, R² 0.368). Trade count matters most. Descriptive, not causal or about profit.
- Report: `wallet_analysis/outputs/wallet_purchase_price_report.md` (also .pdf/.docx/.html)
- 4 slides with speaker notes: `wallet_analysis/outputs/wallet_purchase_price_slides.pptx`,
  `wallet_analysis/outputs/presentation_notes.md`; figures in `wallet_analysis/figures/`
- Reproduce: see `wallet_analysis/README.md` (own requirements, Python 3.12)

**Still open for the midterm**
- [ ] Deck assembly (Leo): market slides follow `reports/midterm/slide_script.md`, wallet slides come from
      `wallet_analysis/outputs/wallet_purchase_price_slides.pptx`. Market slide 2 needs a simple 3-step flow
      drawn: resolved markets → price before close (4.1M trades) → grade against outcome. Use one visual
      style across both parts.
- [ ] Timing: market 7 min + wallet part + intro must fit in about 12 minutes, leaving 3 for Q&A.
- [ ] Literature review (Leo). References named in the script: Thaler & Ziemba (1988, JEP) on racetrack
      betting; Snowberg & Wolfers (2010, JPE) on the favorite-longshot bias; Wolfers & Zitzewitz (2004, JEP)
      on prediction markets; Page & Clemen (2013, Economic Journal) on prediction-market calibration.
      Check each citation before using it.
- [ ] Full-team rehearsal, total under 12 minutes plus Q&A.
- [ ] Before Oct 29 11:59pm: re-run the catalog and trade downloads once more to capture the last days.

## Rules for anyone editing (people and agents)

1. **Never type a result number by hand.** Take it from `reports/tables/key_numbers.json` or the CSVs in
   `reports/tables/`. If you change the analysis, run `make market` and update the docs from the new files.
2. **All analysis code lives in `src/market_analysis.py`.** The scripts and the notebook only call it. Do not
   copy logic into a notebook cell.
3. **Never commit `.env`** (database password) or `data/raw/wallet_trades/` (3.1 GB, too big for GitHub).
   Both are in `.gitignore`.
4. **The repo is private** because the course data is class-only. Keep it that way, and do not try to
   identify anyone behind a wallet (course rule).
5. Commit as yourself; keep commit messages short and plain.

## Commands

```
pip install -r requirements.txt
make market            # tables + figures + executed notebook from the committed sample (~2 min)
make market-from-raw   # also rebuilds the sample from raw trades (needs data/raw/wallet_trades/)
```

Data download (only while access lasts; password goes in `.env`, see `.env.example`):

```
python scripts/download_catalog.py          # needs eduroam, not UCLA_WEB
python scripts/download_wallet_trades.py
python scripts/build_hourly_book.py --start 2026-05-30 --end 2026-10-28
python scripts/fetch_event_tags.py --since 2026-05-30
```

## Map

| Path | What |
| --- | --- |
| `src/market_analysis.py` | market analysis: calibration, robustness, models, metrics |
| `src/common.py` | paths, credentials from `.env`, download helper |
| `scripts/` | data download, sample building, tables, figures |
| `notebooks/01_market_calibration.ipynb` | executed walk-through of the market analysis |
| `data/raw/catalog/` | markets (6 parts), events, resolutions, event tags |
| `data/processed/hourly_book/` | best bid/ask, mid, spread, depth per token per hour, May 30 to Oct 26 |
| `data/processed/market_sample.parquet` | market x horizon sample used by the market analysis |
| `data/external/` | lecture tables: `wallet_features.csv`, `wallet_scores.csv` |
| `data/README.md` | data layout and how the tables join |
| `reports/figures/`, `reports/tables/` | outputs of `make market` |
| `reports/midterm/` | market write-up and slide script |
| `wallet_analysis/` | Jiahong's wallet study: code, figures, tables, report, slides |
