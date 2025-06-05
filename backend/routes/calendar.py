# backend/routes/calendar.py
from flask import Blueprint, render_template, jsonify, current_app
from backend.db import get_db_connection_with_retry

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


# ─────────────────────────────── HTML view ──────────────────────────────────
@bp.route("/<int:user_id>")
def view_calendar(user_id):
    return render_template("calendar.html", user_id=user_id)


# ─────────────────────────────── JSON feed ──────────────────────────────────
@bp.route("/api/<int:user_id>")
def calendar_api(user_id):
    try:
        conn = get_db_connection_with_retry()
        if not conn:
            return jsonify({"error": "Database connection unavailable"}), 503

        cur = conn.cursor()

        # ---------- availability (green) ----------
        cur.execute("""
            SELECT availability_id, start_time, end_time
            FROM availabilities WHERE user_id=%s
        """,(user_id,))
        avail=[{"type":"Available","id":aid,"start":str(s),"end":str(e),
                "description":""} for aid,s,e in cur.fetchall()]

        # ---------- busy (red) ----------
        cur.execute("""
            SELECT start_time,end_time,description
            FROM busy_times WHERE user_id=%s
        """,(user_id,))
        busy=[{"type":"Busy","start":str(s),"end":str(e),"description":d or ''}
            for s,e,d in cur.fetchall()]

        # ---------- projects (blue, deadline dots) ----------
        cur.execute("""
            SELECT p.project_name,p.deadline,p.estimated_hours_needed
            FROM participation pa
            JOIN projects p ON pa.project_id=p.project_id
            WHERE pa.user_id=%s
        """,(user_id,))
        projects=[{"type":"Project","start":str(d),"end":str(d),
                "description":f"{n} ({h}h)"} for n,d,h in cur.fetchall()]

        # ---------- work sessions (purple) ----------
        cur.execute("""
            SELECT ws.start_time,ws.end_time,p.project_name
            FROM work_sessions ws
            JOIN projects p ON ws.project_id=p.project_id
            WHERE p.project_id IN (
                SELECT project_id FROM participation WHERE user_id=%s
            )
        """,(user_id,))
        sessions=[{"type":"Session","start":str(s),"end":str(e),
                "description":n} for s,e,n in cur.fetchall()]
        
        cur.close(); conn.close()
        return jsonify(avail + busy + projects + sessions)
    except Exception as e:
        current_app.logger.error(f"Error in calendar_api: {e}")
        return jsonify({"error": "An error occurred processing the calendar data"}), 500
