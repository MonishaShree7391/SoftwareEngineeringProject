# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from sqlalchemy.ext.automap import automap_base

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
Base = automap_base()
