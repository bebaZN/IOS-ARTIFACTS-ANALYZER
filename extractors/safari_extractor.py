"""
safari_extractor.py
Extracts Safari browsing history and bookmarks.
"""

import sqlite3
from datetime import datetime, timezone

APPLE_EPOCH_OFFSET = 978307200


def apple_ts(ts) -> str:
    if ts is None:
        return "Unknown"
    try:
        ts_unix = float(ts) + APPLE_EPOCH_OFFSET
        return datetime.fromtimestamp(ts_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(ts)


class SafariExtractor:
    DOMAIN = "AppDomain-com.apple.mobilesafari"
    HISTORY_DB = "Library/Safari/History.db"

    def __init__(self, parser):
        self.parser = parser

    def extract(self) -> list:
        db_path = self.parser.get_file(self.DOMAIN, self.HISTORY_DB)
        if not db_path:
            raise FileNotFoundError("Safari History.db not found in backup")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT
                hi.url,
                hi.domain_expansion,
                hv.title,
                hv.visit_time,
                hv.load_successful
            FROM history_visits hv
            LEFT JOIN history_items hi ON hv.history_item = hi.id
            ORDER BY hv.visit_time DESC
            LIMIT 500
        """)
        rows = cur.fetchall()
        conn.close()

        records = []
        for r in rows:
            records.append({
                "url":     r["url"] or "Unknown",
                "domain":  r["domain_expansion"] or "",
                "title":   r["title"] or "Untitled",
                "visited": apple_ts(r["visit_time"]),
                "loaded":  bool(r["load_successful"]),
            })
        return records
