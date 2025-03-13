from flask import Flask
from flask_session import Session
from app.models.models import init_models,Users, models,get_session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import create_engine
import os
from app.config.config import Config
from app.routes.main_routes import main_bp
from app.routes.user_routes import user_bp
from app.services.DatabaseConnection import db,Base
from sqlalchemy.ext.declarative import declarative_base

# Initialize Flask extensions
login_manager = LoginManager()

def create_app(config_class=Config):
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__, static_folder="../static")  # Ensure Flask knows where static files are
    app.config.from_object(config_class)
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)

    # Ensure necessary directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['IMAGE_FOLDER'], exist_ok=True)

    # Initialize SQLAlchemy
    try:
        db.init_app(app)
    except Exception as e:
        print(f"db.init__app failed: {e}")

    # Set up SQLAlchemy engine (optional, if you need engine separately)
    app.engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    print(app.config["SQLALCHEMY_DATABASE_URI"])

    try:
        with app.engine.connect() as connection:
            print("Database connection successful.")
    except Exception as e:
        print(f"Database connection failed: {e}")

    # Initialize models within the app context
    try:
        with app.app_context():
            try:
                init_models()
            except Exception as e:
                print(f"init_models() Failed to initialize models: {e}")
                raise
    except Exception as e:
        print(f"Failed to initialize models: {e}")

    # Set up Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'user.login'

    @login_manager.user_loader
    def load_user(user_id):
        """
        Callback to reload the user object from the user ID stored in the session.
        """
        return Users.query.get(user_id)  # Use the explicit Users model

    Session(app)  # Initialize session management
    return app
