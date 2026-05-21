"""
contacts_extractor.py
Extracts contacts from AddressBook.sqlitedb
"""

import sqlite3


class ContactsExtractor:
    DOMAIN = "HomeDomain"
    RELATIVE = "Library/AddressBook/AddressBook.sqlitedb"

    def __init__(self, parser):
        self.parser = parser

    def extract(self) -> list:
        db_path = self.parser.get_file(self.DOMAIN, self.RELATIVE)
        if not db_path:
            raise FileNotFoundError("AddressBook.sqlitedb not found in backup")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Get names
        cur.execute("""
            SELECT
                ABPerson.ROWID AS pid,
                ABPerson.First,
                ABPerson.Last,
                ABPerson.Organization,
                ABPerson.Note,
                ABPerson.Birthday
            FROM ABPerson
            ORDER BY ABPerson.Last, ABPerson.First
            LIMIT 500
        """)
        persons = {r["pid"]: dict(r) for r in cur.fetchall()}

        # Get phone numbers
        cur.execute("""
            SELECT record_id, value, label FROM ABMultiValue
            WHERE property = 3
        """)
        phones = {}
        for r in cur.fetchall():
            phones.setdefault(r["record_id"], []).append(r["value"])

        # Get emails
        cur.execute("""
            SELECT record_id, value FROM ABMultiValue
            WHERE property = 4
        """)
        emails = {}
        for r in cur.fetchall():
            emails.setdefault(r["record_id"], []).append(r["value"])

        conn.close()

        records = []
        for pid, p in persons.items():
            name_parts = [p.get("First") or "", p.get("Last") or ""]
            name = " ".join(x for x in name_parts if x).strip() or p.get("Organization") or "Unknown"
            records.append({
                "name":         name,
                "organization": p.get("Organization") or "",
                "phones":       ", ".join(phones.get(pid, [])),
                "emails":       ", ".join(emails.get(pid, [])),
                "birthday":     str(p.get("Birthday") or ""),
                "note":         (p.get("Note") or "")[:100],
            })
        return records
