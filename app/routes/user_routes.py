from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from flask_login import login_user, logout_user, login_required
from app.models.models import Users,models,get_session
from app.services.DatabaseConnection import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

user_bp = Blueprint("user", __name__)


@user_bp.route('/register', methods=["GET", "POST"])
def register():
    """
    Handles user registration.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")

        # Hash the password
        #hashed_password = generate_password_hash(password)

        # Create new user
        #user = Users(username=username, password=password, firstname=firstname, lastname=lastname)
        user = Users(username=username, firstname=firstname, lastname=lastname)
        user.password = password  # This will hash the password using bcrypt

        try:
            db.session.add(user)
            db.session.commit()
            insert_user_table(user)
            return redirect(url_for("user.login"))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

        #return redirect(url_for("user.login"))
    return render_template("signup.html")


@user_bp.route("/", methods=["GET", "POST"])
def login():
    """
    Handles user login.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Users.query.filter_by(username=username).first()
        if not user:
            return "Invalid username or password.",500
        #if user and user.password == request.form.get("password"):
        #if check_password_hash(user.password, password):
        if user and user.check_password(password):
            login_user(user)
            fetch_userdata(user)
            session['username'] = username
            session["logged_in_user"] = {
                "id": user.userid,
                "email": user.username,  # Assuming User model has an email field
                "name": user.firstname  # Assuming User model has a name field
            }
            current_app.logger.info(f"User {username} logged in and stored in session.")
            return redirect(url_for("main.index"))
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")


@user_bp.route("/logout")
@login_required
def logout():
    """
    Handles user logout.
    """
    logout_user()
    return redirect(url_for("user.login"))

def fetch_userdata(user):
    """
    Fetches user data from the USERDATA table using Flask-SQLAlchemy.
    """
    try:
        username, firstname, lastname = user.get_userdetails()

        # Query the Users table using Flask-SQLAlchemy
        result = Users.query.filter_by(username=username).all()
        if result:
            current_app.current_app.logger.info(f"Fetched {len(result)} rows.")
        else:
            current_app.logger.info("No rows fetched.")

        # Convert results to a dictionary
        result_list = [u.get_userdetails() for u in result]
        print(result_list)
        return result_list
    except Exception as e:
        current_app.logger.error(f"Error during fetch: {str(e)}")
        return []

def insert_user_table(user):
    """
    Inserts a user into the USERDATA table using Flask-SQLAlchemy.
    """
    try:
        userid, username, firstname, lastname = user.get_userdetails()

        # Check if the username already exists
        existing_user = user.query.filter_by(username=username).first()
        if existing_user:
            current_app.current_app.logger.warning("Username already exists. Skipping insert.")
            return

        # Insert the user
        new_user = Users(username=username, firstname=firstname, lastname=lastname)
        db.session.add(new_user)
        db.session.commit()
        current_app.logger.info(f"User {username} inserted successfully.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during insert: {str(e)}")
