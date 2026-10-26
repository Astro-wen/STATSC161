"""Shared paths, credentials and a download helper for the course data."""

import hashlib
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"

BASE_URL = "https://d1yyqbluk0oz0t.cloudfront.net"

load_dotenv(ROOT / ".env")


def auth():
    user = os.getenv("PM_USER", "polymarketdatabase")
    pw = os.getenv("PM_PASSWORD")
    if not pw:
        raise SystemExit("PM_PASSWORD is missing. Copy .env.example to .env and fill it in.")
    return (user, pw)


def db_url():
    url = os.getenv("PM_DB_URL", "")
    if not url or "<PASSWORD>" in url:
        raise SystemExit("PM_DB_URL is missing or still has <PASSWORD>. Check your .env.")
    return url


def fetch(session, remote_path, dest, retries=4):
    """Download one file. Skips files already on disk with the right size.

    Returns a manifest row, or None if the file does not exist on the server.
    """
    url = f"{BASE_URL}/{remote_path}"
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(retries):
        try:
            head = session.head(url, timeout=60)
            if head.status_code in (403, 404):
                return None
            head.raise_for_status()
            expected = int(head.headers.get("content-length", -1))

            if dest.exists() and dest.stat().st_size == expected:
                return {"path": remote_path, "bytes": expected, "sha256": sha256(dest), "cached": True}

            tmp = dest.with_suffix(dest.suffix + ".part")
            h = hashlib.sha256()
            with session.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        h.update(chunk)
            if expected >= 0 and tmp.stat().st_size != expected:
                raise IOError(f"size mismatch for {remote_path}")
            tmp.replace(dest)
            return {"path": remote_path, "bytes": dest.stat().st_size, "sha256": h.hexdigest(), "cached": False}
        except (requests.RequestException, IOError) as e:
            if attempt == retries - 1:
                print(f"  failed: {remote_path} ({e})")
                return {"path": remote_path, "error": str(e)}
            time.sleep(2 ** attempt)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(rows, path):
    rows = [r for r in rows if r]
    old = []
    if Path(path).exists():
        old = json.loads(Path(path).read_text())
    merged = {r["path"]: r for r in old + rows}
    Path(path).write_text(json.dumps(sorted(merged.values(), key=lambda r: r["path"]), indent=1))
