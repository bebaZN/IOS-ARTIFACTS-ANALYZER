"""
apps_extractor.py
Extracts the list of installed applications from the backup Info.plist.
"""

import plistlib
from pathlib import Path


class AppsExtractor:
    def __init__(self, parser):
        self.parser = parser

    def extract(self) -> list:
        info_path = Path(self.parser.backup_path) / "Info.plist"
        if not info_path.exists():
            raise FileNotFoundError("Info.plist not found in backup root")

        with open(info_path, "rb") as f:
            info = plistlib.load(f)

        apps_raw = info.get("Installed Applications", [])
        records = []
        for bundle_id in sorted(apps_raw):
            # Categorize by bundle ID prefix
            category = "Third-Party"
            if bundle_id.startswith("com.apple."):
                category = "Apple System"
            elif any(bundle_id.startswith(p) for p in ["com.google.", "com.facebook.", "com.microsoft.", "com.instagram."]):
                category = "Major Platform"

            records.append({
                "bundle_id": bundle_id,
                "name":      bundle_id.split(".")[-1].replace("-", " ").title(),
                "category":  category,
            })
        return records
