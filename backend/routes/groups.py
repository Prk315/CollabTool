from flask import Blueprint, request, redirect, render_template, url_for, flash, jsonify
from backend.db import SessionLocal
from backend.models import Group, User, Membership, Availability

bp = Blueprint("groups", __name__, url_prefix="/groups")

# ---------- LIST GROUPS ----------
@bp.route("/")
def list_groups():
    with SessionLocal() as db:
        groups = db.query(Group.group_id, Group.group_name, Group.description).order_by(Group.group_id).all()
    return render_template("groups/list.html", groups=groups)

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

    return render_template("groups/new.html")

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

    return render_template("groups/view.html", group=group, members=members, group_id=group_id)

# ---------- ADD MEMBER ----------
@bp.route("/<int:group_id>/add_member", methods=["GET", "POST"])
def add_member(group_id):
    with SessionLocal() as db:
        if request.method == "POST":
            uid = int(request.form["user_id"])
            mem = Membership(group_id=group_id, user_id=uid)
            db.add(mem)
            db.commit()
            return redirect(url_for("groups.view_group", group_id=group_id))

        # Get group name for displaying
        group = db.query(Group.group_name).filter(Group.group_id == group_id).first()
        if not group:
            return "Group not found", 404

        # Get users who are not yet members
        subq = db.query(Membership.user_id).filter(Membership.group_id == group_id).subquery()
        users = db.query(User.user_id, User.username).filter(
            ~User.user_id.in_(subq)
        ).order_by(User.username).all()

    return render_template("groups/add_member.html", group=group, users=users, group_id=group_id)

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

    return render_template("groups/edit.html", grp=grp)

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

    return render_template("groups/calendar.html", group_id=group_id, g=g)

# ---------- GROUP CALENDAR (JSON API) ----------
@bp.route("/api/<int:group_id>")
def group_calendar_json(group_id):
    with SessionLocal() as db:
        # Get members
        members = db.query(User.user_id)\
                    .join(Membership, Membership.user_id == User.user_id)\
                    .filter(Membership.group_id == group_id)\
                    .all()
        member_ids = [m[0] for m in members]
        
        if not member_ids:
            return jsonify([])

        # Get all availabilities for all members
        avail = (
            db.query(Availability.start_time, Availability.end_time)
              .filter(Availability.user_id.in_(member_ids))
              .order_by(Availability.start_time)
              .all()
        )

    # Get overlapping time windows where everyone is available
    common_slots = []
    # (this implementation is simplified and could be improved
    #  to better handle overlapping availability from the same user)
    
    # Format for FullCalendar
    events = []
    for start, end in avail:
        events.append({
            "title": "Available",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "color": "green"
        })

    return jsonify(events)
