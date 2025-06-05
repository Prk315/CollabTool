# backend/routes/availability_api.py
from flask import Blueprint, request, jsonify
from backend.db import get_db_connection
from datetime import datetime

bp = Blueprint("availability_api", __name__, url_prefix="/availability/api")

# ---------------- list -------------------------------------------------------
@bp.route("/<int:user_id>")
def list_avail(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT availability_id, start_time, end_time
        FROM availabilities
        WHERE user_id=%s
        ORDER BY start_time
    """, (user_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"id":aid,"start":s.isoformat(),"end":e.isoformat()}
                    for aid,s,e in rows])

# ---------------- create -----------------------------------------------------
@bp.route("", methods=["POST"])
def create_avail():
    data = request.get_json(force=True)
    user_id = int(data["user_id"])
    start   = datetime.fromisoformat(data["start"])
    end     = datetime.fromisoformat(data["end"])
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO availabilities(user_id,start_time,end_time,source)
        VALUES (%s,%s,%s,'manual')
        RETURNING availability_id
    """, (user_id,start,end))
    aid = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    return jsonify({"id":aid}), 201

# ---------------- update (resize / drag) ------------------------------------
@bp.route("/<int:availability_id>", methods=["PATCH"])
def update_avail(availability_id):
    data = request.get_json(force=True)
    start = datetime.fromisoformat(data["start"])
    end   = datetime.fromisoformat(data["end"])
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        UPDATE availabilities
        SET start_time=%s, end_time=%s
        WHERE availability_id=%s
    """, (start,end,availability_id))
    conn.commit(); cur.close(); conn.close()
    return "", 204

# ---------------- delete -----------------------------------------------------
@bp.route("/<int:availability_id>", methods=["DELETE"])
def delete_avail(availability_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM availabilities WHERE availability_id=%s",
                (availability_id,))
    conn.commit(); cur.close(); conn.close()
    return "", 204
