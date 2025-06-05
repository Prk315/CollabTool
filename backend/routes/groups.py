# backend/routes/groups.py
from flask import Blueprint, request, redirect, render_template, url_for, flash, jsonify, current_app
import psycopg2
from backend.db import get_db_connection, get_db_connection_with_retry

bp = Blueprint("groups", __name__, url_prefix="/groups")

# ---------- LIST GROUPS ------------------------------------------------------
@bp.route("/")
def list_groups():
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return render_template("groups/list.html", groups=[])
            
        cur = conn.cursor()
        cur.execute("SELECT group_id, group_name, description FROM groups ORDER BY group_id;")
        groups = cur.fetchall(); cur.close(); conn.close()
        return render_template("groups/list.html", groups=groups)
    except Exception as e:
        current_app.logger.error(f"Error listing groups: {e}")
        flash("An error occurred while retrieving groups.", "error")
        return render_template("groups/list.html", groups=[])

# ---------- CREATE GROUP -----------------------------------------------------
@bp.route("/new", methods=["GET", "POST"])
def create_group():
    if request.method == "POST":
        try:
            name = request.form["group_name"]; desc = request.form["description"]
            conn = get_db_connection_with_retry()
            if not conn:
                flash("Database connection unavailable. Unable to create group.", "error")
                return render_template("groups/new.html")
                
            cur = conn.cursor()
            cur.execute("INSERT INTO groups (group_name, description) VALUES (%s,%s)", (name, desc))
            conn.commit(); cur.close(); conn.close()
            flash("Group created successfully.", "success")
            return redirect(url_for("groups.list_groups"))
        except Exception as e:
            current_app.logger.error(f"Error creating group: {e}")
            flash("An error occurred while creating the group.", "error")
            return render_template("groups/new.html")
    return render_template("groups/new.html")

# ---------- VIEW GROUP & MEMBERS --------------------------------------------
@bp.route("/<int:group_id>")
def view_group(group_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("groups.list_groups"))
            
        cur = conn.cursor()
        cur.execute("SELECT group_name, description FROM groups WHERE group_id=%s", (group_id,))
        group = cur.fetchone()
        
        if not group:
            cur.close(); conn.close()
            flash("Group not found.", "error")
            return redirect(url_for("groups.list_groups"))
            
        cur.execute("""
            SELECT u.user_id, u.username
            FROM memberships m JOIN users u ON m.user_id=u.user_id
            WHERE m.group_id=%s ORDER BY u.username;
        """, (group_id,))
        members = cur.fetchall(); cur.close(); conn.close()
        return render_template("groups/view.html", group=group, members=members, group_id=group_id)
    except Exception as e:
        current_app.logger.error(f"Error viewing group: {e}")
        flash("An error occurred while retrieving group information.", "error")
        return redirect(url_for("groups.list_groups"))

# ---------- ADD MEMBER -------------------------------------------------------
@bp.route("/<int:group_id>/add_member", methods=["GET", "POST"])
def add_member(group_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))
            
        cur = conn.cursor()
        cur.execute("SELECT group_name FROM groups WHERE group_id=%s", (group_id,))
        group = cur.fetchone()
        if not group: 
            cur.close(); conn.close()
            flash("Group not found.", "error")
            return redirect(url_for("groups.list_groups"))
            
        cur.execute("SELECT user_id, username FROM users ORDER BY username")
        users = cur.fetchall()

        if request.method == "POST":
            user_id = int(request.form["user_id"])
            try:
                cur.execute("INSERT INTO memberships(user_id,group_id) VALUES(%s,%s)", (user_id, group_id))
                conn.commit()
                flash("Member added successfully.", "success")
            except psycopg2.Error as e:
                conn.rollback()
                current_app.logger.error(f"Error adding member: {e}")
                flash("User already in group or database error.", "error")
            cur.close(); conn.close()
            return redirect(url_for("groups.view_group", group_id=group_id))

        cur.close(); conn.close()
        return render_template("groups/add_member.html", users=users, group=group, group_id=group_id)
    except Exception as e:
        current_app.logger.error(f"Error in add_member: {e}")
        flash("An error occurred while processing your request.", "error")
        return redirect(url_for("groups.view_group", group_id=group_id))

# ---------- EDIT GROUP -------------------------------------------------------
@bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
def edit_group(group_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("groups.list_groups"))
            
        cur = conn.cursor()
        
        if request.method == "POST":
            new_n = request.form["group_name"]; new_d = request.form["description"]
            cur.execute("UPDATE groups SET group_name=%s, description=%s WHERE group_id=%s",
                        (new_n, new_d, group_id))
            conn.commit(); cur.close(); conn.close()
            flash("Group updated successfully.", "success")
            return redirect(url_for("groups.list_groups"))
            
        cur.execute("SELECT group_name,description FROM groups WHERE group_id=%s", (group_id,))
        grp = cur.fetchone()
        cur.close(); conn.close()
        
        if not grp:
            flash("Group not found.", "error")
            return redirect(url_for("groups.list_groups"))
            
        return render_template("groups/edit.html", grp=grp)
    except Exception as e:
        current_app.logger.error(f"Error editing group: {e}")
        flash("An error occurred while processing your request.", "error")
        return redirect(url_for("groups.list_groups"))

# ---------- DELETE GROUP -----------------------------------------------------
@bp.route("/<int:group_id>/delete")
def delete_group(group_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("groups.list_groups"))
            
        cur = conn.cursor()
        cur.execute("DELETE FROM groups WHERE group_id=%s", (group_id,))
        conn.commit(); cur.close(); conn.close()
        flash("Group deleted successfully.", "success")
        return redirect(url_for("groups.list_groups"))
    except Exception as e:
        current_app.logger.error(f"Error deleting group: {e}")
        flash("An error occurred while deleting the group.", "error")
        return redirect(url_for("groups.list_groups"))

# ---------- GROUP CALENDAR (HTML) -------------------------------------------
@bp.route("/<int:group_id>/calendar")
def group_calendar_view(group_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            flash("Database connection unavailable. Please try again later.", "error")
            return redirect(url_for("groups.list_groups"))
            
        cur = conn.cursor()
        cur.execute("SELECT group_name FROM groups WHERE group_id=%s", (group_id,))
        g = cur.fetchone(); cur.close(); conn.close()
        
        if not g:
            flash("Group not found.", "error")
            return redirect(url_for("groups.list_groups"))
            
        return render_template("groups/calendar.html", group_id=group_id, g=g)
    except Exception as e:
        current_app.logger.error(f"Error viewing group calendar: {e}")
        flash("An error occurred while retrieving calendar information.", "error")
        return redirect(url_for("groups.list_groups"))


# ───────────────────────────────── JSON API ────────────────────────────────
@bp.route("/api/<int:group_id>")
def group_calendar_api(group_id):
    """
    • Blue  = time blocks when *all* group members are free
    • Purple = booked work-sessions for any project owned by this group
    """
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            return jsonify({"error": "Database connection unavailable"}), 503
            
        cur = conn.cursor()

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

        seed = next((slots for slots in per.values() if slots), [])
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
    except Exception as e:
        current_app.logger.error(f"Error in group_calendar_api: {e}")
        return jsonify({"error": "An error occurred processing the calendar data"}), 500
