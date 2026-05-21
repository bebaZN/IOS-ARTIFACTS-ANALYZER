#!/usr/bin/env python3
"""
iOS Artifact Analyzer
=====================
Digital Forensics Semester Project
Author: [Your Name]
Description: Extracts and reports forensic artifacts from iOS backups.
"""

import argparse
import hashlib
import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

from extractors.backup_parser import BackupParser
from extractors.sms_extractor import SMSExtractor
from extractors.call_extractor import CallExtractor
from extractors.contacts_extractor import ContactsExtractor
from extractors.safari_extractor import SafariExtractor
from extractors.photos_extractor import PhotosExtractor
from extractors.apps_extractor import AppsExtractor
from extractors.location_extractor import LocationExtractor
from report_generator import ReportGenerator


BANNER = """
╔══════════════════════════════════════════════════════════╗
║           iOS Artifact Analyzer v1.0                    ║
║        Digital Forensics Tool — Academic Project        ║
╚══════════════════════════════════════════════════════════╝
"""


def compute_hash(path: str, algo: str = "sha256") -> str:
    """Compute file/directory hash for chain of custody."""
    h = hashlib.new(algo)
    p = Path(path)
    if p.is_file():
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    elif p.is_dir():
        for file in sorted(p.rglob("*")):
            if file.is_file():
                with open(file, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
    return h.hexdigest()


def run_analysis(backup_path: str, output_dir: str, password: str = None, case_number: str = "CASE-001"):
    print(BANNER)
    backup_path = os.path.abspath(backup_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"[*] Case Number   : {case_number}")
    print(f"[*] Backup Path   : {backup_path}")
    print(f"[*] Output Dir    : {output_dir}")
    print(f"[*] Start Time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # --- Chain of Custody: Pre-analysis hash ---
    print("[*] Computing pre-analysis hash (chain of custody)...")
    pre_hash = compute_hash(backup_path)
    print(f"    SHA-256: {pre_hash}")

    # --- Parse Backup ---
    print("\n[*] Parsing iOS backup manifest...")
    parser = BackupParser(backup_path, password=password)
    if not parser.parse():
        print("[!] ERROR: Could not parse backup. Check path or password.")
        sys.exit(1)

    device_info = parser.get_device_info()
    print(f"    Device  : {device_info.get('device_name', 'Unknown')}")
    print(f"    iOS     : {device_info.get('ios_version', 'Unknown')}")
    print(f"    Serial  : {device_info.get('serial_number', 'Unknown')}")
    print(f"    Backup  : {device_info.get('backup_date', 'Unknown')}")

    # --- Run Extractors ---
    results = {}
    sms_extractor = SMSExtractor(parser)
    extractors = [
        ("SMS / iMessage",   sms_extractor),
        ("Call Logs",        CallExtractor(parser)),
        ("Contacts",         ContactsExtractor(parser)),
        ("Safari History",   SafariExtractor(parser)),
        ("Photos & EXIF",    PhotosExtractor(parser, output_dir)),
        ("Installed Apps",   AppsExtractor(parser)),
        ("Location History", LocationExtractor(parser)),
    ]

    print()
    for name, extractor in extractors:
        print(f"[*] Extracting: {name}...")
        try:
            data = extractor.extract()
            results[name] = data
            count = len(data) if isinstance(data, list) else len(data.get("records", []))
            print(f"    └─ Found {count} record(s)")
        except Exception as e:
            print(f"    └─ WARNING: {e}")
            results[name] = []

    # ── Deleted SMS Recovery ─────────────────────────────────────────────────
    print("[*] Extracting: Deleted SMS (forensic carving)...")
    try:
        deleted_data = sms_extractor.extract_deleted()
        results["Deleted SMS"] = deleted_data
        count = len(deleted_data.get("records", []))
        print(f"    └─ Recovered {count} deleted fragment(s)")
        print(f"    └─ Technique: {deleted_data.get('technique','')}")
    except Exception as e:
        print(f"    └─ WARNING: {e}")
        results["Deleted SMS"] = {"records": [], "pages_scanned": 0, "wal_scanned": 0, "technique": str(e)}

    # --- Post-analysis hash (integrity check) ---
    print("\n[*] Computing post-analysis hash...")
    post_hash = compute_hash(backup_path)
    print(f"    SHA-256: {post_hash}")
    integrity = "✔ VERIFIED (backup unchanged)" if pre_hash == post_hash else "✘ MISMATCH — backup may have been altered"
    print(f"    Status : {integrity}")

    # --- Generate Report ---
    print("\n[*] Generating forensic HTML report...")
    custody = {
        "case_number": case_number,
        "examiner": "Digital Forensics Student",
        "pre_hash": pre_hash,
        "post_hash": post_hash,
        "integrity": integrity,
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    generator = ReportGenerator(
        output_dir=output_dir,
        device_info=device_info,
        results=results,
        custody=custody,
    )
    report_path = generator.generate()
    print(f"    └─ Report saved: {report_path}")

    # --- Summary ---
    print("\n" + "="*58)
    print("  ANALYSIS COMPLETE")
    print("="*58)
    total = sum(
        len(v) if isinstance(v, list) else len(v.get("records", []))
        for v in results.values()
    )
    print(f"  Total artifacts extracted : {total}")
    print(f"  Report location           : {report_path}")
    print("="*58)
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="iOS Artifact Analyzer — Digital Forensics Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyzer.py /path/to/backup --output ./case_output
  python analyzer.py /path/to/backup --output ./case_output --password mypass
  python analyzer.py /path/to/backup --output ./case_output --case CASE-2024-001
        """
    )
    parser.add_argument("backup", help="Path to the iOS backup folder")
    parser.add_argument("--output", "-o", default="./output", help="Output directory for report")
    parser.add_argument("--password", "-p", default=None, help="Backup encryption password (if encrypted)")
    parser.add_argument("--case", "-c", default="CASE-001", help="Case number for report header")
    args = parser.parse_args()

    run_analysis(
        backup_path=args.backup,
        output_dir=args.output,
        password=args.password,
        case_number=args.case,
    )


if __name__ == "__main__":
    main()
