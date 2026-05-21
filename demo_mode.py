#!/usr/bin/env python3
"""
demo_mode.py
============
Generates a demo forensic report using FAKE/SYNTHETIC data.
Use this to test the tool and HTML report without a real iOS backup.

Run:  python demo_mode.py
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from report_generator import ReportGenerator

OUTPUT_DIR = "./demo_output"

# ── Fake device info ─────────────────────────────────────────────────
device_info = {
    "device_name":    "iPhone 14 Pro (DEMO)",
    "ios_version":    "17.2.1",
    "serial_number":  "DEMO1234567890",
    "imei":           "35-DEMO-000000-0",
    "phone_number":   "+1 (555) 000-1234",
    "backup_date":    "2024-03-15 09:30:00",
    "itunes_version": "12.13.0",
}

# ── Fake artifacts ───────────────────────────────────────────────────
sms = [
    {"contact":"+1-555-9876","direction":"Received","service":"iMessage","date":"2024-03-15 08:12:00 UTC","text":"Hey, are you coming to the meeting?","attachments":False},
    {"contact":"+1-555-9876","direction":"Sent",    "service":"iMessage","date":"2024-03-15 08:13:00 UTC","text":"Yes, be there in 10 mins","attachments":False},
    {"contact":"+1-555-1111","direction":"Received","service":"SMS",    "date":"2024-03-14 19:45:00 UTC","text":"Your package has been delivered","attachments":False},
    {"contact":"Unknown",    "direction":"Received","service":"SMS",    "date":"2024-03-14 14:00:00 UTC","text":"Verification code: 482910","attachments":False},
    {"contact":"+1-555-2222","direction":"Sent",    "service":"iMessage","date":"2024-03-13 11:30:00 UTC","text":"[Media/Attachment]","attachments":True},
]

calls = [
    {"number":"+1-555-9876","direction":"Outgoing","type":"Phone",          "duration":"3m 22s","answered":True, "date":"2024-03-15 09:00:00 UTC","provider":"T-Mobile"},
    {"number":"+1-555-4444","direction":"Incoming","type":"FaceTime Video", "duration":"12m 5s","answered":True, "date":"2024-03-14 20:15:00 UTC","provider":"T-Mobile"},
    {"number":"+1-555-5555","direction":"Incoming","type":"Phone",          "duration":"0m 0s", "answered":False,"date":"2024-03-14 10:30:00 UTC","provider":"T-Mobile"},
    {"number":"+1-555-6666","direction":"Outgoing","type":"FaceTime Audio", "duration":"5m 10s","answered":True, "date":"2024-03-13 16:00:00 UTC","provider":"T-Mobile"},
]

contacts = [
    {"name":"Alice Johnson",  "organization":"Acme Corp",  "phones":"+1-555-9876","emails":"alice@acme.com","birthday":"","note":""},
    {"name":"Bob Smith",      "organization":"",            "phones":"+1-555-4444","emails":"bob@email.com", "birthday":"1990-05-20","note":"College friend"},
    {"name":"Carol White",    "organization":"NYPD",        "phones":"+1-555-7777","emails":"carol@nypd.gov","birthday":"","note":""},
    {"name":"David Lee",      "organization":"Law Firm LLC","phones":"+1-555-8888","emails":"david@law.com", "birthday":"","note":""},
]

safari = [
    {"title":"Google","domain":"google.com","url":"https://www.google.com","visited":"2024-03-15 08:00:00 UTC","loaded":True},
    {"title":"GitHub - iOS forensics","domain":"github.com","url":"https://github.com/search?q=ios+forensics","visited":"2024-03-14 22:00:00 UTC","loaded":True},
    {"title":"Stack Overflow","domain":"stackoverflow.com","url":"https://stackoverflow.com/questions/ios-backup","visited":"2024-03-14 21:00:00 UTC","loaded":True},
    {"title":"CNN News","domain":"cnn.com","url":"https://cnn.com","visited":"2024-03-14 08:30:00 UTC","loaded":True},
    {"title":"Maps - New York","domain":"maps.apple.com","url":"https://maps.apple.com/?q=New+York","visited":"2024-03-13 10:00:00 UTC","loaded":True},
]

photos = [
    {"filename":"IMG_0001.HEIC","kind":"Photo","date":"2024-03-15 07:55:00 UTC","camera":"Apple iPhone 14 Pro","latitude":40.7128, "longitude":-74.0060,"has_gps":True},
    {"filename":"IMG_0002.HEIC","kind":"Photo","date":"2024-03-14 18:30:00 UTC","camera":"Apple iPhone 14 Pro","latitude":40.7580, "longitude":-73.9855,"has_gps":True},
    {"filename":"VID_0001.MOV", "kind":"Video","date":"2024-03-14 15:00:00 UTC","camera":"Apple iPhone 14 Pro","latitude":40.7489, "longitude":-73.9680,"has_gps":True},
    {"filename":"IMG_0003.HEIC","kind":"Photo","date":"2024-03-13 12:00:00 UTC","camera":"Apple iPhone 14 Pro","latitude":None,    "longitude":None,    "has_gps":False},
]

apps = [
    {"name":"Instagram",    "bundle_id":"com.instagram.Instagram",   "category":"Major Platform"},
    {"name":"WhatsApp",     "bundle_id":"com.whatsapp.WhatsApp",     "category":"Third-Party"},
    {"name":"Telegram",     "bundle_id":"ph.telegra.Telegraph",      "category":"Third-Party"},
    {"name":"Snapchat",     "bundle_id":"com.toyopagroup.picaboo",   "category":"Third-Party"},
    {"name":"Maps",         "bundle_id":"com.apple.Maps",            "category":"Apple System"},
    {"name":"Messages",     "bundle_id":"com.apple.MobileSMS",       "category":"Apple System"},
    {"name":"ProtonMail",   "bundle_id":"ch.protonmail.protonmail",  "category":"Third-Party"},
    {"name":"Signal",       "bundle_id":"org.whispersystems.signal", "category":"Third-Party"},
]

locations = [
    {"type":"Significant Location","latitude":40.7128,"longitude":-74.0060,"date":"2024-03-15"},
    {"type":"Significant Location","latitude":40.7580,"longitude":-73.9855,"date":"2024-03-14"},
    {"type":"Visit",               "latitude":40.6892,"longitude":-74.0445,"date":"2024-03-13"},
]

# ── Chain of custody (fake hashes for demo) ───────────────────────────
fake_hash = hashlib.sha256(b"demo_backup_data_2024").hexdigest()
custody = {
    "case_number": "CASE-DEMO-2024",
    "examiner":    "Student Examiner (Demo Mode)",
    "pre_hash":    fake_hash,
    "post_hash":   fake_hash,
    "integrity":   "✔ VERIFIED (backup unchanged)",
    "start_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

deleted_sms = {
    "records": [
        {
            "text":      "Meet me at the warehouse at midnight, dont tell anyone",
            "date":      "2024-03-10 23:45:00 UTC",
            "contact":   "Unknown (recovered)",
            "direction": "Unknown",
            "service":   "Unknown",
            "method":    "Freelist carving (page 7)",
            "status":    "DELETED — partial recovery",
        },
        {
            "text":      "The package has been delivered. Delete this.",
            "date":      "2024-03-09 14:22:00 UTC",
            "contact":   "Unknown (recovered)",
            "direction": "Unknown",
            "service":   "Unknown",
            "method":    "WAL frame (page 12)",
            "status":    "DELETED — partial recovery",
        },
        {
            "text":      "I already deleted everything from my phone dont worry",
            "date":      "2024-03-08 09:10:00 UTC",
            "contact":   "Unknown (recovered)",
            "direction": "Unknown",
            "service":   "Unknown",
            "method":    "Freelist carving (page 3)",
            "status":    "DELETED — partial recovery",
        },
    ],
    "pages_scanned": 14,
    "wal_scanned":   6,
    "technique":     "SQLite freelist carving (14 free pages) + WAL frame analysis (6 frames)",
}

results = {
    "SMS / iMessage":   sms,
    "Deleted SMS":      deleted_sms,
    "Call Logs":        calls,
    "Contacts":         contacts,
    "Safari History":   safari,
    "Photos & EXIF":    photos,
    "Installed Apps":   apps,
    "Location History": locations,
}

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("🔍 iOS Artifact Analyzer — DEMO MODE")
    print(f"   Generating report with synthetic data...")
    gen = ReportGenerator(
        output_dir=OUTPUT_DIR,
        device_info=device_info,
        results=results,
        custody=custody,
    )
    path = gen.generate()
    print(f"   ✔ Report saved: {path}")
    print(f"\n   Open {path} in your browser to preview the report.")
