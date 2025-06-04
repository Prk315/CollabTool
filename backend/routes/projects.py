# backend/routes/projects.py
from flask import Blueprint, render_template_string, request, redirect, url_for
from backend.db import get_db_connection
from datetime import datetime

bp = Blueprint("projects", __name__, url_prefix="/projects")

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
    return render_template_string("""
        <h2>Projects</h2>
        <a href='{{ url_for("projects.new_project") }}'>+ New project</a>
        <ul>
        {% for pid, name, gname, ddl, hrs in projects %}
          <li>
            <strong><a href='{{ url_for("schedule.project_schedule", project_id=pid) }}'>{{ name }}</a></strong>
            (Grp: {{ gname }}) – deadline {{ ddl.strftime('%Y-%m-%d %H:%M') }} – {{ hrs }} hrs
            [<a href='{{ url_for("projects.edit_project", project_id=pid) }}'>Edit</a>]
            [<a href='{{ url_for("projects.delete_project", project_id=pid) }}'>Del</a>]
            [<a href="{{ url_for('projects.suggest_slots', project_id=pid) }}">
             Suggest slots</a>]

          </li>
        {% endfor %}
        </ul>
        <a href='/'>Home</a>
    """, projects=projects)

# ---------- SUGGEST COMMON MEETING SLOTS ------------------------------------
@bp.route("/suggest/<int:project_id>")
def suggest_slots(project_id):
    """
    Show up to 5 candidate time-blocks (>= 1 h) where *all* project participants
    are free before the deadline.
    """
    conn = get_db_connection(); cur = conn.cursor()

    # project meta
    cur.execute("""
        SELECT project_name, deadline, estimated_hours_needed
        FROM projects
        WHERE project_id = %s
    """, (project_id,))
    row = cur.fetchone()
    if not row:
        return "Project not found", 404
    pname, ddl, hrs_needed = row

    # participants ----------------------------------------------
    cur.execute("SELECT user_id FROM participation WHERE project_id=%s", (project_id,))
    members = [r[0] for r in cur.fetchall()]

    if not members:
        # fallback: everyone in the project’s group
        cur.execute("SELECT group_id FROM projects WHERE project_id=%s", (project_id,))
        gid = cur.fetchone()[0]
        cur.execute("SELECT user_id FROM memberships WHERE group_id=%s", (gid,))
        members = [r[0] for r in cur.fetchall()]

    if not members:
        return "No participants or group members found."




    # pull all availability up to deadline
    cur.execute("""
        SELECT user_id, start_time, end_time
        FROM availabilities
        WHERE user_id = ANY(%s) AND end_time <= %s
        ORDER BY start_time
    """, (members, ddl))
    rows = cur.fetchall(); cur.close(); conn.close()

    # bucket by user
    per = {}
    for uid, s, e in rows:
        per.setdefault(uid, []).append((s, e))

    # helper
    def overlap(a, b):
        s = max(a[0], b[0]); e = min(a[1], b[1])
        return (s, e) if s < e else None

    # intersect all members
    common = per.get(members[0], [])[:]
    for uid in members[1:]:
        new = []
        for a in common:
            for b in per.get(uid, []):
                ov = overlap(a, b)
                if ov:
                    new.append(ov)
        common = new
        if not common:
            break

    # filter ≥ 1 h windows, trim to first 5
    suggestions = [(s, e) for s, e in common if (e - s).total_seconds() >= 3600]
    suggestions.sort()
    suggestions = suggestions[:5]

    return render_template_string("""
        <h2>Suggested slots for '{{ pname }}'</h2>
        <p>Deadline: {{ ddl }} &nbsp; | &nbsp; need {{ hrs_needed }} hours total</p>
        {% if suggestions %}
          <ul>
          {% for s, e in suggestions %}
            <li>{{ s.strftime('%Y-%m-%d %H:%M') }} → {{ e.strftime('%H:%M') }}
                ({{ ((e-s).total_seconds() // 3600)|int }} h)</li>
          {% endfor %}
          </ul>
        {% else %}
          <p><em>No common 1-hour slot found before deadline.</em></p>
        {% endif %}
        <a href="{{ url_for('projects.list_projects') }}">Back to projects</a>
    """, pname=pname, ddl=ddl, hrs_needed=hrs_needed, suggestions=suggestions)


@bp.route("/new", methods=["GET","POST"], endpoint="new_project")
def new_project():
    conn = get_db_connection(); cur = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        group_id = int(request.form["group_id"])
        deadline = datetime.fromisoformat(request.form["deadline"])
        hours = int(request.form["hours"])
        cur.execute("INSERT INTO projects(project_name,group_id,deadline,estimated_hours_needed) VALUES(%s,%s,%s,%s)", (name, group_id, deadline, hours))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for("projects.list_projects"))
    cur.execute("SELECT group_id,group_name FROM groups ORDER BY group_name"); groups=cur.fetchall(); cur.close(); conn.close()
    return render_template_string("""
        <h2>New Project</h2>
        <form method='POST'>
            Name: <input name='name' required><br>
            Group: <select name='group_id'>{% for gid,gname in groups %}<option value='{{ gid }}'>{{ gname }}</option>{% endfor %}</select><br>
            Deadline: <input type='datetime-local' name='deadline' required><br>
            Hours: <input type='number' name='hours' min='1' required><br>
            <button type='submit'>Create</button>
        </form>
        <a href='{{ url_for("projects.list_projects") }}'>Back</a>
    """, groups=groups)

@bp.route("/edit/<int:project_id>", methods=["GET","POST"])
def edit_project(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    if request.method == "POST":
        name=request.form["name"]; gid=int(request.form["group_id"]); ddl=datetime.fromisoformat(request.form["deadline"]); hrs=int(request.form["hours"])
        cur.execute("UPDATE projects SET project_name=%s, group_id=%s, deadline=%s, estimated_hours_needed=%s WHERE project_id=%s", (name,gid,ddl,hrs,project_id))
        conn.commit(); cur.close(); conn.close(); return redirect(url_for("projects.list_projects"))
    cur.execute("SELECT project_name,group_id,deadline,estimated_hours_needed FROM projects WHERE project_id=%s",(project_id,)); proj=cur.fetchone()
    cur.execute("SELECT group_id,group_name FROM groups ORDER BY group_name"); groups=cur.fetchall(); cur.close(); conn.close()
    if not proj: return "Not found",404
    return render_template_string("""
        <h2>Edit Project</h2>
        <form method='POST'>
            Name: <input name='name' value='{{ proj[0] }}'><br>
            Group: <select name='group_id'>{% for gid,gname in groups %}<option value='{{ gid }}' {% if gid==proj[1] %}selected{% endif %}>{{ gname }}</option>{% endfor %}</select><br>
            Deadline: <input type='datetime-local' name='deadline' value='{{ proj[2].strftime("%Y-%m-%dT%H:%M") }}'><br>
            Hours: <input type='number' name='hours' value='{{ proj[3] }}'><br>
            <button type='submit'>Save</button>
        </form>
        <a href='{{ url_for("projects.list_projects") }}'>Cancel</a>
    """, proj=proj, groups=groups)

@bp.route("/delete/<int:project_id>")
def delete_project(project_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE project_id=%s", (project_id,)); conn.commit(); cur.close(); conn.close()
    return redirect(url_for("projects.list_projects"))
