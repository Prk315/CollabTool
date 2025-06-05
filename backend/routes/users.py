from flask import Blueprint, request, render_template, redirect, url_for, current_app
from backend.db import SessionLocal
from backend.models import User
import logging
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint("users", __name__, url_prefix="/users")

# ---------- LIST USERS ----------
@bp.route("/")
def list_users():
    users = []
    try:
        with SessionLocal() as db:
            users = db.query(User.user_id, User.username, User.email).order_by(User.user_id).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error in list_users: {str(e)}")
        return f"Database connection error. Please check your configuration.", 500
        
    return render_template("users/list.html", users=users)

# ---------- REGISTER USER ----------
@bp.route("/new", methods=["GET", "POST"], endpoint="register")
def register():
    if request.method == "POST":
        try:
            username = request.form["username"]
            email    = request.form["email"]
            pwd      = request.form["password"]
            with SessionLocal() as db:
                new = User(username=username, email=email, password=pwd)
                db.add(new)
                db.commit()
            return redirect(url_for("users.list_users"))
        except SQLAlchemyError as e:
            logging.error(f"Database error in register: {str(e)}")
            return f"Error registering user. Please try again later.", 500

    return render_template("users/register.html")

# ---------- EDIT USER ----------
@bp.route("/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = None
    try:
        with SessionLocal() as db:
            if request.method == "POST":
                uname = request.form["username"]
                mail  = request.form["email"]
                user  = db.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.username = uname
                    user.email    = mail
                    db.commit()
                return redirect(url_for("users.list_users"))

            user = db.query(User.username, User.email).filter(User.user_id == user_id).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in edit_user: {str(e)}")
        return f"Database error while editing user. Please try again later.", 500
        
    if not user:
        return "User not found", 404

    return render_template("users/edit.html", user=user)

# ---------- DELETE USER ----------
@bp.route("/delete/<int:user_id>")
def delete_user(user_id):
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                db.delete(user)
                db.commit()
    except SQLAlchemyError as e:
        logging.error(f"Database error in delete_user: {str(e)}")
        return f"Database error while deleting user. Please try again later.", 500
        
    return redirect(url_for("users.list_users"))
