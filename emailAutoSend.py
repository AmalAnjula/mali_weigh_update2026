#!/usr/bin/env python3
"""
emailAutoSend.py
================
Polls an inbox for emails whose subject starts with "sendme".
Expected subject format:
    sendme 20260210132435 20260310132435
              ^start         ^stop
              YYYYMMDDHHmmss

Steps:
  1. Fetch unread emails
  2. Reject any email whose subject doesn't start with "sendme" (sends a rejection reply)
  3. Parse start / stop datetime from the subject
  4. Query /logs/production.db for rows in that range
  5. Write a CSV temp file, attach it, send reply
  6. Delete the temp CSV
  7. Mark processed email as read / delete it

Config — edit the block below or set environment variables.
"""

import os
import re
import csv
import imaplib
import smtplib
import sqlite3
import tempfile
import logging

from datetime import datetime
from email import message_from_bytes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
import time

# ══════════════════════════════════════════════════════════════════
#  CONFIG  — change these or export as environment variables
# ══════════════════════════════════════════════════════════════════
IMAP_HOST   = os.getenv("EMAIL_IMAP_HOST",   "imap.gmail.com")
IMAP_PORT   = int(os.getenv("EMAIL_IMAP_PORT", "993"))
SMTP_HOST   = os.getenv("EMAIL_SMTP_HOST",   "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_USER  = os.getenv("EMAIL_USER",  "sprayer01weighingpo@gmail.com")
EMAIL_PASS  = os.getenv("EMAIL_PASS",  "kqwalbufyepwfnpt")
EMAIL_NAME  = os.getenv("EMAIL_NAME",  "OLS Production System")

 

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
DB_PATH      = os.path.join(LOG_DIR, "production.db")
 
POLL_EVERY  = int(os.getenv("POLL_EVERY_SEC", "5"))   # seconds between inbox checks

# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("emailAutoSend")

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
SUBJECT_PREFIX = "sendme"
DATETIME_FMT   = "%Y%m%d%H%M%S"   # YYYYMMDDHHmmss

def _parse_subject(subject: str):
    """
    Parses 'sendme 20260210132435 20260310132435' from a subject line.
    Returns (start_dt, stop_dt) as datetime objects, or raises ValueError.
    Subject must START with 'sendme' (case-insensitive).
    """
    subject = subject.strip()
    if not subject.lower().startswith(SUBJECT_PREFIX):
        raise ValueError("Subject does not start with 'sendme'")

    # Extract exactly two 14-digit timestamps
    tokens = re.findall(r"\d{14}", subject)
    if len(tokens) < 2:
        raise ValueError(
            f"Expected two timestamps (YYYYMMDDHHmmss) in subject, got: {subject!r}"
        )

    start_dt = datetime.strptime(tokens[0], DATETIME_FMT)
    stop_dt  = datetime.strptime(tokens[1], DATETIME_FMT)

    if start_dt >= stop_dt:
        raise ValueError(
            f"Start datetime ({start_dt}) must be before stop datetime ({stop_dt})"
        )

    return start_dt, stop_dt


def _query_db(start_dt: datetime, stop_dt: datetime):
    """
    Queries production_log for rows between start_dt and stop_dt (inclusive).
    Returns list of dicts.
    """
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    stop_str  = stop_dt.strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """SELECT timestamp, product, initial_weight,
                      required_weight, final_weight, status, reason
               FROM production_log
               WHERE timestamp BETWEEN ? AND ?
               ORDER BY timestamp ASC""",
            (start_str, stop_str),
        ).fetchall()

    return [dict(r) for r in rows]


def _write_csv(rows: list, start_dt: datetime, stop_dt: datetime) -> str:
    """
    Writes rows to a temp CSV file.
    Returns the file path.
    """
    prefix = f"production_{start_dt.strftime('%Y%m%d%H%M%S')}_{stop_dt.strftime('%Y%m%d%H%M%S')}_"
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".csv")
    os.close(fd)

    fieldnames = [
        "timestamp", "product", "initial_weight",
        "required_weight", "final_weight", "status", "reason",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


def _send_email(to_addr: str, subject: str, body: str, attachment_path: str = None):
    """Sends an email via SMTP, with an optional file attachment."""
    msg = MIMEMultipart()
    msg["From"]    = formataddr((EMAIL_NAME, EMAIL_USER))
    msg["To"]      = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path:
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_addr, msg.as_string())

    log.info("Email sent → %s | Subject: %s", to_addr, subject)


def _get_sender(email_msg) -> str:
    """Extracts the sender's email address from a parsed email message."""
    from_field = email_msg.get("From", "")
    match = re.search(r"<(.+?)>", from_field)
    return match.group(1) if match else from_field.strip()


