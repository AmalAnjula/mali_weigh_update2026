"""
gmail_auto_reply.py
────────────────────────────────────────────────────────────────
Monitors a Gmail inbox every 5 minutes (+ IMAP IDLE for fast pickup).
When an email subject contains a date string (YYYY-MM-DD), it looks for
  /home/palmoil/stuff/logs/production_<date>.csv
and replies with the file attached.
If the file is missing or the subject is unrecognised, it sends an error reply.

Setup (one-time):
  pip install imapclient
  Enable "IMAP" in Gmail settings → See all settings → Forwarding and POP/IMAP
  Use an App Password (Google Account → Security → App Passwords).
"""

import imaplib
import smtplib
import email
import os
import re
import time
import threading
import logging
from email.message import EmailMessage
from datetime import datetime, timedelta

# ── CONFIG ────────────────────────────────────────────────────────────────────
GMAIL_USER     = "sprayer01weighingpo@gmail.com"
GMAIL_PASSWORD = "kqwalbufyepwfnpt"          # App Password (16-char)
LOG_DIR        = "/home/palmoil/stuff/logs"
POLL_INTERVAL  = 300                          # seconds between full polls
IMAP_HOST      = "imap.gmail.com"
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/home/palmoil/stuff/logs/auto_reply.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")   # matches YYYY-MM-DD


# ── HELPERS ───────────────────────────────────────────────────────────────────

def extract_date(subject: str):
    """Return 'YYYY-MM-DD' string if found in subject, else None."""
    m = DATE_PATTERN.search(subject)
    return m.group(1) if m else None


def csv_path_for_date(date_str: str):
    """Return expected CSV path for a given date string."""
    return os.path.join(LOG_DIR, f"production_{date_str}.csv")


def build_success_body(date_str: str, csv_path: str) -> str:
    return f"""Hi,

This is an automated reply from Raspberry Pi 5.

Your requested production report for {date_str} is attached.

File: {os.path.basename(csv_path)}

Have a nice day!

Regards,
RPI5 Palm Olein System
"""


def build_error_body(subject: str, reason: str) -> str:
    return f"""Hi,

This is an automated reply from Raspberry Pi 5.

Unfortunately we could not fulfil your request.

  Original subject : {subject}
  Reason           : {reason}

Please make sure the email subject contains a valid date in the format
  YYYY-MM-DD
For example:  production_2026-03-25

If the problem persists, please contact your admin.

Regards,
RPI5  Palm Olein System
"""


def send_reply(to_addr: str, original_subject: str,
               body: str, attachment_path: str = None):
    """Send a reply email, optionally with a CSV attachment."""
    reply_subject = f"Re: {original_subject}"

    msg = EmailMessage()
    msg["Subject"] = reply_subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = to_addr
    msg.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=os.path.basename(attachment_path),
        )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_USER, GMAIL_PASSWORD)
        smtp.send_message(msg)

    log.info("Reply sent to %s | Subject: %s", to_addr, reply_subject)


# ── CORE LOGIC ────────────────────────────────────────────────────────────────

def process_message(imap: imaplib.IMAP4_SSL, uid: bytes):
    """
    Fetch one message by UID, decide what to reply, mark it as seen.
    """
    res, data = imap.uid("fetch", uid, "(RFC822)")
    if res != "OK" or not data or data[0] is None:
        log.warning("Could not fetch UID %s", uid)
        return

    raw = data[0][1]
    msg = email.message_from_bytes(raw)

    subject  = msg.get("Subject", "").strip()
    from_hdr = msg.get("From", "").strip()

    # Extract a plain email address from the From header
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", from_hdr)
    sender = m.group(0) if m else from_hdr

    log.info("Processing email | From: %s | Subject: %s", sender, subject)

    date_str = extract_date(subject)

    if not date_str:
        reason = (
            "No valid date (YYYY-MM-DD) found in the subject line."
        )
        log.warning("No date in subject '%s' → sending error reply", subject)
        send_reply(sender, subject, build_error_body(subject, reason))
    else:
        csv_path = csv_path_for_date(date_str)
        if os.path.exists(csv_path):
            log.info("Found CSV: %s → attaching to reply", csv_path)
            send_reply(
                sender, subject,
                build_success_body(date_str, csv_path),
                attachment_path=csv_path,
            )
        else:
            reason = (
                f"Production file for {date_str} not found on this device.\n"
                f"  Expected path: {csv_path}"
            )
            log.warning("CSV not found for %s → sending error reply", date_str)
            send_reply(sender, subject, build_error_body(subject, reason))

    # Mark the message as Seen so we don't process it again
    imap.uid("store", uid, "+FLAGS", "\\Seen")


