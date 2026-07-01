import os
from datetime import datetime, timedelta

# Correct folder containing converted TRN files
TARGET_FOLDER = r"C:\Renfrew\2.AVATAR\3_TRN_Bulk_Check\Converted_trn_to_txt"

# Age threshold (3 months ≈ 90 days)
AGE_LIMIT = datetime.now() - timedelta(days=3 * 30)

print(">>> TRN Cleanup Started")
print(f">>> Target folder: {TARGET_FOLDER}")
print(f">>> Deleting TRN files older than: {AGE_LIMIT.strftime('%Y-%m-%d')}")
print("--------------------------------------------------")

deleted = 0
kept = 0

for filename in os.listdir(TARGET_FOLDER):
    full_path = os.path.join(TARGET_FOLDER, filename)

    # Only delete .trn or .txt.trn style files
    if not filename.lower().endswith(".trn") and not filename.lower().endswith(".txt"):
        kept += 1
        continue

    # Skip directories
    if not os.path.isfile(full_path):
        kept += 1
        continue

    # Get last modified time
    file_mtime = datetime.fromtimestamp(os.path.getmtime(full_path))

    # Delete if older than threshold
    if file_mtime < AGE_LIMIT:
        print(f"Deleting: {filename}  (modified {file_mtime})")
        os.remove(full_path)
        deleted += 1
    else:
        kept += 1

print("--------------------------------------------------")
print(f"Files deleted: {deleted}")
print(f"Files kept:    {kept}")
print(">>> Cleanup complete")
input("Press ENTER to exit...")
