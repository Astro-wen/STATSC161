# data

The catalog, the hourly book and the two lecture CSVs are committed (the repo is private).
The raw wallet trades are too big for GitHub; run `scripts/download_wallet_trades.py` or ask Aaron for a copy.

```
data/
  raw/
    catalog/            events.parquet, resolutions.parquet, markets/ (split in 6 parts, read with pd.read_parquet('data/raw/catalog/markets'))
    wallet_trades/      one parquet per day, every fill with a pseudonymous wallet (download_wallet_trades.py)
    book_snapshots/     only if build_hourly_book.py is run with --keep-raw
  processed/
    hourly_book/        best bid/ask, mid, spread, 2c depth per asset per hour (build_hourly_book.py)
                        assets with an empty book that hour are dropped
  external/
    wallet_features.csv the 55,952-wallet table from the Week 3 lecture package
    wallet_scores.csv   same wallets with the lecture's Isolation Forest score
```

Joins: `wallet_trades.market` = `markets.slug`. The book files use `market` = condition id and
`asset_id` = token id, so go through `markets.token_ids` / `markets.outcomes` to match a trade's outcome
to a book row.

Known recorder gaps in the order book: 2026-06-16T11 to 06-19T19, 08-25T00 to 08-31T14, 09-14T01 to 09-14T15.
Wallet trades are complete through 2026-10-05.

What we pulled on Oct 26: 543 daily trade files (146M fills, May 2025 to Oct 26 2026), 1.49M markets,
324K events, 321K resolutions, and 143 days of hourly book (05-30 to 10-26, gap days have fewer hours).
