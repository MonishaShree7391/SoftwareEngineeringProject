from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from extensions import db, Base
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

auth_bp = Blueprint('auth', __name__)

#User = Base.classes['users'] # Access reflected 'users' table
#if User:
    #print("User table loaded!!")

@auth_bp.route('/signup', methods=['POST'])
def signup():
    from app import Base
    User= Base.classes['users']
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing or invalid JSON'}), 400
    print('request: ', data)
    username = data.get('username')
    password = data.get('password')
    firstname = data.get('firstname')
    lastname = data.get('lastname')

    user = db.session.query(User).filter_by(username=username).first()
    if user:
        return jsonify({'error': 'Username already exists'}), 409

    user = User(
        username=username,
        firstname=firstname,
        lastname=lastname,
        password_hash=generate_password_hash(password)
    )

    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration failed: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        from app import Base
        User = Base.classes['users']
        data = request.get_json()
        print('request: ',data)
        username = data.get('username')
        password = data.get('password')
        try:
            #user = User.query.filter_by(username=username).first()
            user = db.session.query(User).filter_by(username=username).first()
        except Exception as e:
            current_app.logger.error(f"Login failed: {e}")
            return jsonify({'error': 'Login failed with database connection'}), 500

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401

        access_token = create_access_token(
                identity=str(user.id),
                additional_claims={
                    "username": user.username,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "is_admin": user.is_admin
                }
            )

        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'firstname': user.firstname,
                'lastname': user.lastname,
                'is_admin': user.is_admin
            }
        })
    except Exception as e:
        current_app.logger.error(f"Login failed: {e}")
        return jsonify({'error': 'Login failed internally'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    claims = get_jwt()
    return jsonify({
        "id": get_jwt_identity(),  # the user.id
        "username": claims.get("username"),
        "firstname": claims.get("firstname"),
        "lastname": claims.get("lastname"),
        "is_admin": claims.get("is_admin")
    })

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout placeholder – handle via token revocation'})

@auth_bp.route('/settings', methods=['POST'])
@jwt_required()
def change_password():
    from app import Base
    User = Base.classes['users']
    user_data = get_jwt_identity()
    userid= get_jwt_identity()
    user = db.session.query(User).filter_by(id=userid).first()
    #user = User.query.get(user_data['id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json()
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not new_password or new_password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    user.password_hash = generate_password_hash(new_password)
    try:
        db.session.commit()
        return jsonify({'message': 'Password updated successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password update failed: {str(e)}")
        return jsonify({'error': 'Password update failed'}), 500

@auth_bp.route("/api/users/<int:user_id>", methods=["GET"])
def get_user_by_id(user_id):
    from app import Base
    User = Base.classes['users']
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "is_admin": user.is_admin
    })
