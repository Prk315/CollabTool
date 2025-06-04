# backend/routes/calendar.py
from flask import Blueprint, render_template_string, jsonify
from backend.db import get_db_connection

bp = Blueprint("calendar", __name__, url_prefix="/calendar")

# ---------- HTML view --------------------------------------------------------
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
              color: ev.type === 'Busy' ? 'red'
                    : ev.type === 'Available' ? 'green'
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
              events: events
            }
          );
          cal.render();
        });
      </script>
    </body>
    </html>
    """, user_id=user_id)

# ---------- JSON API ---------------------------------------------------------
@bp.route("/api/<int:user_id>")
def calendar_api(user_id):
    conn = get_db_connection(); cur = conn.cursor()

    cur.execute(
        "SELECT start_time, end_time, COALESCE(source,'manual') "
        "FROM availabilities WHERE user_id=%s",
        (user_id,)
    )
    avail = [
        {"type":"Available","start":str(s),"end":str(e),"description":src}
        for s,e,src in cur.fetchall()
    ]

    cur.execute(
        "SELECT start_time,end_time,description FROM busy_times WHERE user_id=%s",
        (user_id,)
    )
    busy = [
        {"type":"Busy","start":str(s),"end":str(e),"description":d or ''}
        for s,e,d in cur.fetchall()
    ]

    cur.execute(
        "SELECT p.project_name,p.deadline,p.estimated_hours_needed "
        "FROM participation pa JOIN projects p ON pa.project_id=p.project_id "
        "WHERE pa.user_id=%s",
        (user_id,)
    )
    proj = [
        {
          "type":"Project",
          "start":str(dl),
          "end":str(dl),
          "description":f"{n} (est. {h} h)"
        } for n,dl,h in cur.fetchall()
    ]

    cur.close(); conn.close()
    return jsonify(avail + busy + proj)
