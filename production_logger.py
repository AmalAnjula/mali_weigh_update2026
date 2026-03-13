# production_logger.py

import csv
import os
from datetime import datetime, timedelta


class ProductionLogger:

    def __init__(self, log_dir="logs", shift_hour=6, retention_days=30):
        self.log_dir = log_dir
        self.shift_hour = shift_hour
        self.retention_days = retention_days

        os.makedirs(self.log_dir, exist_ok=True)

        # delete old logs automatically
        self.cleanup_old_logs()

    def _get_log_date(self):
        now = datetime.now()

        if now.hour < self.shift_hour:
            now = now - timedelta(days=1)

        return now.strftime("%Y-%m-%d")

    def cleanup_old_logs(self):

        now = datetime.now()

        for file in os.listdir(self.log_dir):

            if not file.endswith(".csv"):
                continue

            filepath = os.path.join(self.log_dir, file)

            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))

            if now - file_time > timedelta(days=self.retention_days):

                try:
                    os.remove(filepath)
                    print(f"Deleted old log: {file}")
                except Exception as e:
                    print(f"Error deleting {file}: {e}")

    def log(self, product, now_weight, req_weight, final_weight, task_state, reason):

        now = datetime.now()

        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        log_date = self._get_log_date()

        filename = os.path.join(self.log_dir, f"production_{log_date}.csv")

        file_exists = os.path.isfile(filename)

        with open(filename, "a", newline="") as f:

            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "date",
                    "time",
                    "product",
                    "now_weight",
                    "req_weight",
                    "final_weight",
                    "task_state",
                    "reason"
                ])

            writer.writerow([
                date_str,
                time_str,
                product,
                round(now_weight, 2),
                round(req_weight, 2),
                round(final_weight, 2),
                task_state,
                reason
            ])