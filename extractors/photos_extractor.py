import sqlite3
from datetime import datetime, timezone

APPLE_EPOCH_OFFSET = 978307200

def apple_ts(ts):
    if ts is None:
        return "Unknown"
    try:
        ts = int(ts)
        if ts > 1e15:
            ts = ts / 1e9
        ts_unix = ts + APPLE_EPOCH_OFFSET
        return datetime.fromtimestamp(ts_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(ts)

class PhotosExtractor:
    DOMAIN   = "CameraRollDomain"
    RELATIVE = "Media/PhotoData/Photos.sqlite"

    def __init__(self, parser, output_dir=None):
        self.parser = parser

    def extract(self):
        db_path = self.parser.get_file(self.DOMAIN, self.RELATIVE)
        if not db_path:
            raise FileNotFoundError("Photos.sqlite not found in backup")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check which tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        records = []

        # iOS 12 uses ZGENERICASSET, iOS 13+ uses ZASSET
        asset_table = None
        if "ZASSET" in tables:
            asset_table = "ZASSET"
        elif "ZGENERICASSET" in tables:
            asset_table = "ZGENERICASSET"

        if asset_table:
            try:
                cur.execute(f"""
                    SELECT
                        ZFILENAME,
                        ZDATECREATED,
                        ZLATITUDE,
                        ZLONGITUDE,
                        ZKIND
                    FROM {asset_table}
                    ORDER BY ZDATECREATED DESC
                    LIMIT 300
                """)
                for r in cur.fetchall():
                    lat = r["ZLATITUDE"]
                    lon = r["ZLONGITUDE"]
                    has_gps = lat is not None and lat != -180.0
                    records.append({
                        "filename":  r["ZFILENAME"] or "Unknown",
                        "date":      apple_ts(r["ZDATECREATED"]),
                        "latitude":  round(float(lat), 6) if has_gps else None,
                        "longitude": round(float(lon), 6) if has_gps else None,
                        "has_gps":   has_gps,
                        "kind":      "Video" if r["ZKIND"] == 1 else "Photo",
                        "camera":    "Apple iPhone",
                    })
            except Exception as e:
                print(f"    [!] Photos query error: {e}")

        conn.close()
        return records