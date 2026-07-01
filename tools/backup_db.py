import os
import sys
import subprocess
import time

# Add root directory to sys.path to import bot configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import conf

def backup():
    print("Starting database backup...")
    
    # Ensure backups directory exists
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backups'))
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive_name = f"dinogochi_backup_{timestamp}.archive"
    archive_path = os.path.join(backup_dir, archive_name)
    
    # If running inside docker container, we also map to /backups path
    if os.path.exists("/backups"):
        archive_path = os.path.join("/backups", archive_name)

    print(f"Backup destination: {archive_path}")
    
    # Build mongodump command
    command = [
        "mongodump",
        f"--uri={conf.mongo_url}",
        f"--archive={archive_path}",
        "--gzip"
    ]
    
    try:
        print("Running mongodump...")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[✓] Backup successfully created at: {archive_path}")
            print(result.stderr)
        else:
            print(f"[❌] mongodump failed with exit code {result.returncode}")
            print("Error details:")
            print(result.stderr)
            sys.exit(result.returncode)
    except FileNotFoundError:
        print("[❌] Error: 'mongodump' utility not found. Please install mongodb-database-tools.")
        sys.exit(1)
    except Exception as e:
        print(f"[❌] An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    backup()
