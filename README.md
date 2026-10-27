# STATS C161 Project

Group project for STATS C161/C261 (Fall 2026, UCLA). We work with Polymarket data: market catalog,
hourly order books and per-wallet trade history. The midterm part is a predictive analysis on this data,
and the final part looks for insider / informed trading in Politics, Technology, Entertainment and Economy markets.

## Setup

```
pip install -r requirements.txt
cp .env.example .env      # then put the password from Bruin Learn in it
```

Don't commit `.env`. The repo is private because the data is course-only; please keep it that way.

## Getting the data

The catalog, the hourly book table and the lecture CSVs are already in `data/`. The raw wallet trades (3.1 GB)
are not on GitHub. Database access closes **Oct 29, 11:59pm PDT**, so run the trade download before then if you need it.

```
python scripts/download_catalog.py                     # markets, events, resolutions (needs eduroam, not UCLA_WEB)
python scripts/download_wallet_trades.py               # all daily trade files, ~3.2 GB
python scripts/build_hourly_book.py --start 2026-05-30 --end 2026-10-26   # hourly book table, ~5 MB per day
```

See `data/README.md` for the folder layout and how the tables join.

## Midterm: market calibration

Where things stand and who does what: `AGENTS.md`. Full write-up: `reports/midterm/market_writeup.md`.
Slide script and Q&A: `reports/midterm/slide_script.md`.

```
make market            # tables, figures and executed notebook from the committed sample
make market-from-raw   # also rebuilds the sample from raw trades
```

## Layout

```
scripts/     download and build the data
src/         shared code (market_analysis.py has all analysis logic)
notebooks/   analysis
reports/     midterm and final write-ups
data/        catalog, hourly book, samples (raw trades stay local)
```
