from flask import Blueprint, request, jsonify, render_template, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from parser_helpers import create_dataframe
from date_utils import convert_date
from datetime import datetime
import os
import logging
from flask import Blueprint, render_template, request
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from extensions import db, Base
import requests
import logging

#SPLIT_SERVICE_URL = "http://splitservice:5003"
#DEBT_SERVICE_URL = "http://debtservice:5004"

SPLIT_SERVICE_URL = "http://localshost:5003"
DEBT_SERVICE_URL = "http://localshost:5004"
#try:
#    Grocery = Base.classes.groceries
#except AttributeError:
#    Grocery = None


invoice_bp = Blueprint('invoice', __name__)
logger = logging.getLogger(__name__)


UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {'pdf'}
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static', 'images')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_input(value):
    return value.isalnum() or all(c.isalnum() or c in ('_', '-', '.') for c in value)

@invoice_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_invoice():
    try:
        user = get_jwt_identity()
        user_id = user

        filename = request.form.get('filename')
        if not filename:
            return jsonify({'error': 'Missing filename'}), 400

        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        bill_id = filename.rsplit('.', 1)[0]
        print('BILL ID IN UPLOAD: ',bill_id)
        shop = request.form.get('NameOfTheShop')
        month = request.form.get('month')
        year = request.form.get('year')
        file = request.files.get('file')

        if not all([shop, month, year, file]):
            return jsonify({'error': 'Missing required fields'}), 400

        if not sanitize_input(filename + shop + month + year):
            return jsonify({'error': 'Invalid characters in input'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        # Save file
        upload_dir = os.path.join(UPLOAD_FOLDER, year, month)
        print('upload_dir: ',upload_dir)
        os.makedirs(upload_dir, exist_ok=True)
        pdf_path = os.path.join(upload_dir, filename)
        print('pdf_path: ', pdf_path)
        file.save(pdf_path)

        # Check for duplicate
        try:
            # Access Base.classes.groceries dynamically within the function
            from app import Base
            groceries = Base.classes['groceries']
            #groceries = Base.classes.groceries
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        session = db.session
        existing = session.query(groceries).filter_by(userid=user_id, billId=bill_id).count()
        if existing > 0:
            return jsonify({'warning': 'Bill already exists', 'Bill_exists': True}), 200
        try:
            df = create_dataframe(pdf_path, filename, month, year, shop.lower(), user_id)
            if df.empty:
                return jsonify({'warning': 'No data extracted from PDF'}), 200

            df['date'] = df['date'].apply(convert_date)
            inserted_count = 0
            for _, row in df.iterrows():
                entry = groceries(
                        userid=user_id,
                        billId=bill_id,
                        month=row['month'],
                        year=int(row['year']),
                        item=row['item'],
                        quantity=row['quantity'],
                        price=row['price'],
                        shopName=row['shopName'],
                        address=row['address'],
                        invoiceNumber=row['invoiceNumber'],
                        totalSum=row['totalSum'],
                        date=row['date']
                    )
                session.add(entry)
                inserted_count += 1

            session.commit()
            if inserted_count > 0:
                return jsonify({'success': True, 'message': f'Invoice {bill_id}- {inserted_count} items inserted','billId': bill_id})
            else:
                return jsonify({'warning': 'No items were inserted'}), 200
        #return jsonify({'success': True, 'message': 'Invoice uploaded successfully'})
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return jsonify({'error': 'Upload failed', 'details': str(e)}), 500
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500


@invoice_bp.route('/check_filename', methods=['POST'])
@jwt_required()
def check_filename():
    try:
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Example: Log the user details
        print(f"User ID: {user_id}, Username: {username}, First Name: {firstname}")

        #user = get_jwt_identity()
        #user_id = user['id']
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'Missing filename'}), 400

            # Dynamically get the Grocery model here
        try:
                #Grocery = Base.classes.groceries
                #Grocery = Base.classes['groceries']
                from app import Base
                Grocery = Base.classes['groceries']
        except AttributeError:
                # If reflection somehow failed or table not found (shouldn't happen if previous check passed)
                current_app.logger.error("Grocery model not reflected. Database connection or table issue.")
                return jsonify({'error': 'Internal server error: Grocery model not found'}), 500

        session = db.session
        exists = session.query(Grocery).filter_by(userid=user_id, billId=filename).first() is not None
        return jsonify({'exists': exists})

    except Exception as e:
        logger.error(f"Filename check failed: {e}")
        return jsonify({'error': 'Check failed', 'details': str(e)}), 500

