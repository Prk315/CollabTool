# backend/routes/groups.py
from flask import Blueprint, request, redirect, render_template_string, url_for, flash, jsonify
import psycopg2
from backend.db import get_db_connection

bp = Blueprint("groups", __name__, url_prefix="/groups")

# ---------- LIST GROUPS ------------------------------------------------------
@bp.route("/")
def list_groups():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT group_id, group_name, description FROM groups ORDER BY group_id;")
    groups = cur.fetchall(); cur.close(); conn.close()
    return render_template_string("""
        <h2>Groups</h2>
        <ul>
        {% for gid, gname, desc in groups %}
          <li>
            <strong>{{ gname }}</strong> (ID {{ gid }}) {% if desc %}– {{ desc }}{% endif %}
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

# ---------- CREATE GROUP -----------------------------------------------------
@bp.route("/new", methods=["GET", "POST"])
def create_group():
    if request.method == "POST":
        name = request.form["group_name"]; desc = request.form["description"]
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO groups (group_name, description) VALUES (%s,%s)", (name, desc))
        conn.commit(); cur.close(); conn.close()
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

# ---------- VIEW GROUP & MEMBERS --------------------------------------------
@bp.route("/<int:group_id>")
def view_group(group_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT group_name, description FROM groups WHERE group_id=%s", (group_id,))
    group = cur.fetchone()
    cur.execute("""
        SELECT u.user_id, u.username
        FROM memberships m JOIN users u ON m.user_id=u.user_id
        WHERE m.group_id=%s ORDER BY u.username;
    """, (group_id,))
    members = cur.fetchall(); cur.close(); conn.close()
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

# ---------- ADD MEMBER -------------------------------------------------------
@bp.route("/<int:group_id>/add_member", methods=["GET", "POST"])
def add_member(group_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT group_name FROM groups WHERE group_id=%s", (group_id,))
    group = cur.fetchone()
    if not group: return "Group not found", 404
    cur.execute("SELECT user_id, username FROM users ORDER BY username")
    users = cur.fetchall()

    if request.method == "POST":
        user_id = int(request.form["user_id"])
        try:
            cur.execute("INSERT INTO memberships(user_id,group_id) VALUES(%s,%s)", (user_id, group_id))
            conn.commit()
        except psycopg2.Error:
            conn.rollback(); flash("User already in group or DB error")
        cur.close(); conn.close()
        return redirect(url_for("groups.view_group", group_id=group_id))

    cur.close(); conn.close()
    return render_template_string("""
        <h2>Add Member to {{ group[0] }}</h2>
        <form method="POST">
            <select name="user_id">
              {% for uid, uname in users %}
                <option value="{{ uid }}">{{ uname }}</option>
              {% endfor %}
            </select>
            <button type="submit">Add</button>
        </form>
        <a href="{{ url_for('groups.view_group', group_id=group_id) }}">Back</a>
    """, users=users, group=group, group_id=group_id)

# ---------- EDIT GROUP -------------------------------------------------------
@bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
def edit_group(group_id):
    conn = get_db_connection(); cur = conn.cursor()
    if request.method == "POST":
        new_n = request.form["group_name"]; new_d = request.form["description"]
        cur.execute("UPDATE groups SET group_name=%s, description=%s WHERE group_id=%s",
                    (new_n, new_d, group_id))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for("groups.list_groups"))
    cur.execute("SELECT group_name,description FROM groups WHERE group_id=%s", (group_id,))
    grp = cur.fetchone(); cur.close(); conn.close()
    if not grp: return "Group not found", 404
    return render_template_string("""
        <h2>Edit Group</h2>
        <form method="POST">
            Name: <input name="group_name" value="{{ grp[0] }}"><br>
            Description: <input name="description" value="{{ grp[1] }}"><br>
            <button type="submit">Save</button>
        </form>
        <a href="{{ url_for('groups.list_groups') }}">Back</a>
    """, grp=grp)

# ---------- DELETE GROUP -----------------------------------------------------
@bp.route("/<int:group_id>/delete")
def delete_group(group_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM groups WHERE group_id=%s", (group_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for("groups.list_groups"))

# ---------- GROUP CALENDAR (HTML) -------------------------------------------
@bp.route("/<int:group_id>/calendar")
def group_calendar_view(group_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT group_name FROM groups WHERE group_id=%s", (group_id,))
    g = cur.fetchone(); cur.close(); conn.close()
    if not g: return "Group not found", 404
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
      <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css" rel="stylesheet">
      <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js"></script>
      <style>body{font-family:Arial;padding:20px;}#calendar{max-width:900px;margin:0 auto;}</style>
    </head>
    <body>
      <h2>Group '{{ g[0] }}' – Common Free Time</h2>
      <div id="calendar"></div>
      <a href="{{ url_for('groups.list_groups') }}">Back</a>
      <script>
        document.addEventListener('DOMContentLoaded', async () => {
          const res  = await fetch('/groups/api/{{ group_id }}');
          const evts = await res.json();
          const cal  = new FullCalendar.Calendar(document.getElementById('calendar'),{
              initialView:'timeGridWeek',
              headerToolbar:{left:'prev,next today',center:'title',
                             right:'dayGridMonth,timeGridWeek,listWeek'},
              events: evts
          });
          cal.render();
        });
      </script>
    </body></html>
    """, group_id=group_id, g=g)


# ───────────────────────────────── JSON API ────────────────────────────────
@bp.route("/api/<int:group_id>")
def group_calendar_api(group_id):
    """
    • Blue  = time blocks when *all* group members are free
    • Purple = booked work-sessions for any project owned by this group
    """
    conn = get_db_connection(); cur = conn.cursor()

    # -------- members
    cur.execute("SELECT user_id FROM memberships WHERE group_id=%s", (group_id,))
    members = [r[0] for r in cur.fetchall()]
    if not members:
        cur.close(); conn.close(); return jsonify([])

    # -------- availabilities
    cur.execute(
        """
        SELECT user_id, start_time, end_time
        FROM availabilities
        WHERE user_id = ANY(%s)
        ORDER BY start_time
        """,
        (members,),
    )
    per = {}
    for uid, s, e in cur.fetchall():
        per.setdefault(uid, []).append((s, e))

    # intersect all members
    def overlap(a, b):
        s = max(a[0], b[0]); e = min(a[1], b[1])
        return (s, e) if s < e else None

    seed   = next((slots for slots in per.values() if slots), [])
    common = seed
    for uid in members:
        new = [ov for a in common for b in per.get(uid, []) if (ov := overlap(a, b))]
        common = new
        if not common:
            break

    free_events = [
        {
            "title": "ALL free",
            "start": s.isoformat(),
            "end":   e.isoformat(),
            "color": "blue",
        }
        for s, e in common
    ]

    # -------- work-sessions for projects of this group
    cur.execute(
        """
        SELECT ws.start_time, ws.end_time, p.project_name
        FROM work_sessions ws
        JOIN projects p ON p.project_id = ws.project_id
        WHERE p.group_id = %s
        """,
        (group_id,),
    )
    sessions = [
        {
            "title": f"Session: {pn}",
            "start": s.isoformat(),
            "end":   e.isoformat(),
            "color": "purple",
        }
        for s, e, pn in cur.fetchall()
    ]

    cur.close(); conn.close()
    return jsonify(free_events + sessions)