def _get_subject(email_msg) -> str:
    """Returns decoded subject string."""
    from email.header import decode_header
    raw = email_msg.get("Subject", "")
    parts = decode_header(raw)
    decoded = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded += part.decode(enc or "utf-8", errors="replace")
        else:
            decoded += part
    return decoded.strip()


# ══════════════════════════════════════════════════════════════════
#  MAIN PROCESSING
# ══════════════════════════════════════════════════════════════════
def process_email(uid: bytes, email_msg):
    """Full pipeline for one email."""
    sender  = _get_sender(email_msg)
    subject = _get_subject(email_msg)

    log.info("Processing email from %s | Subject: %r", sender, subject)

    # ── 1. Reject if subject doesn't start with 'sendme' ──────────
    if not subject.strip().lower().startswith(SUBJECT_PREFIX):
        log.warning("Rejected — subject does not start with 'sendme': %r", subject)
        _send_email(
            to_addr = sender,
            subject = "Re: " + subject,
            body    = (
                "Your request was rejected.\n\n"
                "Email subject must start with 'sendme' followed by two timestamps.\n\n"
                "Example:\n"
                "  sendme 20260210132435 20260310132435\n"
                "           ^start(YYYYMMDDHHmmss)  ^stop(YYYYMMDDHHmmss)\n\n"
                "-- OLS Production System"
            ),
        )
        return

    # ── 2. Parse start/stop datetimes ─────────────────────────────
    try:
        start_dt, stop_dt = _parse_subject(subject)
    except ValueError as exc:
        log.warning("Bad subject format: %s", exc)
        _send_email(
            to_addr = sender,
            subject = "Re: " + subject,
            body    = (
                f"Could not parse your request.\n\nError: {exc}\n\n"
                "Correct format:\n"
                "  sendme 20260210132435 20260310132435\n"
                "-- OLS Production System"
            ),
        )
        return

    log.info("Date range: %s → %s", start_dt, stop_dt)

    # ── 3. Query database ──────────────────────────────────────────
    try:
        rows = _query_db(start_dt, stop_dt)
    except Exception as exc:
        log.error("DB query failed: %s", exc)
        _send_email(
            to_addr = sender,
            subject = "Re: " + subject,
            body    = f"Database error: {exc}\n\n-- OLS Production System",
        )
        return

    log.info("Rows found: %d", len(rows))

    # ── 4. Handle empty result ─────────────────────────────────────
    if not rows:
        _send_email(
            to_addr = sender,
            subject = "Re: " + subject,
            body    = (
                f"No production records found between:\n"
                f"  Start : {start_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Stop  : {stop_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "-- OLS Production System"
            ),
        )
        return

    # ── 5. Write CSV, send, delete ─────────────────────────────────
    csv_path = None
    try:
        csv_path = _write_csv(rows, start_dt, stop_dt)
        _send_email(
            to_addr         = sender,
            subject         = f"Re: {subject}",
            body            = (
                f"Please find attached the production log export.\n\n"
                f"  Start  : {start_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Stop   : {stop_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Records: {len(rows)}\n\n"
                "-- OLS Production System"
            ),
            attachment_path = csv_path,
        )
    except Exception as exc:
        log.error("Failed to send CSV email: %s", exc)
    finally:
        if csv_path and os.path.exists(csv_path):
            os.remove(csv_path)
            log.info("Temp CSV deleted: %s", csv_path)


def poll_inbox():
    """Connects to IMAP, fetches all UNSEEN emails, processes each one."""
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(EMAIL_USER, EMAIL_PASS)
            imap.select("INBOX")

            _, uids = imap.search(None, "UNSEEN")
            uid_list = uids[0].split()

            if not uid_list:
                log.debug("No new emails.")
                return

            log.info("Found %d unread email(s).", len(uid_list))

            for uid in uid_list:
                _, data = imap.fetch(uid, "(RFC822)")
                raw = data[0][1]
                email_msg = message_from_bytes(raw)

                try:
                    process_email(uid, email_msg)
                except Exception as exc:
                    log.error("Unhandled error processing email uid=%s: %s", uid, exc)
                finally:
                    # Mark as read regardless of success/failure
                    imap.store(uid, "+FLAGS", "\\Seen")

    except imaplib.IMAP4.error as exc:
        log.error("IMAP error: %s", exc)
    except Exception as exc:
        log.error("Unexpected error in poll_inbox: %s", exc)


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  OLS Email Auto-Send started")
    log.info("  Inbox  : %s @ %s", EMAIL_USER, IMAP_HOST)
    log.info("  DB     : %s", DB_PATH)
    log.info("  Poll   : every %ds", POLL_EVERY)
    log.info("=" * 55)

    while True:
        poll_inbox()
        time.sleep(POLL_EVERY)