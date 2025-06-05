from flask import Blueprint, request, redirect, render_template_string, url_for, flash, jsonify
from backend.db import SessionLocal
from backend.models import Group, User, Membership, Availability

bp = Blueprint("groups", __name__, url_prefix="/groups")

# ---------- LIST GROUPS ----------
@bp.route("/")
def list_groups():
    with SessionLocal() as db:
        groups = db.query(Group.group_id, Group.group_name, Group.description).order_by(Group.group_id).all()
    return render_template_string("""
        <h2>Groups</h2>
        <ul>
        {% for gid, gname, desc in groups %}
          <li>
            <strong>{{ gname }}</strong> (ID {{ gid }})
            {% if desc %}– {{ desc }}{% endif %}
              | <a href="{{ url_for('groups.view_group', group_id=gid) }}">View</a>
              | <a href="{{ url_for('groups.edit_group', group_id=gid) }}">Edit</a>
              | <a href="{{ url_for('groups.delete_group', group_id=gid) }}">Delete</a>
              | <a href="{{ url_for('groups.group_calendar_view', group_id=gid) }}">Calendar</a>
          </li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('groups.create_group') }}">Create new group</a> |
        <a href="/">Home</a>
    """, groups=groups)

# ---------- CREATE GROUP ----------
@bp.route("/new", methods=["GET", "POST"])
def create_group():
    if request.method == "POST":
        name = request.form["group_name"]
        desc = request.form["description"]
        with SessionLocal() as db:
            grp = Group(group_name=name, description=desc)
            db.add(grp)
            db.commit()
        return redirect(url_for("groups.list_groups"))

    return render_template_string("""
        <h2>Create Group</h2>
        <form method="POST">
            Group name: <input name="group_name" required><br>
            Description: <input name="description"><br>
            <button type="submit">Create</button>
        </form>
        <a href="{{ url_for('groups.list_groups') }}">Back</a>
    """)

# ---------- VIEW GROUP & MEMBERS ----------
@bp.route("/<int:group_id>")
def view_group(group_id):
    with SessionLocal() as db:
        group = db.query(Group.group_name, Group.description).filter(Group.group_id == group_id).first()
        members = (
            db.query(User.user_id, User.username)
              .join(Membership, Membership.user_id == User.user_id)
              .filter(Membership.group_id == group_id)
              .order_by(User.username)
              .all()
        )
    if not group:
        return "Group not found", 404

    return render_template_string("""
        <h2>Group: {{ group[0] }}</h2>
        <p>{{ group[1] }}</p>

        <h3>Members</h3>
        <ul>
        {% for uid, uname in members %}
            <li>{{ uname }} (ID {{ uid }})</li>
        {% else %}
            <li>No members yet.</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('groups.add_member', group_id=group_id) }}">Add member</a><br><br>
        <a href="{{ url_for('groups.list_groups') }}">Back</a>
    """, group=group, members=members, group_id=group_id)

# ---------- ADD MEMBER ----------
@bp.route("/<int:group_id>/add_member", methods=["GET", "POST"])
def add_member(group_id):
    with SessionLocal() as db:
        group = db.query(Group.group_name).filter(Group.group_id == group_id).first()
        if not group:
            return "Group not found", 404

        users = db.query(User.user_id, User.username).order_by(User.username).all()

        if request.method == "POST":
            user_id = int(request.form["user_id"])
            try:
                m = Membership(user_id=user_id, group_id=group_id)
                db.add(m)
                db.commit()
            except Exception:
                db.rollback()
                flash("User already in group or DB error")
            return redirect(url_for("groups.view_group", group_id=group_id))

    return render_template_string("""
        <h2>Add Member to {{ group[0] }}</h2>
        <form method="POST">
            <select name="user_id">
              {% for uid, uname in users %}
                <option value="{{ uid }}">{{ uname }}</option>
              {% endfor %}
            </select><br><br>
            <button type="submit">Add</button>
        </form>
        <a href="{{ url_for('groups.view_group', group_id=group_id) }}">Back</a>
    """, users=users, group=group, group_id=group_id)