@invoice_bp.route('/view_invoices_by_month', methods=['GET'])
@jwt_required()
def view_by_month():
    try:
        user_id = get_jwt_identity()
        month = request.args.get('month', '').lower()  #   Normalize to lowercase
        year = request.args.get('year')

        print(f"[INVOICE_SERVICE] Fetching invoices for user {user_id} - Month: {month}, Year: {year}")
        groceries = Base.classes['groceries']
        #groceries = Base.classes.groceries
        session = db.session
        records = session.query(groceries).filter_by(userid=user_id, month=month, year=year).all()

        print(f"[INVOICE_SERVICE] Found {len(records)} matching invoices.")

        # Group by unique billId (only keep first entry per bill)
        unique_bills = {}
        for r in records:
            if r.billId not in unique_bills:
                unique_bills[r.billId] = r
                if not r.billId.endswith('.pdf'):
                    filename_pdf = r.billId + '.pdf'
                else:
                    filename_pdf = r.billId
        bills = []
        for r in unique_bills.values():
            pdf_url=f"/invoice/static/uploads/{r.year}/{r.month}/{filename_pdf}"
            bill = {
                "billId": r.billId,
                "shop": r.shopName,
                "date": r.date,
                "total": float(r.totalSum),
                "pdf_url": pdf_url
            }
            bills.append(bill)
        return jsonify({"bills": bills})

    except Exception as e:
        logger.error(f"Error viewing invoices: {e}")
        return jsonify({"error": "Failed to retrieve invoices", "details": str(e)}), 500




@invoice_bp.route('/view', methods=['GET'])
@jwt_required()
def view_data():
    try:
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Now you can use user_id, username, firstname, etc.
        # Example: Log the user details
        print(f"User ID: {user_id}, Username: {username}, First Name: {firstname}")

        bill_id = request.args.get('billId')

        if not bill_id:
            print('Bill ID not found!!')
            return jsonify({'error':'Missing bill ID'}),500
        else:
            print('BILL_ID: ',bill_id)
        #groceries = models.get("groceries")
        try:
            # Access Base.classes.groceries dynamically within the function
            groceries = Base.classes['groceries']
            Users = Base.classes['users']
            #groceries = Base.classes.groceries
            #Users = Base.classes.users
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        session = db.session
        records = session.query(groceries).filter_by(userid=user_id, billId=bill_id).all()
        if not records:
            print('no records found!')
            return jsonify({'warning': 'No records found'}), 404
            #return render_template("view.html", message="No records found.")

        record = records[0]
        items_data = [
                {
                    'item': r.item,
                    'quantity': r.quantity,
                    'price': r.price,
                    'shared_with': ''  # To be filled from split service
                } for r in records
            ]

        #   Optional: Fetch shared_with from split service
        #   Fetch shared_with from split service via /split_invoice
        try:
            split_resp = requests.get(
                f"{SPLIT_SERVICE_URL}/split/split_invoice",
                headers={
                    "Authorization": request.headers.get("Authorization"),
                    "Accept": "application/json"
                },
                params={"billId": bill_id}
            )

            if split_resp.ok:
                split_data = split_resp.json()
                shared_map = {
                    item["item"].lower(): item.get("shared_with", [])
                    for item in split_data.get("items", [])
                }

                for item_data in items_data:
                    item_name = item_data["item"].lower()
                    if item_name in shared_map:
                        raw_shared = shared_map[item_name]
                        if isinstance(raw_shared, str):
                            emails = [e.strip() for e in raw_shared.split(",") if e.strip()]
                        else:
                            emails = raw_shared

                        item_data["shared_with"] = ", ".join(emails)

        except Exception as e:
            logger.warning(f"Split service failed: {e}")

        #   Optional: Fetch debt info from settlement service
        debt_settlement_details = []
        try:
            debt_resp = requests.get(
                f"{DEBT_SERVICE_URL}/debt/settlements/{bill_id}",
                headers={
                    "Authorization": request.headers.get("Authorization"),
                    "Accept": "application/json"
                },
                params={"user_id": user_id}
            )
            if debt_resp.ok:
                debt_settlement_details = debt_resp.json()
                print("+++Settlement service details: ",debt_settlement_details)
        except Exception as e:
            logger.warning(f"Settlement service failed: {e}")

        logged_in_user = session.query(Users).filter_by(id=user_id).first()
        # Convert only the needed fields to dict
        user_info = {
            "firstname": logged_in_user.firstname,
            "lastname": logged_in_user.lastname,
            "email": logged_in_user.username
        } if logged_in_user else None
        '''
        return jsonify(
            bill_info=record.billId,
            totalSum=record.totalSum,
            address_info=record.address,
            ShopName=record.shopName,
            date_info=record.date,
            items_data=items_data,
            selected_date=record.date,
            debt_settlement_details=debt_settlement_details,
            logged_in_user=user_info

        )'''
        print("debtSettlement: ",debt_settlement_details)
        return jsonify(
            billId=record.billId,
            totalSum=record.totalSum,
            address=record.address,
            shopName=record.shopName,
            date=record.date,
            items=items_data,
            debtSettlement=debt_settlement_details,
            user=user_info
        )
    except Exception as e:
        logger.error(f"View data failed: {e}")
        return jsonify({'error': 'Failed to load invoice view data'}), 500

