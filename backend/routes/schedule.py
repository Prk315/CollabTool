from flask import Blueprint, render_template_string, abort
from backend.db import get_db_connection
from datetime import timedelta

bp = Blueprint("schedule", __name__, url_prefix="/schedule")

@bp.route("/project/<int:project_id>")
def project_schedule(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT p.project_name, p.deadline, p.estimated_hours_needed,
               g.group_id, g.group_name
        FROM projects p JOIN groups g ON p.group_id = g.group_id
        WHERE p.project_id = %s
    """, (project_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    name, deadline, hrs_needed, gid, gname = row

    # pull member availabilities before deadline
    cur.execute("SELECT user_id FROM memberships WHERE group_id = %s", (gid,))
    members = [r[0] for r in cur.fetchall()]
    if not members:
        return "Group has no members."

    cur.execute("""
        SELECT user_id, start_time, end_time
        FROM availabilities
        WHERE user_id = ANY(%s) AND end_time <= %s
        ORDER BY start_time
    """, (members, deadline))
    rows = cur.fetchall(); cur.close(); conn.close()

    # simple “sum every user’s hours” demo
    total = sum((e - s).total_seconds() for _, s, e in rows) / 3600
    status = "✅ enough time" if total >= hrs_needed else "❌ short of time"

    return render_template_string("""
        <h2>{{ name }}</h2>
        <p>Group {{ gname }} – deadline {{ deadline }}</p>
        <p>Hours needed: {{ hrs_needed }} &nbsp; | &nbsp; hours available (sum): {{ total|round(2) }}</p>
        <h3>{{ status }}</h3>
        <a href='/projects/'>Back to projects</a>
    """, **locals())
