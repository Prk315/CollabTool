# backend/reminder.py
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

from backend.db import SessionLocal
from backend.models import Project, Participation, Membership, User

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
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        print(f"[REMINDER] To: {to_addr}\nSubj: {subject}\n{body}\n")


def deadline_reminder_job():
    """Find projects with deadline < 24 h and notify participants."""
    now = datetime.utcnow()
    upper = now + timedelta(hours=24)

    with SessionLocal() as db:
        # projects nearing deadline
        projects = (
            db.query(
                Project.project_id,
                Project.project_name,
                Project.deadline,
                Project.group_id,
            )
            .filter(Project.deadline.between(now, upper))
            .all()
        )

        for pid, pname, ddl, gid in projects:
            # collect participant emails
            emails = [
                email
                for (email,) in (
                    db.query(User.email)
                    .join(Participation, Participation.user_id == User.user_id)
                    .filter(Participation.project_id == pid)
                    .all()
                )
            ]

            # fall back to whole group if no direct participants
            if not emails:
                emails = [
                    email
                    for (email,) in (
                        db.query(User.email)
                        .join(Membership, Membership.user_id == User.user_id)
                        .filter(Membership.group_id == gid)
                        .all()
                    )
                ]

            subject = f"[CollabTool] Project '{pname}' deadline in 24 h"
            body = (
                f"Reminder: project '{pname}' is due at {ddl}.\n"
                "Make sure all tasks are wrapped up!"
            )
            for mail in emails:
                send_email(mail, subject, body)
