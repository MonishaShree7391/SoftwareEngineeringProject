import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify, current_app,render_template
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from extensions import db, Base
import logging

split_bp = Blueprint('split', __name__)
logger = logging.getLogger(__name__)


split_bp = Blueprint('split', __name__)
logger = logging.getLogger(__name__)

@split_bp.route('/add_split_invoice_user', methods=['POST'])
@jwt_required()
def add_split_user():
    try:
        #user = get_jwt_identity()
        #data = request.get_json()
        #email = data.get('email')
        #name = data.get('name')
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        #email = claims.get("username")
        #firstname = claims.get("firstname")
       #lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")
        #name = f"{firstname} {lastname}"
        # Example: Log the user details
        data = request.get_json()
        email = data.get("email")
        name = data.get("name")

        print(f"User ID: {user_id}, Username: {email},  Name: {name}")

        if not email or not name:
            logger.warning("Missing name or email in request")
            return jsonify({'error': 'Missing name or email'}), 400
        try:
            # Access Base.classes.groceries dynamically within the function
            #groceries = Base.classes.groceries
            #SplitInvoiceUser = Base.classes.SplitInvoiceUsers
            from app import Base
            groceries = Base.classes['groceries']
            SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"SplitInvoiceUser/groceries model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: SplitInvoiceUsers model not available'}), 500
        session = db.session
        #existing = session.query.filter_by(userid=user_id, email=email).first()
        existing = session.query(SplitInvoiceUser).filter_by(userid=user_id,email=email).first()

        if existing:
            logger.info(f"Split user {email} already exists for user {user_id}")
            return jsonify({'message': 'User already exists'}), 200

        new_user = SplitInvoiceUser(name=name, email=email, userid=user_id)
        session.add(new_user)
        session.commit()
        logger.info(f"Added new split user {email} for user {user_id}")
        return jsonify({'message': 'Split user added successfully'})

    except Exception as e:
        logger.error(f"Failed to add split user: {e}")
        return jsonify({'error': 'Failed to add user', 'details': str(e)}), 500


