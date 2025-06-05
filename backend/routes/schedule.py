from flask import Blueprint, render_template_string
from backend.db import SessionLocal
from backend.models import Project, Participation, Availability

bp = Blueprint("schedule", __name__, url_prefix="/schedule")

# ---------- PROJECT SCHEDULE ----------
@bp.route("/project/<int:project_id>")
def project_schedule(project_id):
    with SessionLocal() as db:
        proj = db.query(Project).filter(Project.project_id == project_id).first()
        if not proj:
            return "Project not found", 404

        members = [r[0] for r in
            db.query(Participation.user_id).filter(Participation.project_id == project_id).all()
        ]

        avail_rows = (
            db.query(Availability.user_id, Availability.start_time, Availability.end_time)
              .filter(Availability.user_id.in_(members))
              .order_by(Availability.start_time)
              .all()
        )

    per = {}
    for uid, s, e in avail_rows:
        per.setdefault(uid, []).append((s, e))

    def overlap(a, b):
        s = max(a[0], b[0])
        e = min(a[1], b[1])
        return (s, e) if s < e else None

    common = per.get(members[0], [])[:]
    for uid in members[1:]:
        slots = per.get(uid, [])
        new = [
            ov for a in common for b in slots
            if (ov := overlap(a, b))
        ]
        common = new
        if not common:
            break

    return render_template_string("""
        <h2>Project Schedule: {{ proj.project_name }}</h2>
        <p>Deadline: {{ proj.deadline }}</p>
        <h3>Common Availability Blocks</h3>
        <ul>
        {% for s, e in common %}
          <li>{{ s.strftime('%Y-%m-%d %H:%M') }} → {{ e.strftime('%Y-%m-%d %H:%M') }}</li>
        {% else %}
          <li><em>No common availability.</em></li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('projects.list_projects') }}">Back to projects</a>
    """, proj=proj, common=common)
