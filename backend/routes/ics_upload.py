# backend/routes/ics_upload.py
from flask import Blueprint, request, render_template_string, redirect, url_for, flash
from backend.db import get_db_connection
from ics import Calendar
import io, psycopg2
from datetime import datetime, time, timedelta

bp = Blueprint("ics_upload", __name__, url_prefix="/ics")

@bp.route("/upload", methods=["GET", "POST"])
def upload_ics():
    conn = get_db_connection(); cur = conn.cursor()

    # list users for dropdown
    cur.execute("SELECT user_id, username FROM users ORDER BY username")
    users = cur.fetchall()

    if request.method == "POST":
        user_id   = int(request.form["user_id"])
        file      = request.files["icsfile"]
        if not file:
            flash("No file selected"); return redirect(request.url)

        # read & parse
        cal = Calendar(file.stream.read().decode("utf-8"))

        inserted = 0
        for ev in cal.events:
            if ev.begin.tzinfo:               # aware → make it local & naïve
                start = ev.begin.datetime.astimezone().replace(tzinfo=None)
                end   = ev.end.datetime.astimezone().replace(tzinfo=None)
            else:                             # already naïve
                start = ev.begin.datetime
                end   = ev.end.datetime

            desc  = ev.name or ev.description or ""
            cur.execute(
                "INSERT INTO busy_times(user_id,start_time,end_time,description)"
                "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (user_id, start, end, desc[:250])
            )
            inserted += 1

        conn.commit(); cur.close(); conn.close()
        flash(f"Imported {inserted} busy events.")
        generate_daily_availability(user_id)   # compute 08-20 free blocks
        return redirect(url_for("users.list_users"))

    cur.close(); conn.close()
    return render_template_string("""
      <h2>Upload .ics for user</h2>
      <form method="POST" enctype="multipart/form-data">
        User:
        <select name="user_id">
          {% for uid,uname in users %}
            <option value="{{ uid }}">{{ uname }}</option>
          {% endfor %}
        </select><br><br>
        <input type="file" name="icsfile" accept=".ics"><br><br>
        <button type="submit">Upload</button>
      </form>
      <a href="/">Home</a>
    """, users=users)

# ---------- helper: derive 08-20 availability each day -----------------------
def generate_daily_availability(user_id):
    """For each day that has at least one busy event, insert the gaps between
       08:00 and 20:00 as availability rows (source='auto')."""

    conn = get_db_connection(); cur = conn.cursor()

    # find date span of busy events
    cur.execute("""
        SELECT DATE(start_time), start_time, end_time
        FROM busy_times
        WHERE user_id=%s
        ORDER BY start_time
    """, (user_id,))
    rows = cur.fetchall()
    if not rows:
        cur.close(); conn.close(); return

    day_events = {}
    for d, s, e in rows:
        day_events.setdefault(d, []).append((s, e))

    eight = time(8, 0); twenty = time(20, 0)

    for day, events in day_events.items():
        day_start = datetime.combine(day, eight)
        day_end   = datetime.combine(day, twenty)

        # sort events, clip to 08-20
        events = [(max(day_start, s), min(day_end, e)) for s, e in events]
        events = [ev for ev in events if ev[0] < ev[1]]
        events.sort()

        # find gaps
        cursor = day_start
        for s, e in events:
            if s > cursor:
                cur.execute("""
                    INSERT INTO availabilities(user_id,start_time,end_time,source)
                    VALUES (%s,%s,%s,'auto') ON CONFLICT DO NOTHING
                """, (user_id, cursor, s))
            cursor = max(cursor, e)
        if cursor < day_end:
            cur.execute("""
                INSERT INTO availabilities(user_id,start_time,end_time,source)
                VALUES (%s,%s,%s,'auto') ON CONFLICT DO NOTHING
            """, (user_id, cursor, day_end))

    conn.commit(); cur.close(); conn.close()
