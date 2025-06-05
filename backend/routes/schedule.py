from flask import Blueprint, render_template, abort
from backend.db import get_db_connection
from datetime import timedelta

bp = Blueprint("schedule", __name__, url_prefix="/schedule")

@bp.route("/project/<int:project_id>")
def project_schedule(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT project_name, g.group_name, deadline, estimated_hours_needed
        FROM projects p JOIN groups g ON p.group_id=g.group_id
        WHERE project_id=%s
    """, (project_id,))
    project = cur.fetchone()
    if not project:
        cur.close(); conn.close(); abort(404)
    name, gname, deadline, hrs_needed = project

    # demo: list all availabilities of associated users
    cur.execute("""
        SELECT u.user_id, a.start_time, a.end_time
        FROM availabilities a
        JOIN users u ON a.user_id=u.user_id
        JOIN memberships m ON u.user_id=m.user_id
        JOIN projects p ON m.group_id=p.group_id
        WHERE p.project_id=%s AND a.end_time <= p.deadline
    """, (project_id,))
    rows = cur.fetchall(); cur.close(); conn.close()

    # simple "sum every user's hours" demo
    total = sum((e - s).total_seconds() for _, s, e in rows) / 3600

    return render_template("projects/schedule.html", 
                          name=name, gname=gname, deadline=deadline, 
                          hrs_needed=hrs_needed, total=total)
