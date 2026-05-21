code = """import os
import plistlib
import sqlite3
import shutil
from pathlib import Path

try:
    from iphone_backup_decrypt import EncryptedBackup
    HAS_DECRYPT = True
except ImportError:
    HAS_DECRYPT = False


class BackupParser:
    def __init__(self, backup_path, password=None):
        self.backup_path = Path(backup_path)
        self.password = password
        self.device_info = {}
        self.file_map = {}
        self.decrypted_dir = None
        self._encrypted = False

    def parse(self):
        manifest_path = self.backup_path / 'Manifest.db'
        info_path = self.backup_path / 'Info.plist'
        if not manifest_path.exists():
            print('    [!] Manifest.db not found')
            return False
        if info_path.exists():
            with open(info_path, 'rb') as f:
                info = plistlib.load(f)
            self.device_info = {
                'device_name':    info.get('Display Name', 'Unknown'),
                'ios_version':    info.get('Product Version', 'Unknown'),
                'serial_number':  info.get('Serial Number', 'Unknown'),
                'imei':           info.get('IMEI', 'Unknown'),
                'phone_number':   info.get('Phone Number', 'Unknown'),
                'backup_date':    str(info.get('Last Backup Date', 'Unknown')),
                'itunes_version': info.get('iTunes Version', 'Unknown'),
            }
        manifest_plist = self.backup_path / 'Manifest.plist'
        if manifest_plist.exists():
            with open(manifest_plist, 'rb') as f:
                mp = plistlib.load(f)
            self._encrypted = mp.get('IsEncrypted', False)
        if self._encrypted:
            if not self.password:
                print('    [!] Backup encrypted. Use --password flag.')
                return False
            if not HAS_DECRYPT:
                print('    [!] Run: pip install iphone-backup-decrypt')
                return False
            self._decrypt_backup()
        else:
            self._build_file_map(manifest_path)
        return True

    def _decrypt_backup(self):
        self.decrypted_dir = self.backup_path.parent / (self.backup_path.name + '_decrypted')
        self.decrypted_dir.mkdir(exist_ok=True)
        backup = EncryptedBackup(backup_directory=str(self.backup_path), passphrase=self.password)
        print('    [*] Extracting HomeDomain...')
        backup.extract_files(output_folder=str(self.decrypted_dir), domain_like='HomeDomain%')
        print('    [*] Extracting AppDomainGroup...')
        backup.extract_files(output_folder=str(self.decrypted_dir), domain_like='AppDomainGroup%')
        print('    [*] Extracting Safari...')
        try:
            backup.extract_files(output_folder=str(self.decrypted_dir), domain_like='AppDomain-com.apple.mobilesafari%')
        except Exception:
            pass
        print('    [*] Extracting CameraRollDomain...')
        backup.extract_files(output_folder=str(self.decrypted_dir), domain_like='CameraRollDomain%')
        print('    [*] Extracting RootDomain...')
        backup.extract_files(output_folder=str(self.decrypted_dir), domain_like='RootDomain%')
        print('    [*] Building file map...')
        self._build_file_map_decrypted()
        try:
            shutil.copy(str(self.backup_path / 'Manifest.db'), str(self.decrypted_dir / 'Manifest.db'))
        except Exception:
            pass

    def _build_file_map_decrypted(self):
        known = {
            'sms.db':                'HomeDomain::Library/SMS/sms.db',
            'sms.db-wal':            'HomeDomain::Library/SMS/sms.db-wal',
            'CallHistory.storedata': 'HomeDomain::Library/CallHistoryDB/CallHistory.storedata',
            'AddressBook.sqlitedb':  'HomeDomain::Library/AddressBook/AddressBook.sqlitedb',
            'history.db':            'AppDomain-com.apple.mobilesafari::Library/Safari/History.db',
            'Photos.sqlite':         'CameraRollDomain::Media/PhotoData/Photos.sqlite',
        }
        for file in Path(self.decrypted_dir).rglob('*'):
            if file.is_file():
                if file.name in known:
                    self.file_map[known[file.name]] = str(file)

    def _build_file_map(self, db_path):
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT fileID, domain, relativePath FROM Files')
        for row in cur.fetchall():
            key = row['domain'] + '::' + row['relativePath']
            fid = row['fileID']
            actual = self.backup_path / fid[:2] / fid
            if actual.exists():
                self.file_map[key] = str(actual)
        conn.close()

    def get_file(self, domain, relative_path):
        return self.file_map.get(domain + '::' + relative_path)

    def get_files_by_domain(self, domain):
        result = {}
        prefix = domain + '::'
        for key, path in self.file_map.items():
            if key.startswith(prefix):
                result[key[len(prefix):]] = path
        return result

    def get_device_info(self):
        return self.device_info

    def is_encrypted(self):
        return self._encrypted
"""

with open(r"extractors\\backup_parser.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Done! backup_parser.py fixed.")