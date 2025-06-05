# backend/reminder.py
import os, smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

from backend.db import get_db_connection

# ---------- config from .env (optional) -------------------------------------
SMTP_HOST = os.getenv("EMAIL_HOST")
SMTP_PORT = int(os.getenv("EMAIL_PORT", "587"))
SMTP_USER = os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)


def send_email(to_addr: str, subject: str, body: str):
    """Send e-mail if SMTP is configured; otherwise print to console."""
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"]   = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        print(f"[REMINDER] To: {to_addr}\\nSubj: {subject}\\n{body}\\n")


def deadline_reminder_job():
    """Find projects with deadline < 24 h and notify participants."""
    now   = datetime.utcnow()
    upper = now + timedelta(hours=24)

    conn = get_db_connection(); cur = conn.cursor()

    # projects nearing deadline
    cur.execute(
        """
        SELECT p.project_id, p.project_name, p.deadline, g.group_id
        FROM projects p
        JOIN groups g ON g.group_id = p.group_id
        WHERE p.deadline BETWEEN %s AND %s
        """,
        (now, upper),
    )
    projects = cur.fetchall()

    for pid, pname, ddl, gid in projects:
        # participants first
        cur.execute(
            "SELECT u.email FROM participation pa JOIN users u ON u.user_id = pa.user_id WHERE pa.project_id=%s",
            (pid,),
        )
        emails = [r[0] for r in cur.fetchall()]

        # fall back to whole group
        if not emails:
            cur.execute(
                "SELECT u.email FROM memberships m JOIN users u ON u.user_id = m.user_id WHERE m.group_id=%s",
                (gid,),
            )
            emails = [r[0] for r in cur.fetchall()]

        subject = f"[CollabTool] Project '{pname}' deadline in 24 h"
        body    = f"Reminder: project '{pname}' is due at {ddl}.\n" \
                  "Make sure all tasks are wrapped up!"
        for mail in emails:
            send_email(mail, subject, body)

    cur.close(); conn.close()
