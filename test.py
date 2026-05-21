from iphone_backup_decrypt import EncryptedBackup

BACKUP = r"D:\CY-6\Digital Forensics\Theory\f5fb1035b13810a45bf0f05c24c69df8df110046\f5fb1035b13810a45bf0f05c24c69df8df110046"
PASSWORD = "hashim123"

b = EncryptedBackup(backup_directory=BACKUP, passphrase=PASSWORD)

print("Methods:", [m for m in dir(b) if not m.startswith("_")])