# ---------- EDIT GROUP ----------
@bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
def edit_group(group_id):
    with SessionLocal() as db:
        if request.method == "POST":
            new_n = request.form["group_name"]
            new_d = request.form["description"]
            grp = db.query(Group).filter(Group.group_id == group_id).first()
            if grp:
                grp.group_name  = new_n
                grp.description = new_d
                db.commit()
            return redirect(url_for("groups.list_groups"))

        grp = db.query(Group.group_name, Group.description).filter(Group.group_id == group_id).first()
    if not grp:
        return "Group not found", 404

    return render_template_string("""
        <h2>Edit Group</h2>
        <form method="POST">
            Name: <input name="group_name" value="{{ grp[0] }}"><br>
            Description: <input name="description" value="{{ grp[1] }}"><br>
            <button type="submit">Save</button>
        </form>
        <a href="{{ url_for('groups.list_groups') }}">Back</a>
    """, grp=grp)

# ---------- DELETE GROUP ----------
@bp.route("/<int:group_id>/delete")
def delete_group(group_id):
    with SessionLocal() as db:
        grp = db.query(Group).filter(Group.group_id == group_id).first()
        if grp:
            db.delete(grp)
            db.commit()
    return redirect(url_for("groups.list_groups"))

# ---------- GROUP CALENDAR (HTML) ----------
@bp.route("/<int:group_id>/calendar")
def group_calendar_view(group_id):
    with SessionLocal() as db:
        g = db.query(Group.group_name).filter(Group.group_id == group_id).first()
    if not g:
        return "Group not found", 404

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
      <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css" rel="stylesheet">
      <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js"></script>
      <style>body{font-family:Arial;padding:20px;}#calendar{max-width:900px;margin:0 auto;}</style>
    </head>
    <body>
      <h2>Group '{{ g[0] }}' – Common Free Time & Booked Sessions</h2>
      <div id="calendar"></div>
      <a href="{{ url_for('groups.list_groups') }}">Back</a>
      <script>
        document.addEventListener('DOMContentLoaded', async () => {
          const res  = await fetch('/groups/api/{{ group_id }}');
          const evts = await res.json();
          const cal  = new FullCalendar.Calendar(document.getElementById('calendar'),{
              initialView:'timeGridWeek',
              headerToolbar:{
                left:'prev,next today',
                center:'title',
                right:'dayGridMonth,timeGridWeek,listWeek'
              },
              events: evts
          });
          cal.render();
        });
      </script>
    </body>
    </html>
    """, group_id=group_id, g=g)

# ---------- GROUP CALENDAR (JSON API) ----------
@bp.route("/api/<int:group_id>")
def group_calendar_api(group_id):
    """Return blue blocks where *all* members are free, plus purple booked work sessions."""
    with SessionLocal() as db:
        member_ids = [r[0] for r in 
            db.query(Membership.user_id).filter(Membership.group_id == group_id).all()
        ]
        if not member_ids:
            return jsonify([])

        avail_rows = (
            db.query(Availability.user_id, Availability.start_time, Availability.end_time)
              .filter(Availability.user_id.in_(member_ids))
              .order_by(Availability.start_time)
              .all()
        )

        # Bucket availabilities per user
        per = {}
        for uid, s, e in avail_rows:
            per.setdefault(uid, []).append((s, e))

        # Build “common free” intervals
        seed = next((slots for slots in per.values() if slots), [])
        if not seed:
            free_common = []
        else:
            free_common = seed[:]
            def overlap(a, b):
                s = max(a[0], b[0]); e = min(a[1], b[1])
                return (s, e) if s < e else None

            for uid in member_ids:
                slots = per.get(uid, [])
                new = []
                for a in free_common:
                    for b in slots:
                        ov = overlap(a, b)
                        if ov:
                            new.append(ov)
                free_common = new
                if not free_common:
                    break

        free_events = [
            {
              "title": "ALL free",
              "start": s.isoformat(),
              "end":   e.isoformat(),
              "color": "blue"
            }
            for s, e in free_common
        ]

        # Fetch all work_sessions for projects in this group
        work_sessions = (
            db.query(
              # use WorkSession alias if imported
              # We’ll import WorkSession and Project at top
            )
        )
    # Instead of raw SQL, we do a separate session query:
    from backend.models import WorkSession, Project
    with SessionLocal() as db2:
        session_rows = (
            db2.query(
                WorkSession.session_id,
                WorkSession.start_time,
                WorkSession.end_time,
                Project.project_name
            )
            .join(Project, Project.project_id == WorkSession.project_id)
            .filter(Project.group_id == group_id)
            .all()
        )

    booked_events = [
        {
          "title": f"Booked: {pname}",
          "start": s.isoformat(),
          "end":   e.isoformat(),
          "color": "purple"
        }
        for _, s, e, pname in session_rows
    ]

    return jsonify(free_events + booked_events)
