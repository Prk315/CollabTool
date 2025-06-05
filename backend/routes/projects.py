from flask import Blueprint, render_template_string, request, redirect, url_for
from backend.db import SessionLocal
from backend.models import Project, Group, Participation, WorkSession
from datetime import datetime
import re

bp = Blueprint("projects", __name__, url_prefix="/projects")

@bp.route("/")
def list_projects():
    with SessionLocal() as db:
        projects = (
            db.query(
                Project.project_id,
                Project.project_name,
                Group.group_name,
                Project.deadline,
                Project.estimated_hours_needed
            )
            .join(Group, Group.group_id == Project.group_id)
            .order_by(Project.project_id)
            .all()
        )
    return render_template_string("""
        <h2>Projects</h2>
        <a href='{{ url_for("projects.new_project") }}'>+ New project</a>
        <ul>
        {% for pid, name, gname, ddl, hrs in projects %}
          <li>
            <strong>
              <a href='{{ url_for("schedule.project_schedule", project_id=pid) }}'>
                {{ name }}
              </a>
            </strong>
            (Grp: {{ gname }}) – deadline {{ ddl.strftime('%Y-%m-%d %H:%M') }} – {{ hrs }} hrs
            [<a href='{{ url_for("projects.edit_project", project_id=pid) }}'>Edit</a>]
            [<a href='{{ url_for("projects.delete_project", project_id=pid) }}'>Del</a>]
            [<a href='{{ url_for("projects.suggest_slots", project_id=pid) }}'>Suggest slots</a>]
          </li>
        {% endfor %}
        </ul>
        <a href='/'>Home</a>
    """, projects=projects)

# ---------- NEW PROJECT ----------
@bp.route("/new", methods=["GET", "POST"], endpoint="new_project")
def new_project():
    with SessionLocal() as db:
        if request.method == "POST":
            name     = request.form["name"]
            pattern = re.compile("ab*")
            if re.match(pattern,name):
                print("Found a pattern match")
            else:
                print("Pattern was incorrect")
            group_id = int(request.form["group_id"])
            deadline = datetime.fromisoformat(request.form["deadline"])
            hours    = int(request.form["hours"])
            proj = Project(
                project_name=name,
                group_id=group_id,
                deadline=deadline,
                estimated_hours_needed=hours
            )
            db.add(proj)
            db.commit()
            return redirect(url_for("projects.list_projects"))

        groups = db.query(Group.group_id, Group.group_name).order_by(Group.group_name).all()
    return render_template_string("""
        <h2>New Project</h2>
        <form method='POST'>
            Name:   <input name='name' required><br>
            Group:  <select name='group_id'>
                        {% for gid, gname in groups %}
                          <option value='{{ gid }}'>{{ gname }}</option>
                        {% endfor %}
                     </select><br>
            Deadline: <input type='datetime-local' name='deadline' required><br>
            Hours:    <input type='number' name='hours' min='1' required><br>
            <button type='submit'>Create</button>
        </form>
        <a href='{{ url_for("projects.list_projects") }}'>Back</a>
    """, groups=groups)

