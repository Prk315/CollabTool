from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.db import SessionLocal
from backend.models import Availability

bp = Blueprint("availability_api", __name__, url_prefix="/availability/api")

# ---------- CREATE AVAILABILITY ----------
@bp.route("", methods=["POST"])
def create_avail():
    data    = request.get_json(force=True)
    user_id = int(data["user_id"])
    start   = datetime.fromisoformat(data["start"])
    end     = datetime.fromisoformat(data["end"])
    with SessionLocal() as db:
        av = Availability(user_id=user_id, start_time=start, end_time=end, source="manual")
        db.add(av)
        db.commit()
        new_id = av.availability_id
    return jsonify({"id": new_id}), 201

# ---------- UPDATE AVAILABILITY ----------
@bp.route("/<int:availability_id>", methods=["PATCH"])
def update_avail(availability_id):
    data  = request.get_json(force=True)
    start = datetime.fromisoformat(data["start"])
    end   = datetime.fromisoformat(data["end"])
    with SessionLocal() as db:
        av = db.query(Availability).filter(Availability.availability_id == availability_id).first()
        if av:
            av.start_time = start
            av.end_time   = end
            db.commit()
    return "", 204

# ---------- DELETE AVAILABILITY ----------
@bp.route("/<int:availability_id>", methods=["DELETE"])
def delete_avail(availability_id):
    with SessionLocal() as db:
        av = db.query(Availability).filter(Availability.availability_id == availability_id).first()
        if av:
            db.delete(av)
            db.commit()
    return "", 204

# (Optional) if you want a GET endpoint for debugging:
@bp.route("/<int:user_id>", methods=["GET"])
def list_user_avails(user_id):
    with SessionLocal() as db:
        rows = (
            db.query(Availability.availability_id, Availability.start_time, Availability.end_time, Availability.source)
              .filter(Availability.user_id == user_id)
              .order_by(Availability.start_time)
              .all()
        )
    avails = [
        {"id": aid, "start": s.isoformat(), "end": e.isoformat(), "source": src}
        for aid, s, e, src in rows
    ]
    return jsonify(avails)
