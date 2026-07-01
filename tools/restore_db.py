import os
import sys
import subprocess
import glob

# Add root directory to sys.path to import bot configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import conf

def restore():
    print("Starting database restore...")
    
    # Check if backups folder exists
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backups'))
    if os.path.exists("/backups"):
        backup_dir = "/backups"
        
    if not os.path.exists(backup_dir):
        print(f"[❌] Error: Backup directory '{backup_dir}' does not exist.")
        sys.exit(1)
        
    # Find all backup archive files
    archives = glob.glob(os.path.join(backup_dir, "*.archive"))
    if not archives:
        print(f"[❌] Error: No .archive files found in '{backup_dir}'.")
        sys.exit(1)
        
    # Sort by modification time to get the latest backup
    archives.sort(key=os.path.getmtime)
    latest_archive = archives[-1]
    
    # If a specific archive was passed in command line arguments, use it instead
    if len(sys.argv) > 1:
        specified_archive = sys.argv[1]
        # Resolve path
        if not os.path.isabs(specified_archive):
            specified_archive = os.path.abspath(os.path.join(backup_dir, specified_archive))
            
        if os.path.exists(specified_archive):
            latest_archive = specified_archive
        else:
            print(f"[❌] Error: Specified archive file '{specified_archive}' not found.")
            sys.exit(1)
            
    print(f"Restoring database from archive: {latest_archive}")
    
    # Build mongorestore command (uses --drop to clean existing collection data first)
    command = [
        "mongorestore",
        f"--uri={conf.mongo_url}",
        f"--archive={latest_archive}",
        "--gzip",
        "--drop"
    ]
    
    try:
        print("Running mongorestore...")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[✓] Database successfully restored from: {latest_archive}")
            print(result.stderr)
        else:
            print(f"[❌] mongorestore failed with exit code {result.returncode}")
            print("Error details:")
            print(result.stderr)
            sys.exit(result.returncode)
    except FileNotFoundError:
        print("[❌] Error: 'mongorestore' utility not found. Please install mongodb-database-tools.")
        sys.exit(1)
    except Exception as e:
        print(f"[❌] An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    restore()
