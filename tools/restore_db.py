import os
import sys
import subprocess
import glob

# Add root directory to sys.path to import bot configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import conf

def install_tools_linux():
    import shutil
    if shutil.which("mongorestore"):
        return

    if sys.platform == 'win32':
        return

    print("mongorestore utility not found. Attempting to install mongodb-database-tools...")
    
    is_root = os.getuid() == 0
    sudo_prefix = "" if is_root else "sudo "
    
    try:
        if shutil.which("apt-get"):
            print("Detected Debian/Ubuntu. Installing packages...")
            # Try to install directly first
            res = subprocess.run(f"{sudo_prefix}apt-get update && {sudo_prefix}apt-get install -y mongodb-database-tools", shell=True)
            if res.returncode != 0:
                print("Failed to install mongodb-database-tools directly. Trying mongo-tools...")
                res = subprocess.run(f"{sudo_prefix}apt-get install -y mongo-tools", shell=True)
            
            # If still fails, try configuring official MongoDB repo
            if not shutil.which("mongorestore"):
                print("Setting up MongoDB official repository for database tools...")
                setup_cmd = (
                    f"{sudo_prefix}apt-get update && {sudo_prefix}apt-get install -y curl gnupg && "
                    f"curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg --dearmor | {sudo_prefix}tee /etc/apt/trusted.gpg.d/mongodb-org.gpg > /dev/null && "
                    f"echo \"deb [ arch=amd64,arm64 signed-by=/etc/apt/trusted.gpg.d/mongodb-org.gpg ] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main\" | {sudo_prefix}tee /etc/apt/sources.list.d/mongodb-org-8.0.list && "
                    f"{sudo_prefix}apt-get update && {sudo_prefix}apt-get install -y mongodb-database-tools"
                )
                subprocess.run(setup_cmd, shell=True)
                
        elif shutil.which("yum"):
            print("Detected RHEL/CentOS. Installing...")
            subprocess.run(f"{sudo_prefix}yum install -y mongodb-database-tools || {sudo_prefix}yum install -y mongodb-tools", shell=True)
        elif shutil.which("dnf"):
            print("Detected Fedora. Installing...")
            subprocess.run(f"{sudo_prefix}dnf install -y mongodb-database-tools || {sudo_prefix}dnf install -y mongodb-tools", shell=True)
        elif shutil.which("apk"):
            print("Detected Alpine. Installing...")
            subprocess.run(f"{sudo_prefix}apk add mongodb-tools", shell=True)
        else:
            print("[X] Package manager not recognized. Please install mongodb-database-tools manually.")
    except Exception as e:
        print(f"[X] Auto-installation error: {e}")

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

def restore():
    print("Starting database restore...")
    install_tools_linux()
    

    # Check if backups folder exists
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backups'))
    if sys.platform != 'win32' and os.path.exists("/backups"):
        backup_dir = "/backups"

    if not os.path.exists(backup_dir):
        print(f"[X] Error: Backup directory '{backup_dir}' does not exist.")
        sys.exit(1)
        
    # Find all backup archive files
    archives = glob.glob(os.path.join(backup_dir, "*.archive")) + glob.glob(os.path.join(backup_dir, "*.gz"))
    if not archives:
        print(f"[X] Error: No backup files (*.archive or *.gz) found in '{backup_dir}'.")
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
            print(f"[X] Error: Specified archive file '{specified_archive}' not found.")
            sys.exit(1)
            
    print(f"Restoring database from archive: {latest_archive}")
    
    # Build mongorestore command (uses --drop to clean existing collection data first)
    tool_path = get_tool_path("mongorestore")
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
        f"--archive={latest_archive}",
        "--gzip",
        "--drop",
        "--noIndexRestore"
    ]
    
    try:
        print(f"Running {tool_path}...")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] Database successfully restored from: {latest_archive}")
            print(result.stderr)
        else:
            print(f"[X] mongorestore failed with exit code {result.returncode}")
            print("Error details:")
            print(result.stderr)
            sys.exit(result.returncode)
    except FileNotFoundError:
        print("[X] Error: 'mongorestore' utility not found. Please install mongodb-database-tools.")
        sys.exit(1)
    except Exception as e:
        print(f"[X] An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    restore()