@invoice_bp.route('/get_invoice_years', methods=['GET'])
@jwt_required()
def get_invoice_years():
    try:
        # Get the full JWT payload
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Now you can use user_id, username, firstname, etc.
        # Example: Log the user details
        print(f"get_invoice_years: User ID: {user_id}, Username: {username}, First Name: {firstname}")

        session = db.session
        try:
            # Access Base.classes.groceries dynamically within the function
            #groceries = Base.classes.groceries
            groceries = Base.classes['groceries']
            #Users = Base.classes['users']
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        #years = session.query(groceries.year).filter_by(userid=user_id).distinct().all()
        years = [y[0] for y in session.query(groceries.year).filter_by(userid=user_id).distinct().all()]
        #year_list = [y[0] for y in years if y[0]]
        return jsonify({'years': years})
    except Exception as e:
        import traceback
        print("  ERROR in get_invoice_years:", traceback.format_exc())  # Add this for debugging
        return jsonify({'error': 'Could not fetch years', 'details': str(e)}), 500

@invoice_bp.route('/get_invoice_months/<int:year>', methods=['GET'])
@jwt_required()
def get_invoice_months(year):
    try:
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Example: Log the user details
        print(f"get_invoice_months: User ID: {user_id}, Username: {username}, First Name: {firstname}")
        session = db.session
        try:
            # Access Base.classes.groceries dynamically within the function
            groceries = Base.classes['groceries']
            #Users = Base.classes['users']
            #groceries = Base.classes.groceries
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        months = session.query(groceries.month).filter_by(userid=user_id, year=year).distinct().all()
        month_list = [m[0] for m in months if m[0]]
        return jsonify({'months': month_list})
    except Exception as e:
        logger.error(f"Failed to fetch invoice months: {e}")
        return jsonify({'error': 'Could not fetch months'}), 500

