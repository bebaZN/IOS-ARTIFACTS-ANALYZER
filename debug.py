from pathlib import Path

decrypted = Path(r"D:\CY-6\Digital Forensics\Theory\f5fb1035b13810a45bf0f05c24c69df8df110046\f5fb1035b13810a45bf0f05c24c69df8df110046_decrypted")

print("Files in decrypted folder:")
for f in decrypted.rglob("*"):
    if f.is_file():
        print(f.relative_to(decrypted))