@split_bp.route('/my_split_users', methods=['GET'])
@jwt_required()
def my_split_users():
    try:
        print("Inside my_split_users ")
        user = get_jwt_identity()
        claims = get_jwt()
        user_id = user
        email = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Example: Log the user details
        print(f"User ID: {user_id}, Username: {email}, First Name: {firstname}")

        try:
            #SplitInvoiceUser = Base.classes.SplitInvoiceUsers
            from app import Base
            #groceries = Base.classes['groceries']
            SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
        except AttributeError as e:
            current_app.logger.error(f"SplitInvoiceUser model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        session = db.session
        users = session.query(SplitInvoiceUser).filter_by(userid=user_id).all()
        print("\n###USERS VALUES INSIDE SPLIT\n")
        #users = session.query.filter_by(userid=user_id).all()
        logger.info(f"Fetched {len(users)} split users for user {user_id}")
        return jsonify([
            {'name': u.name, 'email': u.email} for u in users
        ])
    except Exception as e:
        logger.error(f"Failed to fetch split users: {e}")
        return jsonify({'error': 'Failed to fetch split users', 'details': str(e)}), 500




@split_bp.route('/split_invoice', methods=['GET', 'POST'])
@jwt_required()
def split_invoice():
    print("inside split_invoice method")
    try:
        # Extract user identity and claims
        user_id = get_jwt_identity()
        claims = get_jwt()
        email = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")

        #bill_id = request.args.get('billId')
        #if not bill_id:
            #return jsonify({'error': 'Missing billId'}), 400

        try:
            #groceries = Base.classes.groceries
            #Users = Base.classes.users
            #SplitInvoiceUser = Base.classes.SplitInvoiceUsers
            #SplitInvoiceDetail = Base.classes.SplitInvoiceDetail
            #Settlements = Base.classes.settlements
            #DebtSettlementsBills = Base.classes.DebtSettlementsBills
            from app import Base
            groceries = Base.classes['groceries']
            SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
            Users=Base.classes['users']
            SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
            Settlements = Base.classes['settlements']
            DebtSettlementsBills = Base.classes['DebtSettlementsBills']
        except AttributeError as e:
            current_app.logger.error(f"Model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: model not available'}), 500

        session = db.session

        if request.method == 'GET':
            bill_id = request.args.get('billId')
            if not bill_id:
                return jsonify({'error': 'Missing billId'}), 400
            user = session.query(Users).filter_by(id=user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            logged_in_email = user.username
            logged_in_name = user.firstname

            print("logged_in_email: ",logged_in_email,"logged_in_name: ",logged_in_name )
            # Ensure user exists in SplitInvoiceUser
            existing = session.query(SplitInvoiceUser).filter_by(email=logged_in_email, userid=user_id).first()
            if not existing:
                session.add(SplitInvoiceUser(email=logged_in_email, name=logged_in_name, userid=user_id))
                session.commit()

            records = session.query(groceries).filter_by(userid=user_id, billId=bill_id).all()
            if not records:
                return jsonify({'error': 'No records found for this billId'}), 404
                #return render_template("split_invoice.html", message="No records found.")

            # Split users excluding self
            split_invoice_users = session.query(SplitInvoiceUser).filter(
                SplitInvoiceUser.userid == user_id,
                SplitInvoiceUser.email != logged_in_email
            ).all()

            # Build item list
            items_data = []
            for r in records:
                item_entry = {
                    'item': r.item,
                    'quantity': r.quantity,
                    'price': float(r.price),
                    'shared_with': "-"  # Default
                }

                # Attach shared_with if available
                splits = session.query(SplitInvoiceDetail).filter_by(
                    billId=bill_id, userid=user_id, item=r.item
                ).all()

                shared_emails = [s.shared_with for s in splits]
                if shared_emails:
                    item_entry["shared_with"] = ", ".join(shared_emails)

                items_data.append(item_entry)

            # Split summary: Paid By → Owed By → Amount
            settlements = session.query(Settlements).filter_by(
                billId=bill_id, userid=user_id
            ).all()

            debt_summary = [
                {
                    "paid_by": s.paid_by_email,
                    "owed_by": s.owed_by_email,
                    "amount": float(s.amount)
                } for s in settlements
            ]
            print("debt_summary: ",debt_summary)
            return jsonify({
                "billId": bill_id,
                "shopName": records[0].shopName if records else "",
                "address": records[0].address if records else "",
                "date": str(records[0].date) if records else "",
                "totalSum": float(records[0].totalSum) if records else 0.0,
                "items": items_data,
                "debtSettlement": debt_summary,
                "split_invoice_users": [
                    {"email": u.email, "name": u.name}
                    for u in split_invoice_users
                ],
                "logged_in_user": {
                    "email": logged_in_email,
                    "name": logged_in_name
                }
            })
            '''
            return render_template(
                'split_invoice.html',
                bill_info=bill_id,
                totalSum_info=records[0].totalSum if records else 0,
                address_info=records[0].address if records else '',
                date_info=records[0].date if records else '',
                items_data=items_data,
                split_invoice_users=split_invoice_users,
                logged_in_user={'email': logged_in_email, 'name': logged_in_name}
            )
            '''
        elif request.method == 'POST':
            data = request.get_json()

            bill_id = data.get('billId')
            paid_by = data.get('paid_by')
            items = data.get('items', [])
            overwrite = bool(data.get('overwrite', False))

            # ✅ Only check for paid_by and items
            if not bill_id or not paid_by or not items:
                return jsonify({'error': 'Missing required fields'}), 400

            user = session.query(Users).filter_by(id=user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            logged_in_email = user.username
            logged_in_name = user.firstname

            payer = session.query(SplitInvoiceUser).filter_by(email=paid_by, userid=user_id).first()
            if not payer:
                return jsonify({'error': 'Payer not found'}), 400

            paid_by_user_id = user_id if payer.email == logged_in_email else payer.id
            paid_by_email = payer.email

            existing_splits = session.query(SplitInvoiceDetail).filter_by(billId=bill_id, userid=user_id).count()
            if existing_splits > 0 and not overwrite:
                return jsonify({'warning': 'Bill is already split. Overwrite?', 'split_exists': True}), 200

            if overwrite:
                session.query(SplitInvoiceDetail).filter_by(billId=bill_id, userid=user_id).delete()
                session.query(Settlements).filter_by(billId=bill_id, userid=user_id).delete()
                session.query(DebtSettlementsBills).filter_by(billId=bill_id, created_by=user_id).delete()
                session.commit()

            # ✅ Loop through each item and extract users from within
            for item_obj in items:
                item = item_obj.get("item")
                users = item_obj.get("shared_with", [])

                if not item or not users:
                    continue

                item_record = session.query(groceries).filter_by(userid=user_id, billId=bill_id, item=item).first()
                if not item_record:
                    continue

                price = float(item_record.price)
                amount_per_user = price / len(users)

                for user_email in users:
                    owed_user = session.query(SplitInvoiceUser).filter_by(email=user_email, userid=user_id).first()
                    if not owed_user:
                        continue

                    owed_by_id = user_id if owed_user.email == logged_in_email else owed_user.id
                    owed_by_email = owed_user.email

                    session.add(SplitInvoiceDetail(
                        billId=bill_id,
                        item=item,
                        shared_with=owed_by_email,
                        amount=amount_per_user,
                        userid=user_id
                    ))

                    session.add(Settlements(
                        billId=bill_id,
                        paid_by=paid_by_user_id,
                        owed_by=owed_by_id,
                        paid_by_email=paid_by_email,
                        owed_by_email=owed_by_email,
                        amount=amount_per_user,
                        settled=False,
                        userid=user_id
                    ))

            session.commit()
            try:
                token = request.headers.get("Authorization")
                print("\ncalling notify_debt_service_bill_split\n")
                print(f"[DEBUG] Auth header: Bearer {token}")
                print(f"Bill_id: {bill_id}")
                notify_debt_service_bill_split(bill_id, token)
                notify_debt_service_overall(token)
            except Exception as e:
                print("Error in calling debtservice",e)
            return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Error in split_invoice route: {str(e)}")
        return jsonify({'error': 'Internal error', 'details': str(e)}), 500

import requests
#DEBT_SERVICE_URL = "http://debtservice:5004"
DEBT_SERVICE_URL = "http://localhost:5004"
def notify_debt_service_bill_split(bill_id, token):
    print("\n inside notify_debt_service_bill_split function \n ")
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    try:
        resp = requests.post(
            f"{DEBT_SERVICE_URL}/debt/calculate_from_bill/{bill_id}",
            headers={"Authorization": auth_header}
        )
        print(f"Debt calc triggered: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"Error notifying Debt Service: {e}")

def notify_debt_service_overall(token):
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    try:
        resp = requests.post(
            f"{DEBT_SERVICE_URL}/debt/calculate_overall",  # ✅ fixed formatting
            headers={"Authorization": auth_header}   # ✅ fixed missing Bearer
        )
        print(f"Overall debt calc triggered: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"Error triggering overall debt calculation: {e}")