def fetch_unseen(imap: imaplib.IMAP4_SSL):
    """Search for all UNSEEN messages and process each one."""
    imap.select("INBOX")
    res, data = imap.uid("search", None, "UNSEEN")
    if res != "OK":
        return

    uids = data[0].split()
    if not uids:
        log.debug("No new messages.")
        return

    log.info("Found %d unseen message(s).", len(uids))
    for uid in uids:
        try:
            process_message(imap, uid)
        except Exception as exc:
            log.error("Error processing UID %s: %s", uid, exc)


# ── LOG CLEANUP ───────────────────────────────────────────────────────────────

def delete_old_logs(days: int = 7):
    """Delete .csv and .log files in LOG_DIR older than `days` days."""
    cutoff = datetime.now() - timedelta(days=days)
    for filename in os.listdir(LOG_DIR):
        if not (filename.endswith(".csv") or filename.endswith(".log")):
            continue
        filepath = os.path.join(LOG_DIR, filename)
        modified = datetime.fromtimestamp(os.path.getmtime(filepath))
        if modified < cutoff:
            os.remove(filepath)
            log.info("Deleted old file: %s (last modified: %s)", filename, modified.date())


# ── IMAP IDLE (fast receive) ──────────────────────────────────────────────────

def idle_loop(stop_event: threading.Event):
    """
    Maintain a persistent IMAP connection with IDLE.
    When the server signals a new message, fetch_unseen() is called.
    Falls back gracefully if IDLE is unsupported.
    """
    while not stop_event.is_set():
        try:
            log.info("IDLE: connecting to Gmail IMAP…")
            imap = imaplib.IMAP4_SSL(IMAP_HOST)
            imap.login(GMAIL_USER, GMAIL_PASSWORD)
            imap.select("INBOX")

            # Check IDLE capability
            res, caps = imap.capability()
            supports_idle = b"IDLE" in caps[0].upper()

            if supports_idle:
                log.info("IDLE: server supports IDLE — listening for new mail…")
                while not stop_event.is_set():
                    # Send IDLE command
                    tag = imap._new_tag().decode()
                    imap.send(f"{tag} IDLE\r\n".encode())

                    # Wait up to 28 minutes (RFC 2177 recommends < 29 min)
                    imap.sock.settimeout(28 * 60)
                    idle_start = time.time()

                    try:
                        while True:
                            line = imap.readline()
                            if not line:
                                break
                            decoded = line.decode(errors="replace").strip()
                            log.debug("IDLE response: %s", decoded)
                            if "EXISTS" in decoded or "RECENT" in decoded:
                                log.info("IDLE: new mail signal received.")
                                break
                            # 28-min refresh
                            if time.time() - idle_start > 27 * 60:
                                break
                    except Exception as idle_exc:
                        log.warning("IDLE read error: %s", idle_exc)

                    # Send DONE to exit IDLE mode
                    imap.send(b"DONE\r\n")
                    # Consume the tagged OK response
                    imap.readline()

                    # Now fetch unseen
                    fetch_unseen(imap)

            else:
                log.info("IDLE not supported — using poll-only mode.")
                while not stop_event.is_set():
                    fetch_unseen(imap)
                    stop_event.wait(POLL_INTERVAL)

            imap.logout()

        except Exception as exc:
            log.error("IDLE loop error: %s — reconnecting in 30 s", exc)
            time.sleep(30)


# ── POLL THREAD (safety net every 5 min) ─────────────────────────────────────

def poll_loop(stop_event: threading.Event):
    """
    Independent polling thread that runs every POLL_INTERVAL seconds.
    Acts as a safety net in case the IDLE thread misses something.
    """
    while not stop_event.is_set():
        stop_event.wait(POLL_INTERVAL)
        if stop_event.is_set():
            break
        try:
            log.info("Poll: checking inbox…")
            imap = imaplib.IMAP4_SSL(IMAP_HOST)
            imap.login(GMAIL_USER, GMAIL_PASSWORD)
            fetch_unseen(imap)
            imap.logout()
            delete_old_logs(days=7)
        except Exception as exc:
            log.error("Poll error: %s", exc)


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=== Gmail Auto-Reply Bot starting up ===")
    log.info("Monitoring: %s", GMAIL_USER)
    log.info("Log dir   : %s", LOG_DIR)
    log.info("Poll every: %d seconds", POLL_INTERVAL)

    stop_event = threading.Event()

    idle_thread = threading.Thread(target=idle_loop, args=(stop_event,), daemon=True)
    poll_thread = threading.Thread(target=poll_loop, args=(stop_event,), daemon=True)

    idle_thread.start()
    poll_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down…")
        stop_event.set()
        idle_thread.join(timeout=5)
        poll_thread.join(timeout=5)
        log.info("Bye.")