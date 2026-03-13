#!/bin/bash
# ── OLS Startup Script ─────────────────────────────────────────
# Runs on Raspberry Pi 5 boot via systemd or autostart
# ──────────────────────────────────────────────────────────────

cd /home/palmoil/stuff

source venv/bin/activate

# 1. Start MQTT serial reader
python mqtttx.py &
echo "[OLS] mqtttx.py started (PID $!)"

sleep 3

# 2. Start Flask app
python app.py &
echo "[OLS] app.py started (PID $!)"

sleep 5

# 3. Open Chromium in fullscreen kiosk mode
chromium \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --start-fullscreen \
  "http://127.0.0.1:5000" &

echo "[OLS] Browser launched"