-- db/migrations/001_initial_schema.sql

-- Users
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Groups
CREATE TABLE IF NOT EXISTS groups (
    group_id SERIAL PRIMARY KEY,
    group_name TEXT NOT NULL,
    description TEXT
);

-- Memberships (many-to-many between users and groups)
CREATE TABLE IF NOT EXISTS memberships (
    user_id INTEGER REFERENCES users(user_id),
    group_id INTEGER REFERENCES groups(group_id),
    PRIMARY KEY (user_id, group_id)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    project_name TEXT NOT NULL,
    group_id INTEGER REFERENCES groups(group_id),
    deadline TIMESTAMP NOT NULL,
    estimated_hours_needed INTEGER
);

-- Participation (many-to-many between users and projects)
CREATE TABLE IF NOT EXISTS participation (
    user_id INTEGER REFERENCES users(user_id),
    project_id INTEGER REFERENCES projects(project_id),
    PRIMARY KEY (user_id, project_id)
);

-- Availabilities
CREATE TABLE IF NOT EXISTS availabilities (
    availability_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    source TEXT
);

-- Busy Times (from .ics files)
CREATE TABLE IF NOT EXISTS busy_times (
    busy_time_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    description TEXT
);
