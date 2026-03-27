import time
import speedtest
from datetime import datetime
import csv
import os

LOG_FILE = "internet_speed_log.csv"

def init_log():
    # Create file with headers if it doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Download (Mbps)", "Upload (Mbps)", "Ping (ms)"])

def check_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        download_speed = st.download() / 1_000_000  # Mbps
        upload_speed = st.upload() / 1_000_000      # Mbps
        ping = st.results.ping
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{timestamp}] Down: {download_speed:.2f} Mbps | Up: {upload_speed:.2f} Mbps | Ping: {ping:.2f} ms")

        # Log to CSV
        with open(LOG_FILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, f"{download_speed:.2f}", f"{upload_speed:.2f}", f"{ping:.2f}"])

    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")

# Initialize log file
init_log()

# Run every 5 minutes
while True:
    check_speed()
    time.sleep(300)