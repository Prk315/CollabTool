from flask import Blueprint, request, render_template_string, redirect, url_for, flash
from backend.db import SessionLocal
from backend.models import BusyTime, Availability
from ics import Calendar
from datetime import datetime, time as dtime

bp = Blueprint("ics_upload", __name__, url_prefix="/ics")

@bp.route("/upload", methods=["GET", "POST"])
def upload_ics():
    with SessionLocal() as db:
        users = db.query(
            # list of (user_id, username)
            # Use direct User import if needed, but here we pass an example to the template.
            # Let’s import User:
            __import__("backend.models", fromlist=["User"])
        )
    # Actually, do we need the above? Instead:
    with SessionLocal() as db:
        users = db.query(BusyTime.user_id).distinct().all()
        # But we want actual usernames, so:
        from backend.models import User
    with SessionLocal() as db:
        users = db.query(User.user_id, User.username).order_by(User.username).all()

    if request.method == "POST":
        user_id = int(request.form["user_id"])
        file    = request.files["icsfile"]
        if not file:
            flash("No file selected")
            return redirect(request.url)

        text = file.stream.read().decode("utf-8")
        try:
            cal = Calendar(text)
        except Exception:
            flash("Invalid .ics file")
            return redirect(request.url)

        inserted = 0
        with SessionLocal() as db2:
            for ev in cal.events:
                if ev.begin.tzinfo:
                    start = ev.begin.datetime.astimezone().replace(tzinfo=None)
                    end   = ev.end.datetime.astimezone().replace(tzinfo=None)
                else:
                    start = ev.begin.datetime
                    end   = ev.end.datetime

                desc = ev.name or ev.description or ""
                busy = BusyTime(
                    user_id=user_id,
                    start_time=start,
                    end_time=end,
                    description=desc[:250]
                )
                db2.add(busy)
                inserted += 1
            db2.commit()

        # After inserting busy_times, compute 08:00–20:00 availability gaps
        generate_daily_availability(user_id)

        flash(f"Imported {inserted} busy events.")
        return redirect(url_for("users.list_users"))

    return render_template_string("""
      <h2>Upload .ics for user</h2>
      <form method="POST" enctype="multipart/form-data">
        User:
        <select name="user_id">
          {% for uid, uname in users %}
            <option value="{{ uid }}">{{ uname }}</option>
          {% endfor %}
        </select><br><br>
        <input type="file" name="icsfile" accept=".ics"><br><br>
        <button type="submit">Upload</button>
      </form>
      <a href="/">Home</a>
    """, users=users)

# ---------- helper: derive 08-20 availability each day ----------
def generate_daily_availability(user_id):
    """
    For each day that has at least one busy event, insert the gaps between
    08:00 and 20:00 as Availability rows (source='auto').
    """
    from backend.db import SessionLocal

    with SessionLocal() as db:
        # Fetch all busy_times for this user, sorted
        from backend.models import BusyTime
        rows = db.query(
            BusyTime.start_time,
            BusyTime.end_time
        ).filter(BusyTime.user_id == user_id).order_by(BusyTime.start_time).all()

        if not rows:
            return

        # Organize by calendar date
        day_events = {}
        for s, e in rows:
            d = s.date()
            day_events.setdefault(d, []).append((s, e))

        eight  = dtime(hour=8, minute=0)
        twenty = dtime(hour=20, minute=0)

        for day, events in day_events.items():
            day_start = datetime.combine(day, eight)
            day_end   = datetime.combine(day, twenty)

            # Clip each busy event to [08:00, 20:00]
            clipped = [(max(day_start, s), min(day_end, e)) for s, e in events]
            clipped = [ev for ev in clipped if ev[0] < ev[1]]
            clipped.sort()

            cursor = day_start
            for s, e in clipped:
                if s > cursor:
                    av = Availability(
                        user_id=user_id,
                        start_time=cursor,
                        end_time=s,
                        source="auto"
                    )
                    db.add(av)
                cursor = max(cursor, e)

            if cursor < day_end:
                av = Availability(
                    user_id=user_id,
                    start_time=cursor,
                    end_time=day_end,
                    source="auto"
                )
                db.add(av)

        db.commit()
