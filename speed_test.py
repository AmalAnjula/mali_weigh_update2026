import time
import speedtest
from datetime import datetime
import csv
import os

LOG_FILE = "internet_speed_log.csv"

def init_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp",
                "Download (Mbps)",
                "Upload (Mbps)",
                "Ping (ms)",
                "Status",
                "Error"
            ])

def log_row(timestamp, download, upload, ping, status, error=""):
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, download, upload, ping, status, error])

def check_speed():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        download_speed = round(st.download() / 1_000_000, 2)
        upload_speed = round(st.upload() / 1_000_000, 2)
        ping = round(st.results.ping, 2)

        print(f"[{timestamp}] OK | Down: {download_speed} Mbps | Up: {upload_speed} Mbps | Ping: {ping} ms")

        log_row(timestamp, download_speed, upload_speed, ping, "OK")

    except Exception as e:
        error_msg = str(e)

        # Detect network-related failure
        if "No connection" in error_msg or "Cannot" in error_msg or "Failed" in error_msg:
            status = "DOWN"
        else:
            status = "ERROR"

        print(f"[{timestamp}] {status} | {error_msg}")

        log_row(timestamp, "", "", "", status, error_msg)

# Initialize CSV
init_log()

# Run every 5 minutes
while True:
    check_speed()
    time.sleep(300)