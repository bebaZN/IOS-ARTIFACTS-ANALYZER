# iOS Artifact Analyzer
### Digital Forensics Semester Project

A Python-based forensic triage tool that extracts and reports artifacts from iOS device backups.

---

## 📁 Project Structure

```
ios_analyzer/
├── analyzer.py              ← Main CLI entry point
├── report_generator.py      ← HTML report builder
├── demo_mode.py             ← Test without a real device
├── requirements.txt
└── extractors/
    ├── backup_parser.py     ← Parses Manifest.db + Info.plist
    ├── sms_extractor.py     ← SMS & iMessage (sms.db)
    ├── call_extractor.py    ← Call logs (CallHistory.storedata)
    ├── contacts_extractor.py← Contacts (AddressBook.sqlitedb)
    ├── safari_extractor.py  ← Browser history (History.db)
    ├── photos_extractor.py  ← Photos + EXIF (Photos.sqlite)
    ├── apps_extractor.py    ← Installed apps (Info.plist)
    └── location_extractor.py← GPS history (cache_encryptedA.db)
```

---

## ⚡ Quick Start (Demo — No iPhone Needed)

```bash
# 1. Install dependencies
pip install exifread iphone-backup-decrypt Pillow

# 2. Run demo with synthetic data
python demo_mode.py

# 3. Open the report
open demo_output/forensic_report.html   # macOS
start demo_output\forensic_report.html  # Windows
```

---

## 📱 Full Usage (With a Real iPhone Backup)

### Step 1 — Create an iOS Backup

**Option A: iTunes / Finder (recommended)**
1. Connect iPhone to PC/Mac via USB
2. Open iTunes (Windows) or Finder (macOS Ventura+)
3. Click your device → "Back Up Now"
4. For unencrypted: leave password blank
5. For encrypted: set a password (needed for SMS/Contacts/Call logs)

**Backup Location:**
- **Windows:** `C:\Users\<YourName>\AppData\Roaming\Apple Computer\MobileSync\Backup\`
- **macOS:**   `~/Library/Application Support/MobileSync/Backup/`

Each backup is a folder named with a long UUID like:  
`00008110-001234567890ABCD`

**Option B: libimobiledevice (Linux/any OS)**
```bash
# Install
sudo apt install libimobiledevice-utils   # Ubuntu/Debian
brew install libimobiledevice             # macOS

# Create backup
idevicebackup2 backup --full /path/to/backup_folder
```

---

### Step 2 — Install Dependencies

```bash
pip install exifread iphone-backup-decrypt Pillow
```

---

### Step 3 — Run the Analyzer

```bash
# Unencrypted backup
python analyzer.py /path/to/backup --output ./case_output --case CASE-2024-001

# Encrypted backup
python analyzer.py /path/to/backup --output ./case_output --password yourpass --case CASE-2024-001
```

---

### Step 4 — View the Report

Open `case_output/forensic_report.html` in any browser.

---

## 🔍 What Gets Extracted

| Artifact         | Source File                        | Records |
|------------------|------------------------------------|---------|
| SMS / iMessage   | `sms.db`                           | Last 500 |
| Call Logs        | `CallHistory.storedata`            | Last 300 |
| Contacts         | `AddressBook.sqlitedb`             | Last 500 |
| Safari History   | `History.db`                       | Last 500 |
| Photos + EXIF    | `Photos.sqlite`                    | Last 300 |
| Installed Apps   | `Info.plist`                       | All     |
| Location History | `cache_encryptedA.db`              | Last 200 |

---

## 🔐 Forensic Best Practices (for your report)

1. **Never work on the original backup** — copy it first
2. **Hash verification** — the tool auto-computes SHA-256 before and after
3. **Chain of custody** — documented in the report header
4. **Read-only** — this tool never modifies the backup

---

## ⚠️ Legal Notice

This tool is for **authorized forensic examination only**.  
Only analyze devices/backups you own or have explicit written permission to examine.  
Unauthorized access to device data may violate computer fraud laws.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `exifread` | EXIF metadata extraction from images |
| `iphone-backup-decrypt` | Decrypt encrypted iOS backups |
| `Pillow` | Image processing |
| `sqlite3` | Built-in Python — parses iOS databases |
| `plistlib` | Built-in Python — parses .plist files |
| Leaflet.js | Interactive GPS map (loaded from CDN) |

---

## 🎓 For Your Forensic Report

Structure your written report as:
1. Cover page (case #, examiner, date, device)
2. Executive summary
3. Methodology (acquisition, tools, hash verification)
4. Chain of custody table
5. Artifact findings (reference the HTML report)
6. GPS map analysis
7. Conclusion and limitations
8. Appendix (tool output, raw hashes)
