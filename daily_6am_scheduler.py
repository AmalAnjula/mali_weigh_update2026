"""
daily_6am_scheduler.py
──────────────────────────────────────────────────────────────────
Runs a daily scheduler that exports production logs to CSV at 6 AM.

Usage:
  from daily_6am_scheduler import start_daily_scheduler

  # Initialize ProductionLogger
  prod_logger = ProductionLogger(log_dir="logs")

  # Start the scheduler
  scheduler_thread = start_daily_scheduler(prod_logger)
  # scheduler_thread is a daemon thread that runs in the background
"""

import schedule
import time
import threading
from datetime import datetime
from production_logger import ProductionLogger


def daily_export_job(prod_logger: ProductionLogger):
    """
    Job that runs at 6 AM daily.
    Exports production logs from the last 24 hours to CSV.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Scheduler] Running daily export at {current_time}")

    result = prod_logger.export_production_log_to_csv()

    if result:
        print(f"[Scheduler] Successfully exported: {result}")
    else:
        print(f"[Scheduler] Export completed (no new data to export)")


def scheduler_loop(prod_logger: ProductionLogger, stop_event: threading.Event):
    """
    Runs the scheduler in a loop.
    Processes scheduled jobs every minute.
    """
    # Schedule the job to run at 6:00 AM every day
    schedule.every().day.at("06:00").do(daily_export_job, prod_logger)

    print("[Scheduler] Daily export scheduled for 06:00 AM")

    while not stop_event.is_set():
        schedule.run_pending()
        # Check every minute for pending jobs
        time.sleep(60)


def start_daily_scheduler(prod_logger: ProductionLogger, stop_event: threading.Event = None):
    """
    Start the daily 6 AM scheduler in a daemon thread.

    Parameters
    ----------
    prod_logger : ProductionLogger
        Instance of ProductionLogger to call export_production_log_to_csv()
    stop_event : threading.Event, optional
        Event to signal thread shutdown. If None, creates a new one.

    Returns
    -------
    scheduler_thread : threading.Thread
        The scheduler daemon thread (already started)
    stop_event : threading.Event
        Event to stop the scheduler
    """
    if stop_event is None:
        stop_event = threading.Event()

    scheduler_thread = threading.Thread(
        target=scheduler_loop,
        args=(prod_logger, stop_event),
        daemon=True,
        name="DailyScheduler"
    )
    scheduler_thread.start()

    return scheduler_thread, stop_event


if __name__ == "__main__":
    # Example usage
    prod_logger = ProductionLogger(log_dir="logs")
    scheduler_thread, stop_event = start_daily_scheduler(prod_logger)

    print("Scheduler started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        stop_event.set()
        scheduler_thread.join(timeout=5)
        print("Scheduler stopped.")
