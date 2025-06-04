# backend/routes/ics_upload.py
from flask import Blueprint, request, render_template_string, redirect, url_for, flash
from backend.db import get_db_connection
from ics import Calendar
import psycopg2
from datetime import datetime, time

bp = Blueprint("ics_upload", __name__, url_prefix="/ics")

# -------------------------------------------------------------------- helpers
def merge_spans(spans):
    """[(start,end), …] → merged, non-overlapping, sorted list."""
    if not spans:
        return []
    spans.sort()
    merged = [spans[0]]
    for s, e in spans[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:               # overlap → extend
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged

def generate_daily_availability(user_id):
    """
    Derive 08:00-20:00 availability for every day that has busy events,
    subtracting the merged busy spans.
    Rows are inserted with source='auto'.
    """
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT DATE(start_time), start_time, end_time
        FROM busy_times
        WHERE user_id=%s
        ORDER BY start_time
    """, (user_id,))
    rows = cur.fetchall()
    if not rows:
        cur.close(); conn.close(); return

    from collections import defaultdict
    by_day = defaultdict(list)
    for d, s, e in rows:
        by_day[d].append((s, e))

    eight   = time(8, 0)
    twenty  = time(20, 0)

    for day, events in by_day.items():
        day_start = datetime.combine(day, eight)
        day_end   = datetime.combine(day, twenty)

        # clip to 08-20 and merge overlaps
        merged_busy = merge_spans([
            (max(day_start, s), min(day_end, e))
            for s, e in events if s < e
        ])

        cursor = day_start
        for s, e in merged_busy:
            if s > cursor:
                cur.execute("""
                    INSERT INTO availabilities(user_id,start_time,end_time,source)
                    VALUES (%s,%s,%s,'auto')
                    ON CONFLICT DO NOTHING
                """, (user_id, cursor, s))
            cursor = max(cursor, e)

        if cursor < day_end:
            cur.execute("""
                INSERT INTO availabilities(user_id,start_time,end_time,source)
                VALUES (%s,%s,%s,'auto')
                ON CONFLICT DO NOTHING
            """, (user_id, cursor, day_end))

    conn.commit(); cur.close(); conn.close()

# ---------------------------------------------------------------- upload form
@bp.route("/upload", methods=["GET", "POST"])
def upload_ics():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id, username FROM users ORDER BY username")
    users = cur.fetchall()

    if request.method == "POST":
        user_id = int(request.form["user_id"])
        file    = request.files.get("icsfile")
        if not file or not file.filename.endswith(".ics"):
            flash("Select a .ics file"); return redirect(request.url)

        cal     = Calendar(file.stream.read().decode("utf-8"))
        cal_id  = file.filename.rsplit(".", 1)[0] or "default"

        inserted = 0
        spans    = []

        for ev in cal.events:
            # handle aware / naive datetimes
            if ev.begin.tzinfo:
                start = ev.begin.datetime.astimezone().replace(tzinfo=None)
                end   = ev.end.datetime.astimezone().replace(tzinfo=None)
            else:
                start = ev.begin.datetime
                end   = ev.end.datetime
            if start >= end:
                continue
            spans.append((start, end))

        for s, e in merge_spans(spans):
            cur.execute("""
                INSERT INTO busy_times(user_id,start_time,end_time,description,calendar_id)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
            """, (user_id, s, e, cal_id, cal_id))
            inserted += 1

        conn.commit(); cur.close(); conn.close()
        flash(f"Imported {inserted} events from '{file.filename}'.")
        generate_daily_availability(user_id)
        return redirect(url_for("users.list_users"))

    cur.close(); conn.close()
    return render_template_string("""
        <h2>Upload calendar (.ics)</h2>
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
