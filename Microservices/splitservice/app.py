# invoiceservice/app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, Base
from sqlalchemy.exc import OperationalError
from flask_jwt_extended import JWTManager  # ✅ Import JWT manager
import time

from split_routes import split_bp

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

#  JWT Configuration
app.config["JWT_SECRET_KEY"] = "auth-secret"  # Replace with secure value in production
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"

#  Initialize JWT
jwt = JWTManager(app)

# Initialize DB
db.init_app(app)
jwt.init_app(app)
# Reflect database
with app.app_context():
    retries = 5
    while retries > 0:
        try:
            Base.prepare(db.engine, reflect=True)
            print("✓ Tables reflected successfully in splitservice")
            print("\nReflected Tables:")
            for classname, class_ in Base.classes.items():
                print(f"- {classname}")
            print("--------------------------\n")
            break
        except OperationalError as e:
            retries -= 1
            print(f"✗ Database not ready: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Register blueprint
app.register_blueprint(split_bp, url_prefix="/split")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
