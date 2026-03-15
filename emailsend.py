import smtplib
from email.message import EmailMessage
import os
import glob




def get_latest_csv(log_dir):

    files = glob.glob(os.path.join(log_dir, "*.csv"))

    if not files:
        return None

    latest_file = max(files, key=os.path.getmtime)

    return latest_file


def send_email(subject, body, to_email, attachment_path=None):

    sender_email = "amalanjula@gmail.com"
    sender_password = "ozzupunfywzbqqdp"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    msg.set_content(body)

    # Attach file
    if attachment_path and os.path.exists(attachment_path):

        with open(attachment_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)

        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="octet-stream",
            filename=file_name
        )

    # Send email
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

    print("Email sent successfully")


send_email("dfgrgsds","ddfgdgbdy","amalanjula@gmail.com")