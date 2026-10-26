# data

Nothing in here is committed. Run the scripts in `scripts/` to fill it.

```
data/
  raw/
    catalog/            markets, events, resolutions (download_catalog.py)
    wallet_trades/      one parquet per day, every fill with a pseudonymous wallet (download_wallet_trades.py)
    book_snapshots/     only if build_hourly_book.py is run with --keep-raw
  processed/
    hourly_book/        best bid/ask, mid, spread, 2c depth per asset per hour (build_hourly_book.py)
  external/
    wallet_features.csv the 55,952-wallet table from the Week 3 lecture package
    wallet_scores.csv   same wallets with the lecture's Isolation Forest score
```

Joins: `wallet_trades.market` = `markets.slug`. The book files use `market` = condition id and
`asset_id` = token id, so go through `markets.token_ids` / `markets.outcomes` to match a trade's outcome
to a book row.

Known recorder gaps in the order book: 2026-06-16T11 to 06-19T19, 08-25T00 to 08-31T14, 09-14T01 to 09-14T15.
Wallet trades are complete through 2026-10-05.
