# authservice/app.py
from dotenv import load_dotenv
load_dotenv()

from config import Config
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base
import time
from flask import Flask
from flask_cors import CORS
from extensions import db, jwt, bcrypt

# ---- DB Connection Setup ----
Base = automap_base()
metadata = MetaData()

DB_SERVER = 'localhost'
DB_NAME = 'authdb'
DB_USER = 'sa'
DB_PASSWORD = '2025Online'
DB_DRIVER = 'ODBC Driver 17 for SQL Server'
connection_string = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}?driver={DB_DRIVER.replace(' ', '+')}"

# Retry DB connection + reflection
for attempt in range(10):
    try:
        print(f"\n⏳ Attempt {attempt+1}: Connecting to DB...")
        engine = create_engine(connection_string)
        print("connecting_string: ", connection_string)
        print("connecting_string:Config.SQLALCHEMY_DATABASE_URI",Config.SQLALCHEMY_DATABASE_URI)
        Base.prepare(engine, reflect=True)

        print("Reflected tables:", Base.classes.keys())
        if 'users' not in Base.classes:
            print("  'users' table not found.")
        else:
            print(" 'users' table found.")

        break
    except Exception as e:
        print(f"⏳ Attempt {attempt+1} failed: {e}")
        time.sleep(5)
else:
    print("  Could not connect to the database after multiple attempts.")
    exit(1)

# ---- Flask App Setup ----
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)

# Now that Base is ready, import routes
from auth_routes import auth_bp
app.register_blueprint(auth_bp, url_prefix="/auth")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
