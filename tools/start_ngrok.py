import subprocess
import time
import json
import urllib.request
import sys
import os

def run_ngrok():
    print("Starting ngrok on port 8080...")
    # Start ngrok in a background process
    try:
        ngrok_proc = subprocess.Popen(["ngrok", "http", "8080"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("Error: 'ngrok' command not found.")
        print("Please make sure ngrok is installed and added to your System PATH.")
        print("If you just installed it, please restart your command prompt, IDE, or Windows Session to update the PATH environment variable.")
        sys.exit(1)

    # Give ngrok some time to start and establish connection
    print("Waiting for ngrok to establish tunnel...")
    for i in range(12):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
                data = json.loads(response.read().decode())
                tunnels = data.get("tunnels", [])
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        public_url = tunnel.get("public_url")
                        print(f"\n[OK] Tunnel established! Public URL: {public_url}")
                        return public_url, ngrok_proc
        except Exception:
            print(".", end="", flush=True)
            pass
    
    print("\nError: Could not retrieve tunnel URL from ngrok API. Is ngrok running?")
    print("Please make sure you have added your auth token using: ngrok config add-authtoken <YOUR_TOKEN>")
    ngrok_proc.terminate()
    sys.exit(1)

def update_config(url):
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        sys.exit(1)

    print(f"Updating {config_path} with webhook_domain = '{url}'...")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    config["webhook_domain"] = url
    config["webhook_mode"] = True
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print("[OK] config.json updated successfully.")

def restart_bot_and_set_webhook(url):
    print("Restarting bot container to apply config...")
    subprocess.run(["docker", "compose", "restart", "bot"])
    
    print("Setting Telegram webhook...")
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    token = config.get("bot_token")
    path = config.get("webhook_path", "/webhook")
    webhook_url = f"{url.rstrip('/')}{path}"
    
    set_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    try:
        with urllib.request.urlopen(set_url) as response:
            res = json.loads(response.read().decode())
            print(f"Webhook set response: {res}")
            if res.get("ok"):
                print("[OK] Telegram webhook set successfully!")
            else:
                print("[ERROR] Failed to set webhook.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Telegram API: {e}")

if __name__ == "__main__":
    url, proc = run_ngrok()
    update_config(url)
    restart_bot_and_set_webhook(url)
    
    print("\n=======================================================")
    print("  Ngrok tunnel is active. Keep this window open!")
    print("  Press Ctrl+C to close the tunnel and exit.")
    print("=======================================================")
    try:
        # Keep python running so the subprocess remains alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ngrok...")
        proc.terminate()
        print("Ngrok stopped.")
