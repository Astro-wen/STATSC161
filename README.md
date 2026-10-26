# STATS C161 Project

Group project for STATS C161/C261 (Fall 2026, UCLA). We work with Polymarket data: market catalog,
hourly order books and per-wallet trade history. The midterm part is a predictive analysis on this data,
and the final part looks for insider / informed trading in Politics, Technology, Entertainment and Economy markets.

## Setup

```
pip install -r requirements.txt
cp .env.example .env      # then put the password from Bruin Learn in it
```

Don't commit `.env` or anything under `data/`. The repo is public and the data is course-only.

## Getting the data

Database access closes **Oct 29, 11:59pm PDT**, so download what we need before then.

```
python scripts/download_catalog.py                     # markets, events, resolutions (needs eduroam, not UCLA_WEB)
python scripts/download_wallet_trades.py               # all daily trade files, ~3.2 GB
python scripts/build_hourly_book.py --start 2026-05-30 --end 2026-10-26   # hourly book table, ~5 MB per day
```

The two lecture CSVs (`wallet_features.csv`, `wallet_scores.csv`) go in `data/external/`.
See `data/README.md` for the folder layout and how the tables join.

## Layout

```
scripts/     download and build the data
src/         shared helpers
notebooks/   analysis
reports/     midterm and final write-ups
data/        local only
```
