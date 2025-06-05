from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from backend.db import Base

class User(Base):
    __tablename__ = "users"
    user_id    = Column(Integer, primary_key=True, index=True)
    username   = Column(Text, nullable=False)
    email      = Column(Text, unique=True, nullable=False)
    password   = Column(Text, nullable=False)

    memberships    = relationship("Membership",    back_populates="user", cascade="all, delete-orphan")
    participation  = relationship("Participation", back_populates="user", cascade="all, delete-orphan")
    busy_times     = relationship("BusyTime",       back_populates="user", cascade="all, delete-orphan")
    availabilities = relationship("Availability",   back_populates="user", cascade="all, delete-orphan")

class Group(Base):
    __tablename__ = "groups"
    group_id    = Column(Integer, primary_key=True, index=True)
    group_name  = Column(Text, nullable=False)
    description = Column(Text)

    memberships = relationship("Membership", back_populates="group", cascade="all, delete-orphan")
    projects    = relationship("Project",     back_populates="group", cascade="all, delete-orphan")

class Membership(Base):
    __tablename__ = "memberships"
    user_id  = Column(Integer, ForeignKey("users.user_id"),  primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), primary_key=True)

    user  = relationship("User",  back_populates="memberships")
    group = relationship("Group", back_populates="memberships")

class Project(Base):
    __tablename__ = "projects"
    project_id             = Column(Integer, primary_key=True, index=True)
    project_name           = Column(Text, nullable=False)
    group_id               = Column(Integer, ForeignKey("groups.group_id"))
    deadline               = Column(TIMESTAMP, nullable=False)
    estimated_hours_needed = Column(Integer)

    group         = relationship("Group",       back_populates="projects")
    participation = relationship("Participation", back_populates="project", cascade="all, delete-orphan")
    work_sessions = relationship("WorkSession",   back_populates="project", cascade="all, delete-orphan")

class Participation(Base):
    __tablename__ = "participation"
    user_id    = Column(Integer, ForeignKey("users.user_id"),    primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), primary_key=True)

    user    = relationship("User",    back_populates="participation")
    project = relationship("Project", back_populates="participation")

class Availability(Base):
    __tablename__ = "availabilities"
    availability_id = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.user_id"))
    start_time      = Column(TIMESTAMP, nullable=False)
    end_time        = Column(TIMESTAMP, nullable=False)
    source          = Column(Text, default="manual")

    user = relationship("User", back_populates="availabilities")

class BusyTime(Base):
    __tablename__ = "busy_times"
    busy_time_id = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.user_id"))
    start_time   = Column(TIMESTAMP, nullable=False)
    end_time     = Column(TIMESTAMP, nullable=False)
    description  = Column(Text)
    calendar_id  = Column(Text, default="default")

    user = relationship("User", back_populates="busy_times")

class WorkSession(Base):
    __tablename__ = "work_sessions"
    session_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    start_time = Column(TIMESTAMP, nullable=False)
    end_time   = Column(TIMESTAMP, nullable=False)

    project = relationship("Project", back_populates="work_sessions")
