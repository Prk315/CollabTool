from flask import Blueprint, render_template_string, jsonify
from backend.db import SessionLocal
from backend.models import Availability, BusyTime, Participation, Project, WorkSession, Membership

bp = Blueprint("calendar", __name__, url_prefix="/calendar")

# ---------- HTML view ----------
@bp.route("/<int:user_id>")
def view_calendar(user_id):
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
      <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css" rel="stylesheet">
      <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js"></script>
      <style>
          body {font-family: Arial; padding: 20px;}
          #calendar {max-width: 900px; margin: 0 auto;}
      </style>
    </head>
    <body>
      <h2>User {{ user_id }} – Calendar</h2>
      <div id="calendar"></div>
      <a href="/users/">Back to users</a>

      <script>
        document.addEventListener('DOMContentLoaded', async () => {
          const res = await fetch('/calendar/api/{{ user_id }}');
          const raw  = await res.json();
          const events = raw.map(ev => ({
              title: `${ev.type}: ${ev.description || ''}`,
              start: ev.start,
              end:   ev.end,
              color: ev.type === 'Busy'        ? 'red'
                    : ev.type === 'Available'   ? 'green'
                    : ev.type === 'Session'     ? 'purple'
                    : 'blue'
          }));

          const cal = new FullCalendar.Calendar(
            document.getElementById('calendar'),
            {
              initialView: 'dayGridMonth',
              headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,listWeek'
              },
              events: events,
              selectable: true,
              select: function(info) {
                // on user drag‐select, open a prompt to add manual availability
                const start = info.startStr;
                const end   = info.endStr;
                const data  = { user_id: {{ user_id }}, start: start, end: end };
                fetch('/availability/api', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(data)
                }).then(() => location.reload());
              },
              eventClick: function(info) {
                // if user clicks an availability, delete it
                if (info.event.title.startsWith('Available')) {
                  const idParts = info.event.id.split('-'); // assume format "avail-<id>"
                  const availId = idParts[1];
                  fetch(`/availability/api/${availId}`, { method: 'DELETE' })
                    .then(() => location.reload());
                }
              },
              eventDidMount: function(info) {
                // tag each availability event with id "avail-<availability_id>"
                if (info.event.title.startsWith('Available')) {
                  info.el.id = `avail-${info.event.extendedProps.id}`;
                }
              }
            }
          );
          cal.render();
        });
      </script>
    </body>
    </html>
    """, user_id=user_id)

# ---------- JSON API ----------
@bp.route("/api/<int:user_id>")
def calendar_api(user_id):
    with SessionLocal() as db:
        avail_rows = (
            db.query(Availability.availability_id, Availability.start_time, Availability.end_time, Availability.source)
              .filter(Availability.user_id == user_id)
              .all()
        )
        busy_rows = (
            db.query(BusyTime.start_time, BusyTime.end_time, BusyTime.description)
              .filter(BusyTime.user_id == user_id)
              .all()
        )
        proj_rows = (
            db.query(Project.project_name, Project.deadline, Project.estimated_hours_needed)
              .join(Participation, Participation.project_id == Project.project_id)
              .filter(Participation.user_id == user_id)
              .all()
        )

        # Sessions: either directly participating or via group membership
        part_sessions = (
            db.query(
                WorkSession.session_id,
                WorkSession.start_time,
                WorkSession.end_time,
                Project.project_name
            )
            .join(Project, Project.project_id == WorkSession.project_id)
            .join(Participation, Participation.project_id == Project.project_id)
            .filter(Participation.user_id == user_id)
        )

        group_ids = [r[0] for r in
            db.query(Membership.group_id).filter(Membership.user_id == user_id).all()
        ]

        if group_ids:
            group_sessions = (
                db.query(
                    WorkSession.session_id,
                    WorkSession.start_time,
                    WorkSession.end_time,
                    Project.project_name
                )
                .join(Project, Project.project_id == WorkSession.project_id)
                .filter(Project.group_id.in_(group_ids))
            )
            session_rows = part_sessions.union(group_sessions).all()
        else:
            session_rows = part_sessions.all()

    avail = [
      {
        "type": "Available",
        "id": aid,
        "start": s.isoformat(),
        "end":   e.isoformat(),
        "description": src or ""
      }
      for aid, s, e, src in avail_rows
    ]
    busy = [
      {
        "type": "Busy",
        "start": s.isoformat(),
        "end":   e.isoformat(),
        "description": d or ""
      }
      for s, e, d in busy_rows
    ]
    proj = [
      {
        "type": "Project",
        "start": dl.isoformat(),
        "end":   dl.isoformat(),
        "description": f"{n} (est {h}h)"
      }
      for n, dl, h in proj_rows
    ]
    sess = [
      {
        "type": "Session",
        "id": sid,
        "start": s.isoformat(),
        "end":   e.isoformat(),
        "description": pname
      }
      for sid, s, e, pname in session_rows
    ]
    return jsonify(avail + busy + proj + sess)
