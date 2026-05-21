"""
call_extractor.py
Extracts call history from CallHistory.storedata (CoreData SQLite)
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


def fmt_duration(seconds) -> str:
    if seconds is None:
        return "0s"
    try:
        s = int(float(seconds))
        return f"{s // 60}m {s % 60}s"
    except Exception:
        return str(seconds)


class CallExtractor:
    DOMAIN = "HomeDomain"
    RELATIVE = "Library/CallHistoryDB/CallHistory.storedata"

    def __init__(self, parser):
        self.parser = parser

    def extract(self) -> list:
        db_path = self.parser.get_file(self.DOMAIN, self.RELATIVE)
        if not db_path:
            raise FileNotFoundError("CallHistory.storedata not found in backup")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Table is ZCALLRECORD in CoreData schema
        cur.execute("""
            SELECT
                ZADDRESS,
                ZDURATION,
                ZDATE,
                ZORIGINATED,
                ZANSWERED,
                ZCALLTYPE,
                ZSERVICE_PROVIDER
            FROM ZCALLRECORD
            ORDER BY ZDATE DESC
            LIMIT 300
        """)
        rows = cur.fetchall()
        conn.close()

        call_type_map = {0: "Phone", 1: "FaceTime Video", 8: "FaceTime Audio"}
        records = []
        for r in rows:
            ct = r["ZCALLTYPE"] or 0
            records.append({
                "number":    r["ZADDRESS"] or "Unknown",
                "duration":  fmt_duration(r["ZDURATION"]),
                "date":      apple_ts(r["ZDATE"]),
                "direction": "Outgoing" if r["ZORIGINATED"] else "Incoming",
                "answered":  bool(r["ZANSWERED"]),
                "type":      call_type_map.get(ct, f"Type {ct}"),
                "provider":  r["ZSERVICE_PROVIDER"] or "Unknown",
            })
        return records
