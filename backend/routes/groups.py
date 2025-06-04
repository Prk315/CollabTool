from flask import Blueprint, request, redirect, render_template_string, url_for, flash
import psycopg2
from backend.db import get_db_connection

bp = Blueprint('groups', __name__, url_prefix='/groups')


# ---------- LIST GROUPS ----------
@bp.route('/')
def list_groups():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT group_id, group_name, description FROM groups ORDER BY group_id;")
    groups = cur.fetchall()
    cur.close(); conn.close()
    return render_template_string("""
        <h2>Groups</h2>
        <ul>
        {% for gid, gname, desc in groups %}
          <li>
            <strong>{{ gname }}</strong> (ID: {{ gid }})
            {% if desc %} – {{ desc }}{% endif %}
            |
            <a href="{{ url_for('groups.view_group', group_id=gid) }}">View</a>
            |
            <a href="{{ url_for('groups.edit_group', group_id=gid) }}">Edit</a>
            |
            <a href="{{ url_for('groups.delete_group', group_id=gid) }}">Delete</a>
          </li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('groups.create_group') }}">Create new group</a> |
        <a href="/">Home</a>
    """, groups=groups)


# ---------- CREATE GROUP ----------
@bp.route('/new', methods=['GET', 'POST'])
def create_group():
    if request.method == 'POST':
        name = request.form['group_name']
        desc = request.form['description']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO groups (group_name, description) VALUES (%s, %s)", (name, desc))
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('groups.list_groups'))

    return render_template_string("""
        <h2>Create Group</h2>
        <form method="POST">
            Group name: <input name="group_name" required><br>
            Description: <input name="description"><br>
            <button type="submit">Create</button>
        </form>
        <a href="{{ url_for('groups.list_groups') }}">Back to groups</a>
    """)


# ---------- VIEW GROUP + MEMBERS ----------
@bp.route('/<int:group_id>')
def view_group(group_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch group info
    cur.execute("SELECT group_name, description FROM groups WHERE group_id = %s", (group_id,))
    group = cur.fetchone()

    # Fetch members
    cur.execute("""
        SELECT u.user_id, u.username
        FROM memberships m
        JOIN users u ON m.user_id = u.user_id
        WHERE m.group_id = %s
        ORDER BY u.username;
    """, (group_id,))
    members = cur.fetchall()

    cur.close(); conn.close()
    if not group:
        return "Group not found", 404

    return render_template_string("""
        <h2>Group: {{ group[0] }}</h2>
        <p>{{ group[1] }}</p>

        <h3>Members</h3>
        <ul>
        {% for uid, uname in members %}
            <li>{{ uname }} (ID: {{ uid }})</li>
        {% else %}
            <li>No members yet.</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('groups.add_member', group_id=group_id) }}">Add Member</a><br><br>
        <a href="{{ url_for('groups.list_groups') }}">Back to groups</a>
    """, group=group, members=members, group_id=group_id)


# ---------- ADD MEMBER ----------
@bp.route('/<int:group_id>/add_member', methods=['GET', 'POST'])
def add_member(group_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT group_name FROM groups WHERE group_id = %s", (group_id,))
    group = cur.fetchone()
    if not group:
        return "Group not found", 404

    cur.execute("SELECT user_id, username FROM users ORDER BY username")
    users = cur.fetchall()

    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        try:
            cur.execute("INSERT INTO memberships (user_id, group_id) VALUES (%s, %s)", (user_id, group_id))
            conn.commit()
        except psycopg2.Error:
            conn.rollback()
            flash("User already in group or DB error")
        cur.close(); conn.close()
        return redirect(url_for('groups.view_group', group_id=group_id))

    cur.close(); conn.close()
    return render_template_string("""
        <h2>Add Member to Group: {{ group_name }}</h2>
        <form method="POST">
            <label for="user_id">Select user:</label>
            <select name="user_id">
                {% for uid, uname in users %}
                    <option value="{{ uid }}">{{ uname }}</option>
                {% endfor %}
            </select><br><br>
            <button type="submit">Add Member</button>
        </form>
        <a href="{{ url_for('groups.view_group', group_id=group_id) }}">Back to group</a>
    """, users=users, group_name=group[0], group_id=group_id)


# ---------- EDIT GROUP ----------
@bp.route('/<int:group_id>/edit', methods=['GET', 'POST'])
def edit_group(group_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['group_name']
        new_desc = request.form['description']
        cur.execute(
            "UPDATE groups SET group_name = %s, description = %s WHERE group_id = %s",
            (new_name, new_desc, group_id)
        )
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('groups.list_groups'))

    # GET
    cur.execute("SELECT group_name, description FROM groups WHERE group_id = %s", (group_id,))
    group = cur.fetchone()
    cur.close(); conn.close()
    if not group:
        return "Group not found", 404

    return render_template_string("""
        <h2>Edit Group</h2>
        <form method="POST">
            Group name: <input name="group_name" value="{{ group[0] }}" required><br>
            Description: <input name="description" value="{{ group[1] }}"><br>
            <button type="submit">Save Changes</button>
        </form>
        <a href="{{ url_for('groups.list_groups') }}">Back to groups</a>
    """, group=group)


# ---------- DELETE GROUP ----------
@bp.route('/<int:group_id>/delete')
def delete_group(group_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM groups WHERE group_id = %s", (group_id,))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('groups.list_groups'))
