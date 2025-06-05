CREATE TABLE IF NOT EXISTS work_sessions (
    session_id   SERIAL PRIMARY KEY,
    project_id   INTEGER REFERENCES projects(project_id),
    start_time   TIMESTAMP NOT NULL,
    end_time     TIMESTAMP NOT NULL
);
