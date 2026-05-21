"""
sms_extractor.py
================
Extracts LIVE and DELETED SMS/iMessage records from sms.db.

Deleted message recovery uses two real forensic techniques:
  1. SQLite Freelist Page Scanning  — pages marked free after DELETE still
     hold raw row data until overwritten. We read them as binary and use
     regex to carve text fragments and timestamps.
  2. WAL (Write-Ahead Log) parsing  — iOS SQLite uses WAL mode. Committed
     but not checkpointed frames in sms.db-wal may contain deleted rows.
"""

import sqlite3
import struct
import re
import os
from datetime import datetime, timezone


APPLE_EPOCH_OFFSET = 978307200
SQLITE_HEADER_MAGIC = b"SQLite format 3\x00"
TEXT_PATTERN = re.compile(rb"[\x20-\x7e\xc0-\xfd]{4,}")
NS_MIN = 0
NS_MAX = int(35 * 365.25 * 24 * 3600 * 1e9)


def apple_ts(ts) -> str:
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


def _read_page_size(db_bytes: bytes) -> int:
    raw = struct.unpack(">H", db_bytes[16:18])[0]
    return 65536 if raw == 1 else raw


def _get_freelist_pages(db_bytes: bytes, page_size: int) -> list:
    total_pages = len(db_bytes) // page_size
    trunk_pgno = struct.unpack(">I", db_bytes[32:36])[0]
    free_offsets = []
    visited = set()

    while trunk_pgno != 0 and trunk_pgno not in visited:
        visited.add(trunk_pgno)
        if trunk_pgno > total_pages:
            break
        offset = (trunk_pgno - 1) * page_size
        page = db_bytes[offset: offset + page_size]
        next_trunk = struct.unpack(">I", page[0:4])[0]
        leaf_count = struct.unpack(">I", page[4:8])[0]
        free_offsets.append(offset)
        for i in range(leaf_count):
            leaf_pgno = struct.unpack(">I", page[8 + i*4: 12 + i*4])[0]
            if 0 < leaf_pgno <= total_pages:
                free_offsets.append((leaf_pgno - 1) * page_size)
        trunk_pgno = next_trunk

    return free_offsets


def _carve_page(page_data: bytes, method: str = "Freelist carving") -> list:
    carved = []
    text_matches = list(TEXT_PATTERN.finditer(page_data))

    for m in text_matches:
        raw_text = m.group(0)
        try:
            text = raw_text.decode("utf-8", errors="replace").strip()
        except Exception:
            continue
        if len(text) < 4 or text.isspace():
            continue
        if any(kw in text.lower() for kw in ["sqlite", "create table", "index", "autoincrement", "integer", "varchar"]):
            continue

        ts_found = "Unknown"
        search_start = max(0, m.start() - 16)
        search_end   = min(len(page_data), m.end() + 16)
        window = page_data[search_start: search_end]

        for i in range(0, len(window) - 7):
            try:
                candidate_be = struct.unpack(">q", window[i:i+8])[0]
                if NS_MIN < candidate_be < NS_MAX:
                    ts_found = apple_ts(candidate_be)
                    break
                candidate_le = struct.unpack("<q", window[i:i+8])[0]
                if NS_MIN < candidate_le < NS_MAX:
                    ts_found = apple_ts(candidate_le)
                    break
            except Exception:
                continue

        carved.append({
            "text":      text[:300],
            "date":      ts_found,
            "contact":   "Unknown (recovered)",
            "direction": "Unknown",
            "service":   "Unknown",
            "method":    method,
            "status":    "DELETED — partial recovery",
        })

    return carved


