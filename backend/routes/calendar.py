# backend/routes/calendar.py
from flask import Blueprint, render_template_string, jsonify
from backend.db import get_db_connection

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


# ─────────────────────────────── HTML view ──────────────────────────────────
@bp.route("/<int:user_id>")
def view_calendar(user_id):
    return render_template_string(
        """
<!doctype html>
<html>
<head>
  <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js"></script>
  <style>body{font-family:Arial;padding:20px;}#calendar{max-width:900px;margin:0 auto;}</style>
</head>
<body>
  <h2>User {{ user_id }} – Calendar</h2>
  <div id="calendar"></div>
  <a href="/users/">Back to users</a>

  <script>
    document.addEventListener('DOMContentLoaded', async () => {
      const uid  = {{ user_id }};
      const feed = await fetch(`/calendar/api/${uid}`).then(r=>r.json());

      const cal  = new FullCalendar.Calendar(
        document.getElementById('calendar'),
        {
          initialView:'dayGridMonth',
          selectable :true,
          editable   :true,
          headerToolbar:{
            left:'prev,next today',
            center:'title',
            right:'dayGridMonth,timeGridWeek,listWeek'
          },
          events: feed.map(ev => ({
            id   : ev.id || null,
            title: ev.type === 'Available' ? 'Available'
                 : ev.type === 'Busy'      ? `Busy: ${ev.description||''}`
                 : ev.type === 'Session'   ? `Session: ${ev.description||''}`
                 : `Project: ${ev.description||''}`,
            start: ev.start,
            end  : ev.end,
            color: ev.type === 'Busy'      ? 'red'
                 : ev.type === 'Available' ? 'green'
                 : ev.type === 'Session'   ? 'purple'
                 : 'blue'
          })),

          /* ---------- create availability ------------------------- */
          select: async info=>{
            if(!confirm(`Add availability:\\n${info.startStr} → ${info.endStr}?`)){
              cal.unselect(); return;
            }
            const res = await fetch('/availability/api',{
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body:JSON.stringify({user_id:uid,start:info.startStr,end:info.endStr})
            }).then(r=>r.json());

            cal.addEvent({id:res.id,title:'Available',
                          start:info.start,end:info.end,color:'green'});
          },

          /* ---------- update availability (drag/resize) ----------- */
          eventDrop  : handleUpdate,
          eventResize: handleUpdate,

          /* ---------- delete availability ------------------------- */
          eventClick: async info=>{
            if(info.event.title!=='Available') return;
            if(!confirm('Delete this availability?')) return;
            await fetch(`/availability/api/${info.event.id}`,{method:'DELETE'});
            info.event.remove();
          }
        });

      async function handleUpdate(info){
        if(info.event.title!=='Available'){ info.revert(); return; }
        await fetch(`/availability/api/${info.event.id}`,{
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            start:info.event.start.toISOString(),
            end  :info.event.end.toISOString()
          })
        });
      }

      cal.render();
    });
  </script>
</body>
</html>
""",
        user_id=user_id,
    )


# ─────────────────────────────── JSON feed ──────────────────────────────────
@bp.route("/api/<int:user_id>")
def calendar_api(user_id):
    conn = get_db_connection(); cur = conn.cursor()

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
    proj=[{"type":"Project","start":str(dl),"end":str(dl),
           "description":f"{n} (est {h}h)"} for n,dl,h in cur.fetchall()]

    # ---------- sessions (purple) ----------
    cur.execute("""
        WITH my_groups AS (
            SELECT group_id FROM memberships WHERE user_id = %s
        )
        SELECT DISTINCT ws.session_id,
                        ws.start_time,
                        ws.end_time,
                        p.project_name
        FROM work_sessions ws
        JOIN projects p       ON ws.project_id = p.project_id
        LEFT JOIN participation pa ON pa.project_id = p.project_id
                                   AND pa.user_id   = %s
        LEFT JOIN my_groups mg     ON mg.group_id    = p.group_id
        WHERE pa.user_id IS NOT NULL       -- explicit participant
           OR mg.group_id IS NOT NULL      -- OR group member
    """,(user_id,user_id))
    sess=[{"type":"Session","id":sid,"start":str(s),"end":str(e),
           "description":pn} for sid,s,e,pn in cur.fetchall()]

    cur.close(); conn.close()
    return jsonify(avail+busy+proj+sess)
