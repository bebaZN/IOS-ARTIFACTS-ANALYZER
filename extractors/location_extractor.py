"""
location_extractor.py
Extracts significant location history from cache_encryptedA.db
(Frequent Locations / Significant Locations stored by iOS).
"""

import sqlite3
import plistlib
from pathlib import Path


class LocationExtractor:
    DOMAIN = "RootDomain"
    CACHE_DB = "Library/Caches/com.apple.routined/cache_encryptedA.db"
    CACHE_DB2 = "Library/Caches/com.apple.routined/Local.sqlite"

    def __init__(self, parser):
        self.parser = parser

    def extract(self) -> list:
        db_path = self.parser.get_file(self.DOMAIN, self.CACHE_DB)
        if not db_path:
            db_path = self.parser.get_file(self.DOMAIN, self.CACHE_DB2)
        if not db_path:
            # Try HomeDomain
            db_path = self.parser.get_file("HomeDomain", self.CACHE_DB)
        if not db_path:
            raise FileNotFoundError("Location cache DB not found in backup")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        records = []

        # Try ZRTLEARNEDLOCATIONOFINTERESTMO (significant locations)
        try:
            cur.execute("""
                SELECT
                    ZLATITUDE, ZLONGITUDE,
                    ZLOCATIONLATITUDE, ZLOCATIONLONGITUDE,
                    ZCREATIONDATE, ZEXPIRATIONDATE
                FROM ZRTLEARNEDLOCATIONOFINTERESTMO
                ORDER BY ZCREATIONDATE DESC
                LIMIT 200
            """)
            for r in cur.fetchall():
                lat = r["ZLATITUDE"] or r["ZLOCATIONLATITUDE"]
                lon = r["ZLONGITUDE"] or r["ZLOCATIONLONGITUDE"]
                if lat and lon:
                    records.append({
                        "latitude":  round(float(lat), 6),
                        "longitude": round(float(lon), 6),
                        "type":      "Significant Location",
                        "date":      str(r["ZCREATIONDATE"] or "Unknown"),
                    })
        except Exception:
            pass

        # Try ZRTVISITMO (visit history)
        if not records:
            try:
                cur.execute("""
                    SELECT ZLATITUDE, ZLONGITUDE, ZARRIVALDATE, ZDEPARTUREDATE
                    FROM ZRTVISITMO
                    ORDER BY ZARRIVALDATE DESC
                    LIMIT 200
                """)
                for r in cur.fetchall():
                    if r["ZLATITUDE"] and r["ZLONGITUDE"]:
                        records.append({
                            "latitude":  round(float(r["ZLATITUDE"]), 6),
                            "longitude": round(float(r["ZLONGITUDE"]), 6),
                            "type":      "Visit",
                            "date":      str(r["ZARRIVALDATE"] or "Unknown"),
                        })
            except Exception:
                pass

        conn.close()
        return records
