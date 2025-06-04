from flask import Blueprint, render_template_string, request, redirect, url_for
from backend.db import get_db_connection

bp = Blueprint('availability', __name__, url_prefix='/availability')

@bp.route('/')
def list_availability():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.availability_id, u.username, a.start_time, a.end_time
        FROM availabilities a
        JOIN users u ON a.user_id = u.user_id
        ORDER BY a.start_time;
    """)
    slots = cur.fetchall()
    cur.close(); conn.close()
    return render_template_string("""
        <h2>User Availabilities</h2>
        <ul>
        {% for aid, uname, start, end in slots %}
          <li>
            {{ uname }}: {{ start }} → {{ end }}
            [<a href="{{ url_for('availability.delete_availability', availability_id=aid) }}">Delete</a>]
          </li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('availability.new_availability') }}">Add availability</a> |
        <a href="/">Home</a>
    """, slots=slots)


@bp.route('/new', methods=['GET', 'POST'])
def new_availability():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        start   = request.form['start_time']
        end     = request.form['end_time']
        cur.execute(
            "INSERT INTO availabilities (user_id, start_time, end_time, source) VALUES (%s, %s, %s, %s)",
            (user_id, start, end, "manual")
        )
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('availability.list_availability'))

    cur.execute("SELECT user_id, username FROM users ORDER BY username;")
    users = cur.fetchall()
    cur.close(); conn.close()
    return render_template_string("""
        <h2>Add Availability</h2>
        <form method="POST">
            User:
            <select name="user_id" required>
                {% for uid, uname in users %}
                  <option value="{{ uid }}">{{ uname }}</option>
                {% endfor %}
            </select><br>
            Start: <input type="datetime-local" name="start_time" required><br>
            End: <input type="datetime-local" name="end_time" required><br>
            <button type="submit">Add</button>
        </form>
        <a href="{{ url_for('availability.list_availability') }}">Cancel</a>
    """, users=users)


@bp.route('/delete/<int:availability_id>')
def delete_availability(availability_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM availabilities WHERE availability_id = %s", (availability_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('availability.list_availability'))