@invoice_bp.route('/view_invoices_by_month', methods=['GET'])
@jwt_required()
def view_invoices_by_month():
    try:
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Example: Log the user details
        print(f"view_invoices_by_month : User ID: {user_id}, Username: {username}, First Name: {firstname}")
        month = request.args.get('month')
        year = request.args.get('year')

        if not (month and year):
            return jsonify({'error': 'Missing month or year'}), 400
        try:
            # Access Base.classes.groceries dynamically within the function
            #groceries = Base.classes.groceries
            groceries = Base.classes['groceries']
            #Users = Base.classes['users']
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500
        records = db.session.query(groceries).filter_by(userid=user_id, month=month, year=year).all()

        if not records:
            return jsonify({'bills': []})

        # Group by unique billId (only keep first entry per bill)
        unique_bills = {}
        for r in records:
            if r.billId not in unique_bills:
                unique_bills[r.billId] = r

        bills = []
        for r in unique_bills.values():
            bill = {
                "billId": r.billId,
                "shop": r.shopName,
                "date": r.date,
                "total": float(r.totalSum),
                "pdf_url": f"/static/uploads/{r.year}/{r.month}/{r.billId}.pdf"
            }
            bills.append(bill)

        return jsonify({"bills": bills})
    except Exception as e:
        logger.error(f"Failed to fetch invoices by month: {e}")
        return jsonify({'error': 'Internal error'}), 500

@invoice_bp.route('/view_data_by_date', methods=['GET'])
@jwt_required()
def view_data_by_date():
    """
    Fetches invoice data for a specific date for the authenticated user.
    If found, returns a redirect URL for the detailed view.
    """
    try:
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Example: Log the user details
        print(f"view_data_by_date:view_data_by_dateUser ID: {user_id}, Username: {username}, First Name: {firstname}")
        selected_date = request.args.get('date')

        if not selected_date:
            return jsonify({'error': 'Date parameter is required'}), 400

        try:
            # Access Base.classes.groceries dynamically within the function
            #groceries = Base.classes.groceries
            groceries = Base.classes['groceries']
            #Users = Base.classes['users']
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        session = db.session
        record = session.query(groceries).filter_by(userid=user_id, date=selected_date).first()

        if not record:
            return jsonify({'warning': f'No records found for {selected_date}'}), 200

        return jsonify({'redirect': f"/view?billId={record.billId}"})  #  

    except Exception as e:
        logger.error(f"Error in view_data_by_date: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@invoice_bp.route('/view_data', methods=['GET'])
@jwt_required()
def view_data_1():
    """
    Fetches detailed invoice data for a given bill ID and returns structured data.
    This can later be used to render a detailed invoice page.
    """
    try:
        claims = get_jwt()  # This will be a dictionary containing all claims

        # Access the identity directly (as it's the primary subject of the token)
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        username = claims.get("username")
        firstname = claims.get("firstname")
        lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")

        # Example: Log the user details
        print(f"view_data: User ID: {user_id}, Username: {username}, First Name: {firstname}")
        bill_id = request.args.get('billId')

        if not bill_id:
            return jsonify({'error': 'Missing billId parameter'}), 400

        try:
            # Access Base.classes.groceries dynamically within the function
            #groceries = Base.classes.groceries
            groceries = Base.classes['groceries']
            #Users = Base.classes['users']
        except AttributeError as e:
            # This error means 'groceries' table was not reflected
            current_app.logger.error(f"Grocery model not found in Base.classes: {e}")
            return jsonify({'error': 'Internal server error: Grocery model not available'}), 500

        session = db.session
        records = session.query(groceries).filter_by(userid=user_id, billId=bill_id).all()

        if not records:
            return jsonify({'warning': f'No records found for Bill ID: {bill_id}'}), 200

        invoice_data = {
            "billId": bill_id,
            "shopName": records[0].shopName,
            "date": records[0].date,
            "address": records[0].address,
            "totalSum": float(records[0].totalSum),
            "items": [
                {
                    "item": r.item,
                    "quantity": r.quantity,
                    "price": float(r.price)
                }
                for r in records
            ]
        }

        return jsonify(invoice_data)

    except Exception as e:
        logger.error(f"Failed to fetch invoice data for billId={request.args.get('billId')}: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
