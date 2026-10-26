"""Pull the market catalog (markets, events, resolutions) from the course Postgres
into data/raw/catalog/*.parquet.

    python scripts/download_catalog.py

Needs PM_DB_URL in .env. On campus use eduroam, UCLA_WEB blocks port 6543.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sqlalchemy import create_engine

from common import RAW, db_url

TABLES = {
    "events": "SELECT * FROM events",
    "markets": "SELECT * FROM markets",
    "resolutions": "SELECT * FROM resolutions",
}


def main():
    out = RAW / "catalog"
    out.mkdir(parents=True, exist_ok=True)
    url = db_url().replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url, connect_args={"sslmode": "require", "connect_timeout": 20})

    for name, sql in TABLES.items():
        print(f"{name} ...", end=" ", flush=True)
        parts = []
        with engine.connect().execution_options(stream_results=True) as con:
            for chunk in pd.read_sql_query(sql, con, chunksize=200_000):
                parts.append(chunk)
        df = pd.concat(parts, ignore_index=True)
        for col in df.columns:
            if df[col].dtype == object and df[col].map(lambda v: isinstance(v, (list, dict))).any():
                df[col] = df[col].map(lambda v: None if v is None else json.dumps(v))
        df.to_parquet(out / f"{name}.parquet", index=False)
        print(f"{len(df):,} rows")

    engine.dispose()


if __name__ == "__main__":
    main()
