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

        # Check if username already exists
        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            return render_template("signup.html", error="Username already exists. Please choose a different one.")

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
def login_bk():
    """
    Handles user login.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Users.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return jsonify({"warning": "Invalid username or password"}), 401
            #return "Invalid username or password.",500

        if user and user.check_password(password):
            login_user(user)
            fetch_userdata(user)
            session['username'] = username
            session["logged_in_user"] = {
                "id": user.userid,
                "email": user.username,  #email
                "name": user.firstname
            }
            current_app.logger.info(f"User {username} logged in and stored in session.")
            return redirect(url_for("main.index"))
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")



@user_bp.route("/", methods=["GET", "POST"])
def login():
    """
       Handles user login.
    """
    if request.method == "POST":
        try:
            username = request.form.get("username")
            password = request.form.get("password")

            current_app.logger.debug(f"Attempt login with: {username}")

            user = Users.query.filter_by(username=username).first()
            if not user:
                current_app.logger.warning("User not found")
                return jsonify({"warning": "User not found"}), 401

            if not user.check_password(password):
                current_app.logger.warning("Invalid password")
                return jsonify({"warning": "Invalid username or password"}), 401

            if user and user.check_password(password):
                login_user(user)
                fetch_userdata(user)
                session['username'] = username
                session["logged_in_user"] = {
                    "id": user.userid,
                    "email": user.username,
                    "name": user.firstname
                }
                current_app.logger.info(f"User {username} logged in and stored in session.")
                return jsonify({"redirect": url_for("main.index")})

        except Exception as e:
            current_app.logger.error(f"🔥 Login crash: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    return render_template("login.html")

@user_bp.route("/logout")
@login_required
def logout():
    """
    Handles user logout.
    """
    logout_user()
    return redirect(url_for("user.login"))



@user_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    return render_template("settings.html")

@user_bp.route('/profile')
@login_required
def profile():
    user = Users.query.get(session.get("logged_in_user")["id"])
    return render_template("profile.html", user=user)



def fetch_userdata(user):
    """
    Fetches user data from the USERDATA table using Flask-SQLAlchemy.
    """
    try:
        username, firstname, lastname = user.get_userdetails()

        # Query the Users table using Flask-SQLAlchemy
        result = Users.query.filter_by(username=username).all()
        if result:
            current_app.logger.info(f"Fetched {len(result)} rows.")
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
            current_app.logger.warning("Username already exists. Skipping insert.")
            return

        # Insert the user
        new_user = Users(username=username, firstname=firstname, lastname=lastname)
        db.session.add(new_user)
        db.session.commit()
        current_app.logger.info(f"User {username} inserted successfully.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during insert: {str(e)}")
