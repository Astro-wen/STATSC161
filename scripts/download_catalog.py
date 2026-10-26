"""Pull the market catalog (markets, events, resolutions) from the course Postgres
into data/raw/catalog/<table>.parquet.

    python scripts/download_catalog.py

Needs PM_DB_URL in .env. On campus use eduroam, UCLA_WEB blocks port 6543.
Big tables are pulled in pages, so if it gets cut off just run it again and it picks up where it stopped.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sqlalchemy import create_engine, text

from common import RAW, db_url

TABLES = {"events": "slug", "markets": "slug", "resolutions": "market_slug"}
PAGE = 100_000


def clean(df):
    for col in df.columns:
        if df[col].dtype == object and df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(lambda v: None if v is None else json.dumps(v))
    return df


def pull(engine, table, key, out):
    final = out / f"{table}.parquet"
    if final.exists():
        print(f"{table}: already done")
        return
    parts_dir = out / f"_{table}_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    parts = sorted(parts_dir.glob("part-*.parquet"))

    last = None
    if parts:
        last = pd.read_parquet(parts[-1], columns=[key])[key].max()

    i = len(parts)
    with engine.connect() as con:
        while True:
            if last is None:
                q = text(f"SELECT * FROM {table} ORDER BY {key} LIMIT :n")
                df = pd.read_sql_query(q, con, params={"n": PAGE})
            else:
                q = text(f"SELECT * FROM {table} WHERE {key} > :k ORDER BY {key} LIMIT :n")
                df = pd.read_sql_query(q, con, params={"k": last, "n": PAGE})
            if df.empty:
                break
            clean(df).to_parquet(parts_dir / f"part-{i:04d}.parquet", index=False)
            last = df[key].iloc[-1]
            i += 1
            print(f"{table}: page {i}", flush=True)
            if len(df) < PAGE:
                break

    df = pd.concat([pd.read_parquet(p) for p in sorted(parts_dir.glob("part-*.parquet"))], ignore_index=True)
    df.to_parquet(final, index=False)
    print(f"{table}: {len(df):,} rows")


def main():
    out = RAW / "catalog"
    out.mkdir(parents=True, exist_ok=True)
    url = db_url().replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url, connect_args={"sslmode": "require", "connect_timeout": 20})
    for table, key in TABLES.items():
        pull(engine, table, key, out)
    engine.dispose()


if __name__ == "__main__":
    main()