def _scan_wal(wal_path: str, page_size: int) -> list:
    if not os.path.exists(wal_path):
        return []
    carved = []
    try:
        with open(wal_path, "rb") as f:
            wal_data = f.read()
        if len(wal_data) < 32:
            return []
        frame_size = 24 + page_size
        offset = 32
        while offset + frame_size <= len(wal_data):
            frame_header = wal_data[offset: offset + 24]
            page_data    = wal_data[offset + 24: offset + 24 + page_size]
            page_no = struct.unpack(">I", frame_header[8:12])[0]
            if page_no > 1:
                hits = _carve_page(page_data, method=f"WAL frame (page {page_no})")
                carved.extend(hits)
            offset += frame_size
    except Exception:
        pass
    return carved


def _deduplicate(deleted: list, live_texts: set) -> list:
    seen  = set()
    clean = []
    for r in deleted:
        key = r["text"][:80]
        if key in seen or key in live_texts:
            continue
        seen.add(key)
        clean.append(r)
    return clean


class SMSExtractor:
    DOMAIN     = "AppDomainGroup-group.com.apple.iMessageDatabase"
    DOMAIN_ALT = "HomeDomain"
    RELATIVE   = "Library/SMS/sms.db"

    def __init__(self, parser):
        self.parser = parser

    def extract(self) -> list:
        """Extract live (existing) SMS and iMessage records."""
        db_path = self._find_db()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()
        cur.execute("""
            SELECT
                m.rowid,
                m.text,
                m.date,
                m.is_from_me,
                m.service,
                m.cache_has_attachments,
                COALESCE(h.id, 'Unknown') AS contact
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.rowid
            ORDER BY m.date DESC
            LIMIT 500
        """)
        rows = cur.fetchall()
        conn.close()

        records = []
        for r in rows:
            records.append({
                "id":          r["rowid"],
                "contact":     r["contact"],
                "text":        r["text"] or "[Media/Attachment]",
                "date":        apple_ts(r["date"]),
                "direction":   "Sent" if r["is_from_me"] else "Received",
                "service":     r["service"] or "SMS",
                "attachments": bool(r["cache_has_attachments"]),
            })
        return records

    def extract_deleted(self) -> dict:
        """
        Recover deleted SMS fragments using:
          1. SQLite freelist page carving
          2. WAL (Write-Ahead Log) frame scanning
        """
        db_path = self._find_db()

        with open(db_path, "rb") as f:
            db_bytes = f.read()

        if not db_bytes.startswith(SQLITE_HEADER_MAGIC):
            return {"records": [], "pages_scanned": 0, "wal_scanned": 0,
                    "technique": "Not a valid SQLite file"}

        page_size = _read_page_size(db_bytes)

        # collect live texts for dedup
        live_texts = set()
        try:
            conn = sqlite3.connect(db_path)
            cur  = conn.cursor()
            cur.execute("SELECT text FROM message WHERE text IS NOT NULL")
            live_texts = {row[0][:80] for row in cur.fetchall()}
            conn.close()
        except Exception:
            pass

        # Technique 1 — freelist carving
        free_offsets  = _get_freelist_pages(db_bytes, page_size)
        pages_scanned = len(free_offsets)
        freelist_hits = []
        for offset in free_offsets:
            page_data = db_bytes[offset: offset + page_size]
            freelist_hits.extend(_carve_page(page_data))

        # Technique 2 — WAL scanning
        wal_path    = db_path + "-wal"
        wal_results = _scan_wal(wal_path, page_size)
        wal_scanned = len(wal_results)

        all_carved = freelist_hits + wal_results
        cleaned    = _deduplicate(all_carved, live_texts)

        return {
            "records":       cleaned,
            "pages_scanned": pages_scanned,
            "wal_scanned":   wal_scanned,
            "technique": (
                f"SQLite freelist carving ({pages_scanned} free pages) + "
                f"WAL frame analysis ({wal_scanned} frames)"
            ),
        }

    def _find_db(self) -> str:
        db_path = self.parser.get_file(self.DOMAIN, self.RELATIVE)
        if not db_path:
            db_path = self.parser.get_file(self.DOMAIN_ALT, self.RELATIVE)
        if not db_path:
            raise FileNotFoundError("sms.db not found in backup")
        return db_path
