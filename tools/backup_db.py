import os
import sys
import subprocess
import time

# Add root directory to sys.path to import bot configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import conf

def get_tool_path(tool_name):
    import shutil
    path = shutil.which(tool_name)
    if path:
        return path
    if sys.platform == 'win32':
        common_paths = [
            f"C:\\Program Files\\MongoDB\\Tools\\100\\bin\\{tool_name}.exe",
            f"C:\\Program Files\\MongoDB\\Tools\\100\\bin\\{tool_name}",
            f"C:\\mongodb-tools\\bin\\{tool_name}.exe",
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p
    return tool_name

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
    tool_path = get_tool_path("mongodump")
    mongo_url = conf.mongo_url
    if sys.platform == 'win32' and '@mongo:' in mongo_url:
        mongo_url = mongo_url.replace('@mongo:', '@localhost:')
    elif sys.platform == 'win32' and '@mongo/' in mongo_url:
        mongo_url = mongo_url.replace('@mongo/', '@localhost/')

    if "authSource=" not in mongo_url:
        clean_url = mongo_url.rstrip('/')
        # Ensure there is a path slash before the query options
        scheme_separator = "://"
        if scheme_separator in clean_url:
            scheme, address = clean_url.split(scheme_separator, 1)
            if "/" not in address and "?" not in address:
                clean_url = clean_url + "/"
            elif "?" in address and "/" not in address.split("?", 1)[0]:
                parts = clean_url.split("?", 1)
                clean_url = parts[0] + "/?" + parts[1]
        
        separator = "&" if "?" in clean_url else "?"
        mongo_url = f"{clean_url}{separator}authSource=admin"

    command = [
        tool_path,
        f"--uri={mongo_url}",
        f"--archive={archive_path}",
        "--gzip"
    ]
    
    try:
        print(f"Running {tool_path}...")
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
