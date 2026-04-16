# production_logger.py

import csv
import os
import json
import time
from datetime import datetime, timedelta


class ProductionLogger:

    def __init__(self, log_dir="logs", shift_hour=6, retention_days=30,
                 mqtt_publish_fn=None, mqtt_topic="ols/tx/infeed_event"):
        """
        Parameters
        ----------
        log_dir          : directory for CSV files
        shift_hour       : hour at which the production day resets (default 6 AM)
        retention_days   : delete CSV files older than this many days
        mqtt_publish_fn  : optional callable  mqtt_publish_fn(topic, payload)
                           Pass app.py's  mqtt_publish  function here so every
                           logged event also fires an MQTT message.
        mqtt_topic       : MQTT topic for infeed-event messages
        """
        self.log_dir         = log_dir
        self.shift_hour      = shift_hour
        self.retention_days  = retention_days
        self._mqtt_publish   = mqtt_publish_fn   # None → MQTT publish disabled
        self._mqtt_topic     = mqtt_topic

        os.makedirs(self.log_dir, exist_ok=True)
        self.cleanup_old_logs()

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_log_date(self):
        now = datetime.now()
        if now.hour < self.shift_hour:
            now = now - timedelta(days=1)
        return now.strftime("%Y-%m-%d")

    # ── Maintenance ─────────────────────────────────────────────────────

    def cleanup_old_logs(self):
        now = datetime.now()
        for file in os.listdir(self.log_dir):
            if not file.endswith(".csv"):
                continue
            filepath  = os.path.join(self.log_dir, file)
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if now - file_time > timedelta(days=self.retention_days):
                try:
                    os.remove(filepath)
                    print(f"Deleted old log: {file}")
                except Exception as e:
                    print(f"Error deleting {file}: {e}")

    # ── Core log method ─────────────────────────────────────────────────

    def log(self, product, now_weight, req_weight, final_weight, task_state, reason):
        """
        Write one row to today's CSV  AND  (if configured) publish an MQTT
        message on the infeed-event topic.

        MQTT payload
        ────────────
        {
          "ts":         <unix timestamp int>,
          "diff":       <final_weight - now_weight, rounded to 2dp>,
          "task_state": <"Sucess" | "FAIL" | …>
        }

        diff = oil actually added this infeed cycle
             = final_weight (tank weight at end) − now_weight (tank weight at start)
        """
        now      = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        log_date = self._get_log_date()

        # ── 1. Write CSV ─────────────────────────────────────────────
        filename    = os.path.join(self.log_dir, f"production_{log_date}.csv")
        file_exists = os.path.isfile(filename)

        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "date", "time", "product",
                    "now_weight", "req_weight", "final_weight",
                    "task_state", "reason"
                ])
            writer.writerow([
                date_str, time_str, product,
                round(now_weight,   2),
                round(req_weight,   2),
                round(final_weight, 2),
                task_state,
                reason
            ])

        # ── 2. Publish MQTT event ────────────────────────────────────
        if self._mqtt_publish is not None:
            diff    = round(final_weight - now_weight, 2)
            payload = json.dumps({
                "ts":         int(time.time()),
                "diff":       diff,
                "task_state": task_state,
            })
            try:
                self._mqtt_publish(self._mqtt_topic, payload)
            except Exception as exc:
                print(f"[ProductionLogger] MQTT publish error: {exc}")

    # ── CSV Export ──────────────────────────────────────────────────────

    def export_production_log_to_csv(self):
        """
        Export production data from the last 24 hours to a CSV file.

        The file is named: production_YYYY-MM-DD.csv (where date is based on
        the shift hour logic — if current time is before shift_hour, it uses
        yesterday's date).

        Returns the filename if successful, None otherwise.
        """
        try:
            # Get the log date (respects shift_hour)
            log_date = self._get_log_date()
            filename = os.path.join(self.log_dir, f"production_{log_date}.csv")

            if os.path.exists(filename):
                print(f"[ProductionLogger] Export: {filename} already exists")
                return filename
            else:
                print(f"[ProductionLogger] No data to export for {log_date}")
                return None

        except Exception as e:
            print(f"[ProductionLogger] Error exporting CSV: {e}")
            return None