from flask import Blueprint, render_template_string, url_for, abort
from backend.db import get_db_connection
from datetime import datetime, timedelta

bp = Blueprint("schedule", __name__, url_prefix="/schedule")

def intersect_two(a, b):
    """Intersect two [start, end) intervals. Return None if no overlap."""
    start = max(a[0], b[0])
    end   = min(a[1], b[1])
    return (start, end) if start < end else None

@bp.route('/project/<int:project_id>')
def project_schedule(project_id):
    conn = get_db_connection()
    cur  = conn.cursor()

    # 1) project meta
    cur.execute("""
        SELECT p.project_name, p.deadline, p.estimated_hours_needed, g.group_id, g.group_name
        FROM projects p
        JOIN groups  g ON p.group_id = g.group_id
        WHERE p.project_id = %s
    """, (project_id,))
    row = cur.fetchone()
    if not row:
        abort(404, "Project not found")

    pname, deadline, hours_needed, group_id, gname = row

    # 2) group members
    cur.execute("SELECT user_id FROM memberships WHERE group_id = %s", (group_id,))
    member_ids = [r[0] for r in cur.fetchall()]
    if not member_ids:
        abort(400, "No members in this group")

    # 3) availabilities for members before deadline
    cur.execute("""
        SELECT user_id, start_time, end_time
        FROM availabilities
        WHERE user_id = ANY(%s) AND end_time <= %s
        ORDER BY start_time
    """, (member_ids, deadline))
    slots = cur.fetchall()
    cur.close(); conn.close()

    # organise per user
    per_user = {}
    for uid, start, end in slots:
        per_user.setdefault(uid, []).append((start, end))

    # 4) compute overall intersection
    # start with first member’s slots
    member_iter = iter(per_user.values())
    common = next(member_iter, [])
    for others in member_iter:
        new_common = []
        for i in common:
            for j in others:
                ov = intersect_two(i, j)
                if ov:
                    new_common.append(ov)
        common = new_common
        if not common:
            break   # no overlap at all

    # 5) total overlapping hours
    overlap_hours = sum((i[1] - i[0]).total_seconds() for i in common) / 3600

    status = (
        "✅ On track"     if overlap_hours >= hours_needed else
        "⚠️ Tight fit"    if overlap_hours >= 0.75 * hours_needed else
        "❌ Not enough time"
    )

    return render_template_string("""
        <h2>Schedule Check: {{ pname }}</h2>
        <p><b>Group:</b> {{ gname }} ({{ member_count }} members)</p>
        <p><b>Deadline:</b> {{ deadline }}</p>
        <p><b>Estimated hours needed:</b> {{ hours_needed }}</p>
        <p><b>Total overlapping free hours:</b> {{ overlap_hours|round(2) }}</p>
        <h3>Status: {{ status }}</h3>
        <a href="/">Home</a>
    """,
        pname=pname,
        gname=gname,
        member_count=len(member_ids),
        deadline=deadline,
        hours_needed=hours_needed,
        overlap_hours=overlap_hours,
        status=status
    )
