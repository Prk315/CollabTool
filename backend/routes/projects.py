from flask import Blueprint, render_template, request, redirect, url_for
from backend.db import SessionLocal
from backend.models import Project, Group, Participation, WorkSession
from datetime import datetime
import re

bp = Blueprint("projects", __name__, url_prefix="/projects")

@bp.route("/")
def list_projects():
    with SessionLocal() as db:
        projects = (
            db.query(
                Project.project_id,
                Project.project_name,
                Group.group_name,
                Project.deadline,
                Project.estimated_hours_needed
            )
            .join(Group, Group.group_id == Project.group_id)
            .order_by(Project.project_id)
            .all()
        )
    return render_template("projects/list.html", projects=projects)

# ---------- NEW PROJECT ----------
@bp.route("/new", methods=["GET", "POST"], endpoint="new_project")
def new_project():
    with SessionLocal() as db:
        if request.method == "POST":
            name     = request.form["name"]
            pattern = re.compile("ab*")
            if re.match(pattern,name):
                print("Found a pattern match")
            else:
                print("Pattern was incorrect")
            group_id = int(request.form["group_id"])
            deadline = datetime.fromisoformat(request.form["deadline"])
            hours    = int(request.form["hours"])
            proj = Project(
                project_name=name,
                group_id=group_id,
                deadline=deadline,
                estimated_hours_needed=hours
            )
            db.add(proj)
            db.commit()
            return redirect(url_for("projects.list_projects"))

        groups = db.query(Group.group_id, Group.group_name).order_by(Group.group_name).all()
    return render_template("projects/new.html", groups=groups)

# ---------- EDIT PROJECT ----------
@bp.route("/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    with SessionLocal() as db:
        if request.method == "POST":
            name   = request.form["name"]
            gid    = int(request.form["group_id"])
            ddl    = datetime.fromisoformat(request.form["deadline"])
            hrs    = int(request.form["hours"])
            proj   = db.query(Project).filter(Project.project_id == project_id).first()
            if proj:
                proj.project_name = name
                proj.group_id     = gid
                proj.deadline     = ddl
                proj.estimated_hours_needed = hrs
                db.commit()
            return redirect(url_for("projects.list_projects"))

        proj   = db.query(Project.project_name, Project.group_id, Project.deadline, Project.estimated_hours_needed)\
                   .filter(Project.project_id == project_id).first()
        groups = db.query(Group.group_id, Group.group_name).order_by(Group.group_name).all()

    if not proj:
        return "Not found", 404

    return render_template("projects/edit.html", proj=proj, groups=groups)

# ---------- DELETE PROJECT ----------
@bp.route("/delete/<int:project_id>")
def delete_project(project_id):
    with SessionLocal() as db:
        proj = db.query(Project).filter(Project.project_id == project_id).first()
        if proj:
            db.delete(proj)
            db.commit()
    return redirect(url_for("projects.list_projects"))

# ---------- SUGGEST COMMON MEETING SLOTS ----------
@bp.route("/suggest/<int:project_id>")
def suggest_slots(project_id):
    with SessionLocal() as db:
        # Get project details
        proj = db.query(Project.project_name, Project.group_id, Project.deadline, Project.estimated_hours_needed)\
                 .filter(Project.project_id == project_id).first()
        if not proj:
            return "Project not found", 404

        pname, group_id, ddl, hrs_needed = proj

        # Get time slots where members are available
        # This would be more complex in a real implementation - this is simplified
        # For a real solution, get all available time slots of all group members,
        # then find overlapping time slots

        # Let's just mock up a few slots for now
        from datetime import timedelta
        suggestions = [
            (datetime.now() + timedelta(days=1, hours=2), 
             datetime.now() + timedelta(days=1, hours=4)),
            (datetime.now() + timedelta(days=2, hours=10), 
             datetime.now() + timedelta(days=2, hours=12)),
            (datetime.now() + timedelta(days=3), 
             datetime.now() + timedelta(days=3, hours=3))
        ]

    return render_template("projects/suggest_slots.html", 
                          pname=pname, 
                          ddl=ddl, 
                          hrs_needed=hrs_needed, 
                          suggestions=suggestions,
                          project_id=project_id)

# ---------- BOOK SESSION ----------
@bp.route("/book/<int:project_id>", methods=["POST"], endpoint="book_session")
def book_session(project_id):
    start = datetime.fromisoformat(request.form["start"])
    end   = datetime.fromisoformat(request.form["end"])
    with SessionLocal() as db:
        ws = WorkSession(project_id=project_id, start_time=start, end_time=end)
        db.add(ws)
        db.commit()
    return redirect(url_for("projects.list_projects"))
