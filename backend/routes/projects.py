# backend/routes/projects.py
from flask import Blueprint, render_template, request, redirect, url_for
from backend.db import get_db_connection
from datetime import datetime

bp = Blueprint("projects", __name__, url_prefix="/projects")

# ------------------------------------------------------------------- project list
@bp.route("/")
def list_projects():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT p.project_id, p.project_name, g.group_name,
               p.deadline, p.estimated_hours_needed
        FROM projects p JOIN groups g ON p.group_id = g.group_id
        ORDER BY p.project_id;
    """)
    projects = cur.fetchall(); cur.close(); conn.close()
    return render_template("projects/list.html", projects=projects)

# ---------------------------------------------------------------- create project
@bp.route("/new", methods=["GET", "POST"], endpoint="new_project")
def new_project():
    conn = get_db_connection(); cur = conn.cursor()
    if request.method == "POST":
        name      = request.form["name"]
        group_id  = int(request.form["group_id"])
        deadline  = datetime.fromisoformat(request.form["deadline"])
        hours     = int(request.form["hours"])
        cur.execute("""
            INSERT INTO projects(project_name,group_id,deadline,estimated_hours_needed)
            VALUES (%s,%s,%s,%s)
        """, (name, group_id, deadline, hours))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for("projects.list_projects"))

    cur.execute("SELECT group_id, group_name FROM groups ORDER BY group_name")
    groups = cur.fetchall(); cur.close(); conn.close()

    return render_template("projects/new.html", groups=groups)

# ---------------------------------------------------------------- edit project
@bp.route("/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        gid  = int(request.form["group_id"])
        ddl  = datetime.fromisoformat(request.form["deadline"])
        hrs  = int(request.form["hours"])
        cur.execute("""
            UPDATE projects
            SET project_name=%s, group_id=%s, deadline=%s, estimated_hours_needed=%s
            WHERE project_id=%s
        """, (name, gid, ddl, hrs, project_id))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for("projects.list_projects"))

    cur.execute("""
        SELECT project_name, group_id, deadline, estimated_hours_needed
        FROM projects WHERE project_id=%s
    """, (project_id,))
    proj = cur.fetchone()
    cur.execute("SELECT group_id, group_name FROM groups ORDER BY group_name")
    groups = cur.fetchall(); cur.close(); conn.close()
    if not proj:
        return "Not found", 404

    return render_template("projects/edit.html", proj=proj, groups=groups)

# ---------------------------------------------------------------- delete project
@bp.route("/delete/<int:project_id>")
def delete_project(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE project_id=%s", (project_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for("projects.list_projects"))

# ---------------------------------------------------------------- suggest slots
@bp.route("/suggest/<int:project_id>")
def suggest_slots(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT project_name, deadline, estimated_hours_needed FROM projects WHERE project_id=%s", (project_id,))
    proj = cur.fetchone()
    if not proj:
        cur.close(); conn.close()
        return "Project not found", 404
    pname, ddl, hrs_needed = proj

    # get all members of the project's group
    cur.execute("""
        SELECT u.user_id FROM memberships me
        JOIN users u ON me.user_id=u.user_id
        JOIN projects p ON me.group_id=p.group_id
        WHERE p.project_id=%s
    """, (project_id,))
    members = [r[0] for r in cur.fetchall()]
    if not members:
        cur.close(); conn.close()
        return "No members in project", 404

    # availability up to deadline
    cur.execute("""
        SELECT user_id, start_time, end_time
        FROM availabilities
        WHERE user_id = ANY(%s) AND end_time <= %s
        ORDER BY start_time
    """, (members, ddl))
    rows = cur.fetchall(); cur.close(); conn.close()

    per = {}
    for uid, s, e in rows:
        per.setdefault(uid, []).append((s, e))

    def overlap(a, b):
        s = max(a[0], b[0]); e = min(a[1], b[1])
        return (s, e) if s < e else None
        
    common = per.get(members[0], [])[:]
    for uid in members[1:]:
        new = [ov for a in common for b in per.get(uid, []) if (ov := overlap(a, b))]
        common = new
        if not common:
            break

    suggestions = [(s, e) for s, e in common if (e - s).total_seconds() >= 3600]
    suggestions.sort(); suggestions = suggestions[:5]

    return render_template("projects/suggest.html", 
                           pname=pname, ddl=ddl, hrs_needed=hrs_needed,
                           suggestions=suggestions, project_id=project_id)

# ---------------------------------------------------------------- book session
@bp.route("/book/<int:project_id>", methods=["POST"], endpoint="book_session")
def book_session(project_id):
    start = datetime.fromisoformat(request.form["start"])
    end   = datetime.fromisoformat(request.form["end"])
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO work_sessions(project_id, start_time, end_time)
        VALUES (%s, %s, %s)
    """, (project_id, start, end))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for("projects.list_projects"))
