# authservice/app.py
from dotenv import load_dotenv
load_dotenv()

import time
from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt, bcrypt, Base
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
CORS(app)
#CORS(app, resources={r"/*": {"origins": "*"}})
app.config.from_object(Config)

db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)

with app.app_context():
    retries = 5
    while retries > 0:
        try:
            Base.prepare(db.engine, reflect=True)
            # Optional: example table assignment
            # User = Base.classes.users
            print("✓ Tables reflected successfully")
            for classname, class_ in Base.classes.items():
                print(f"- {classname}")
            print("--------------------------\n")
            break
        except OperationalError as e:
            retries -= 1
            print(f"✗ Database not ready: {e}. Retrying in 5 seconds...")
            time.sleep(5)

from debt_routes import debt_bp
app.register_blueprint(debt_bp, url_prefix="/debt")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)