# ---------- EDIT PROJECT ----------
@bp.route("/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    with SessionLocal() as db:
        if request.method == "POST":
            name   = request.form["name"]
            gid    = int(request.form["group_id"])
            ddl    = datetime.fromisoformat(request.form["deadline"])
            hrs    = int(request.form["hours"])
            proj   = db.query(Project).filter(Project.project_id == project_id).first()
            if proj:
                proj.project_name = name
                proj.group_id     = gid
                proj.deadline     = ddl
                proj.estimated_hours_needed = hrs
                db.commit()
            return redirect(url_for("projects.list_projects"))

        proj   = db.query(Project.project_name, Project.group_id, Project.deadline, Project.estimated_hours_needed)\
                   .filter(Project.project_id == project_id).first()
        groups = db.query(Group.group_id, Group.group_name).order_by(Group.group_name).all()

    if not proj:
        return "Not found", 404

    return render_template_string("""
        <h2>Edit Project</h2>
        <form method='POST'>
            Name:   <input name='name' value='{{ proj[0] }}'><br>
            Group:  <select name='group_id'>
                      {% for gid,gname in groups %}
                        <option value='{{ gid }}' {% if gid==proj[1] %}selected{% endif %}>
                          {{ gname }}
                        </option>
                      {% endfor %}
                    </select><br>
            Deadline: <input type='datetime-local' name='deadline' 
                     value='{{ proj[2].strftime("%Y-%m-%dT%H:%M") }}'><br>
            Hours:    <input type='number' name='hours' value='{{ proj[3] }}'><br>
            <button type='submit'>Save</button>
        </form>
        <a href='{{ url_for("projects.list_projects") }}'>Cancel</a>
    """, proj=proj, groups=groups)

# ---------- DELETE PROJECT ----------
@bp.route("/delete/<int:project_id>")
def delete_project(project_id):
    with SessionLocal() as db:
        proj = db.query(Project).filter(Project.project_id == project_id).first()
        if proj:
            db.delete(proj)
            db.commit()
    return redirect(url_for("projects.list_projects"))

# ---------- SUGGEST COMMON MEETING SLOTS ----------
@bp.route("/suggest/<int:project_id>")
def suggest_slots(project_id):
    """
    Show up to 5 candidate time-blocks (>= 1 h) where *all* project participants
    are free before the deadline. If no explicit participants, fallback to group members.
    """
    with SessionLocal() as db:
        row = db.query(
            Project.project_name,
            Project.deadline,
            Project.estimated_hours_needed,
            Project.group_id
        ).filter(Project.project_id == project_id).first()

        if not row:
            return "Project not found", 404

        pname, ddl, hrs_needed, gid = row

        members = [r[0] for r in
            db.query(Participation.user_id).filter(Participation.project_id == project_id).all()
        ]
        if not members:
            # fallback to group members
            members = [r[0] for r in 
                db.query(Membership.user_id).filter(Membership.group_id == gid).all()
            ]
        if not members:
            return "No participants or group members found."

        rows = (
            db.query(Availability.user_id, Availability.start_time, Availability.end_time)
              .filter(Availability.user_id.in_(members), Availability.end_time <= ddl)
              .order_by(Availability.start_time)
              .all()
        )

    # Bucket by user_id
    per = {}
    for uid, s, e in rows:
        per.setdefault(uid, []).append((s, e))

    def overlap(a, b):
        s = max(a[0], b[0]); e = min(a[1], b[1])
        return (s, e) if s < e else None

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

    suggestions = [(s, e) for s, e in common if (e - s).total_seconds() >= 3600]
    suggestions.sort()
    suggestions = suggestions[:5]

    return render_template_string("""
        <h2>Suggested slots for '{{ pname }}'</h2>
        <p>Deadline: {{ ddl }} &nbsp; | &nbsp; need {{ hrs_needed }} hours total</p>
        {% if suggestions %}
          <ul>
          {% for s, e in suggestions %}
            <li>
              {{ s.strftime('%Y-%m-%d %H:%M') }} → {{ e.strftime('%H:%M') }}
              ({{ ((e-s).total_seconds() // 3600)|int }} h)
              <form style="display:inline" method="POST"
                    action="{{ url_for('projects.book_session', project_id=project_id) }}">
                <input type="hidden" name="start" value="{{ s.isoformat() }}">
                <input type="hidden" name="end"   value="{{ e.isoformat() }}">
                <button type="submit">Book</button>
              </form>
            </li>
          {% endfor %}
          </ul>
        {% else %}
          <p><em>No common 1-hour slot before deadline.</em></p>
        {% endif %}
        <a href="{{ url_for('projects.list_projects') }}">Back</a>
    """, pname=pname, ddl=ddl, hrs_needed=hrs_needed,
       suggestions=suggestions, project_id=project_id)

# ---------- BOOK SESSION ----------
@bp.route("/book/<int:project_id>", methods=["POST"], endpoint="book_session")
def book_session(project_id):
    start = datetime.fromisoformat(request.form["start"])
    end   = datetime.fromisoformat(request.form["end"])
    with SessionLocal() as db:
        ws = WorkSession(project_id=project_id, start_time=start, end_time=end)
        db.add(ws)
        db.commit()
    return redirect(url_for("projects.list_projects"))
