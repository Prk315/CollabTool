# backend/routes/users.py
from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app
from backend.db import get_db_connection_with_retry

bp = Blueprint("users", __name__, url_prefix="/users")

# list users ------------------------------------------------------------------
@bp.route("/")
def list_users():
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return render_template("users/list.html", users=[])
            
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, email FROM users ORDER BY user_id;")
        users = cur.fetchall(); cur.close(); conn.close()
        return render_template("users/list.html", users=users)
    except Exception as e:
        current_app.logger.error(f"Error listing users: {e}")
        flash("An error occurred while retrieving users.", "error")
        return render_template("users/list.html", users=[])

# create user -----------------------------------------------------------------
@bp.route("/new", methods=["GET", "POST"], endpoint="register")
def register():
    if request.method == "POST":
        try:
            username = request.form["username"]; email = request.form["email"]; pwd = request.form["password"]
            conn = get_db_connection_with_retry()
            if not conn:
                flash("Database connection unavailable. Unable to register user.", "error")
                return render_template("users/register.html")
                
            cur = conn.cursor()
            cur.execute("INSERT INTO users(username,email,password) VALUES (%s,%s,%s)",(username,email,pwd))
            conn.commit(); cur.close(); conn.close()
            flash("User registered successfully.", "success")
            return redirect(url_for("users.list_users"))
        except Exception as e:
            current_app.logger.error(f"Error registering user: {e}")
            flash("An error occurred while registering the user.", "error")
            return render_template("users/register.html")
    return render_template("users/register.html")

# edit user -------------------------------------------------------------------
@bp.route("/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("users.list_users"))
            
        cur = conn.cursor()
        
        if request.method == "POST":
            uname = request.form["username"]; mail = request.form["email"]
            cur.execute("UPDATE users SET username=%s,email=%s WHERE user_id=%s",(uname,mail,user_id))
            conn.commit(); cur.close(); conn.close()
            flash("User updated successfully.", "success")
            return redirect(url_for("users.list_users"))
            
        cur.execute("SELECT username,email FROM users WHERE user_id=%s",(user_id,))
        user = cur.fetchone()
        cur.close(); conn.close()
        
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("users.list_users"))
            
        return render_template("users/edit.html", user=user)
    except Exception as e:
        current_app.logger.error(f"Error editing user: {e}")
        flash("An error occurred while processing your request.", "error")
        return redirect(url_for("users.list_users"))

# delete user -----------------------------------------------------------------
@bp.route("/delete/<int:user_id>")
def delete_user(user_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("users.list_users"))
            
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        conn.commit(); cur.close(); conn.close()
        flash("User deleted successfully.", "success")
        return redirect(url_for("users.list_users"))
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {e}")
        flash("An error occurred while deleting the user.", "error")
        return redirect(url_for("users.list_users"))
