from flask import Blueprint, render_template_string, request, redirect, url_for
from backend.db import get_db_connection

bp = Blueprint('users', __name__, url_prefix='/users')


@bp.route('/')
def list_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, email FROM users ORDER BY user_id;")
    users = cur.fetchall()
    cur.close(); conn.close()

    return render_template_string("""
        <h2>Registered Users</h2>
        <ul>
        {% for uid, uname, mail in users %}
          <li>
            <strong>{{ uid }}</strong> – {{ uname }} ({{ mail }})
            [<a href="{{ url_for('users.edit_user', user_id=uid) }}">Edit</a>]
            [<a href="{{ url_for('users.delete_user', user_id=uid) }}">Delete</a>]
          </li>
        {% endfor %}
        </ul>
        <a href="/">Home</a>
    """, users=users)


@bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        cur.execute(
            "UPDATE users SET username = %s, email = %s WHERE user_id = %s",
            (username, email, user_id)
        )
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('users.list_users'))

    cur.execute("SELECT username, email FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close(); conn.close()

    if not user:
        return "User not found", 404

    return render_template_string("""
        <h2>Edit User</h2>
        <form method="POST">
            Username: <input name="username" value="{{ user[0] }}"><br>
            Email: <input name="email" type="email" value="{{ user[1] }}"><br>
            <button type="submit">Update</button>
        </form>
        <a href="{{ url_for('users.list_users') }}">Cancel</a>
    """, user=user)


@bp.route('/delete/<int:user_id>')
def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('users.list_users'))
