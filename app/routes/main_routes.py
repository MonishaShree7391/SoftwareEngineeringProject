from flask import Blueprint, request, current_app, jsonify, render_template, redirect, url_for
from flask import session
from sqlalchemy import func
from flask_login import login_required
import os
import logging
import pandas as pd
from app.services.groceries import ImageScanner
from app.models.models import Users, models, SplitInvoiceUser, get_session, SplitInvoiceDetail, Settlements, \
    DebtSettlements, DebtSettlementsBills,DebtSummary
from app.utils.dataHelpers import convert_date, create_dataframe
from app.utils.ReadPdf import pdf_to_jpg, extract_text_from_pdf
from sqlalchemy.orm import aliased
from datetime import datetime

# Blueprint setup
main_bp = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    """
    Check if a file's extension is allowed.
    """
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main_bp.route('/index')
def index():
    return render_template('index.html')


@main_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """
    Handles file uploads by saving the file and recording metadata in the database.
    """
    try:
        # Fetch and validate inputs
        filename = request.form.get('filename')
        session['billid'] = filename

        NameOfTheShop = request.form.get('NameOfTheShop')
        session['NameOfTheShop'] = NameOfTheShop.lower()

        month = request.form.get('month').lower()
        year = request.form.get('year')

        # Debugging log to verify values are received correctly
        logger.info(f"Received Upload: filename={filename}, shop={NameOfTheShop}, month={month}, year={year}")

        if  filename is None:
            logger.error("Missing filename  in the request.")
            return jsonify({'error': 'Missing filename'}), 400
        if month is None or '':
            logger.error("Missing  month in the request.")
            return jsonify({'error': 'Missing month'}), 400
        if year is None or '':
            logger.error("Missing  year in the request.")
            return jsonify({'error': 'Missing year'}), 400
        if NameOfTheShop is None:
            logger.error("Missing  ShopNmae in the request.")
            return jsonify({'error': 'Missing ShopNmae'}), 400

        if not sanitize_input(filename) or not sanitize_input(month) or not sanitize_input(year) or not sanitize_input(NameOfTheShop):
            logger.error("Invalid characters detected in input.")
            return jsonify({'error': 'Input contains invalid characters.'}), 400

        # Check if the uploaded file is present
        if 'file' not in request.files:
            logger.error("No file part in the request.")
            return jsonify({'error': 'No file part in the request.'}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file.")
            return jsonify({'error': 'No selected file.'}), 400

        if not allowed_file(file.filename):
            logger.error(f"File type not allowed: {file.filename}")
            return jsonify({'error': 'File type not allowed. Only PDF files are accepted.'}), 400

        # Save the uploaded file
        year_month_directory = os.path.join(current_app.config['UPLOAD_FOLDER'], year, month)
        os.makedirs(year_month_directory, exist_ok=True)
        print(f"Directory created: {year_month_directory}")
        pdf_path = os.path.join(year_month_directory, filename)
        file.save(pdf_path)

        # Fetch the user ID from the session

        userid = fetch_user_id_from_session()
        if not userid:
            logger.error("User ID not found in session or database.")
            return jsonify({'error': 'User not authenticated or invalid session.'}), 403

        shopname = session.get('NameOfTheShop').lower()
        modelShop = models.get("groceries")
        if not modelShop:
            logger.error("groceries model not initialized.")
            return jsonify({'error': 'groceries table is not available.'}), 500

        with get_session() as db_session:
            # Check for duplicates
            existing_count = db_session.query(modelShop).filter_by(userid=userid, billId=filename).count()

            if existing_count > 0:
                logger.info(f"Bill ID {filename} already exists in the database. Skipping insertion.")
                return redirect(url_for('main.view_data'))
            else:
                # Generate the DataFrame using the create_dataframe function

                df = create_dataframe(pdf_path, filename, month, year, shopname, userid)
                if df.empty:
                    logger.info("No data extracted from the PDF.")
                    # return render_template('view_bk30jan.html', message="No records found.")

                df['date'] = df['date'].apply(convert_date)
                # Insert metadata
                try:
                    for index, row in df.iterrows():
                        new_entry = modelShop(
                            userid=int(userid),
                            billId=filename,
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
                        db_session.add(new_entry)

                    db_session.commit()
                    logger.info(f"File metadata for {filename} recorded successfully.")
                    return redirect(url_for('main.view_data'))
                except Exception as e:
                    db_session.rollback()  # Rollback on error
                    logger.error(f"Error inserting data: {str(e)}")
                    return jsonify({'error': 'Database error.', 'details': str(e)}), 500


    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500

@main_bp.route('/check_filename', methods=['POST'])
@login_required
def check_filename():
    """
    Check if a filename already exists in the database.
    """
    try:
        filename = request.form.get('filename')
        if not filename:
            logger.error("Missing filename in the request.")
            return jsonify({'error': 'Missing filename.'}), 400

        userid = fetch_user_id_from_session()
        if not userid:
            logger.error("User ID not found in session or database.")
            return jsonify({'error': 'User not authenticated or invalid session.'}), 403

        modelShop = models.get("groceries")
        if not modelShop:
            logger.error("groceries model not initialized.")
            return jsonify({'error': 'groceries table is not available.'}), 500

        with get_session() as db_session:
            existing_count = db_session.query(modelShop).filter_by(userid=userid, billId=filename).count()
            if existing_count > 0:
                return jsonify({'exists': True}), 200
            else:
                return jsonify({'exists': False}), 200

    except Exception as e:
        logger.error(f"Error during filename check: {str(e)}")
        return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500

@main_bp.route('/view', methods=['GET'])
@login_required
def view_data():
    """
    Fetches data for the authenticated user and displays item details
    associated with the Bill ID from the session.
    """
    try:
        # Fetch user ID from the session
        userid = fetch_user_id_from_session()
        if not userid:
            logger.error("User ID not found in session.")
            return jsonify({'error': 'User not authenticated or invalid session.'}), 403

        # Fetch the Bill ID from the session
        billid = session.get('billid')
        if not billid:
            logger.error("Bill ID not found in session.")
            return jsonify({'error': 'Bill ID not found in session.'}), 400

        # Query the database for the user's uploaded file records based on userid and billId

        modelShop = models.get("groceries")
        if not modelShop:
            logger.error(f"{modelShop} model not initialized.")
            return jsonify({'error': 'groceries table is not available.'}), 500

        with get_session() as db_session:
            # Query for records that match the user ID and Bill ID
            records = db_session.query(modelShop).filter_by(userid=userid, billId=billid).all()

            if not records:
                logger.info(f"No uploaded files found for user {userid} with Bill ID {billid}.")
                return render_template('view.html', message="No records found.")

            else:
                # Process the records to extract details
                bill_info = records[0].billId  # Assuming all records belong to the same Bill ID
                totalSum_info = records[0].totalSum
                address_info = records[0].address  # Assuming the same address for all records
                date_info = records[0].date  # Assuming the same date for all records
                ShopName = records[0].shopName
                # Fetch debt settlement details for the bill ID
                debt_settlement_details = fetch_debt_settlement_details(billid)
                # Prepare the item data to display in the table


                split_details = db_session.query(SplitInvoiceDetail).filter_by(billId=billid).all()
                # Fetch split invoice users (InvoiceUsers) to build an email-to-name mapping.
                split_invoice_users = db_session.query(SplitInvoiceUser).filter_by(userid=userid).all()

                # Build mapping from email to name.
                email_to_name = {user.email: user.name for user in split_invoice_users}
                # Build the initial items_data from groceries records.
                items_data = [
                    {
                        'item': record.item,
                        'quantity': record.quantity,
                        'price': record.price,
                        'shared_with': ''  # default empty if not split
                    }
                    for record in records
                ]

                # If split details exist, merge the shared_with info.
                if split_details:
                    # Create a mapping from item to list of shared_with emails.
                    shared_map = {}
                    for detail in split_details:
                        # Use the item as key; append the shared user (you might choose to display email or name)
                        name = email_to_name.get(detail.shared_with, detail.shared_with)
                        shared_map.setdefault(detail.item, []).append(name)

                    # Update items_data with the shared_with information.
                    for item_data in items_data:
                        if item_data['item'] in shared_map:
                            item_data['shared_with'] = ', '.join(shared_map[item_data['item']])

                # Also fetch split_invoice_users and logged in user info as before.
                split_invoice_users = db_session.query(SplitInvoiceUser).filter_by(userid=userid).all()
                logged_in_user = db_session.query(Users).filter_by(userid=userid).first()
                return render_template(
                    'view.html',
                    bill_info=bill_info,
                    totalSum_info=totalSum_info,
                    address_info=address_info,
                    ShopName=ShopName,
                    date_info=date_info,
                    items_data=items_data,
                    selected_date=date_info,
                    debt_settlement_details=debt_settlement_details,
                    split_invoice_users = split_invoice_users,
                    logged_in_user = logged_in_user
                # Assuming you want to show the date in the header
                )

    except Exception as e:
        logger.error(f"Error processing view data: {str(e)}")
        return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500


@main_bp.route('/view_data_by_date', methods=['GET'])
@login_required
def view_data_by_date():
    """
    Fetches and displays data from the groceries table for the authenticated user,
    filtered by a specific date. Then redirects to the main view page with the Bill ID.
    """
    try:
        # Get the selected date from the request arguments.
        selected_date = request.args.get('date') or request.args.get('datePicker')
        if not selected_date:
            logger.error("No date provided in the request.")
            return render_template('view_data.html', message="Please provide a valid date.")

        # Debugging log to check the received date
        logger.info(f"Received selected_date: {selected_date}")

        # Fetch the user ID from the session.
        userid = fetch_user_id_from_session()
        if not userid:
            logger.error("User ID not found in session.")
            return jsonify({'error': 'User not authenticated or invalid session.'}), 403

        with get_session() as db_session:
            # Retrieve the groceries model.
            modelShop = models.get("groceries")
            if not modelShop:
                logger.error("groceries model not initialized.")
                return jsonify({'error': 'groceries table is not available.'}), 500

            # Query records for the given userid and selected date.
            records = db_session.query(modelShop).filter_by(userid=userid, date=selected_date).all()
            if not records:
                logger.info(f"No records found for user {userid} on {selected_date}.")
                return jsonify({'warning': f'No records found for {selected_date}'}), 200

            # **Fetch Bill ID from the first record since all records for the date should belong to the same bill**
            billid = records[0].billId

            # **Store the Bill ID in the session**
            session['billid'] = billid

            # **Redirect to `/view` so that it can use the Bill ID from the session**
            return redirect(url_for('main.view_data'))

    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return render_template('view_data.html', message="An error occurred while fetching data.")




@main_bp.route('/split_invoice', methods=['GET', 'POST'])
@login_required
def split_invoice():
    try:
        userid = fetch_user_id_from_session()
        if not userid:
            return jsonify({'error': 'User not authenticated'}), 403

        billid = session.get('billid')
        if not billid:
            logger.error("Bill ID  not found in session.")
            return jsonify({'error': 'Bill ID or User ID not found in session.'}), 400

        groceries = models.get("groceries")
        if not groceries:
            logger.error(f"{groceries} model not initialized.")
            return jsonify({'error': f'{groceries} table is not available.'}), 500

        if request.method == 'GET':

            with get_session() as db_session:

                    # Fetch the logged-in user from Users table
                    logged_in_user = db_session.query(Users).filter_by(userid=userid).first()

                    if logged_in_user:
                        logged_in_user_email = logged_in_user.username  # Convert ID to email
                        logged_in_user_name = logged_in_user.firstname
                    else:
                        logger.error("Logged-in user not found in Users table.")
                        return jsonify({'error': 'Logged-in user not found.'}), 400

                    # Ensure logged-in user is included in the list
                    split_invoice_user_for_loggedinUser = db_session.query(SplitInvoiceUser).filter_by(email=logged_in_user_email).first()

                    if not split_invoice_user_for_loggedinUser:
                        #   Insert logged-in user into SplitInvoiceUser with correct userid
                        new_split_user = SplitInvoiceUser(
                            email=logged_in_user_email,
                            name=logged_in_user_name,
                            userid=userid  #   Ensures `userid` matches Users table
                        )
                        db_session.add(new_split_user)
                        db_session.commit()
                        logger.info(f"Logged-in user {logged_in_user_email} added to SplitInvoiceUser.")

                    # Fetch all the items from the bill
                    records = db_session.query(groceries).filter_by(userid=userid, billId=billid).all()
                    if not records:
                        logger.info(f"No records found for Bill ID {billid}.")
                        return render_template('split_invoice.html', message="No records found.")

                    # Fetch all users from SplitInvoiceUser for this logged-in user EXCLUDING THE LOGGEDIN USER RECORD
                    split_invoice_users = db_session.query(SplitInvoiceUser).filter(
                        SplitInvoiceUser.userid == userid, SplitInvoiceUser.email != logged_in_user_email
                    ).all()

                    items_data = [
                        {
                        'item': record.item,
                        'quantity': record.quantity,
                        'price': record.price
                        }
                    for record in records
                    ]

                    return render_template(
                        'split_invoice.html',
                        bill_info=billid,
                        totalSum_info=records[0].totalSum if records else 0,
                        address_info=records[0].address if records else '',
                        date_info=records[0].date if records else '',
                        items_data=items_data,
                        split_invoice_users=split_invoice_users,
                        logged_in_user={'email': logged_in_user_email, 'name': logged_in_user_name}
                    )

        elif request.method == 'POST':
            # Handle form submission for splitting the bill
            try:
                userid = fetch_user_id_from_session()
                if not userid:
                    logger.error("User ID not found in session.")
                    return jsonify({'error': 'User not authenticated or invalid session.'}), 403

                logger.info("Incoming Headers: %s", request.headers)
                logger.info("Raw Data: %s", request.data)

                data = request.get_json()
                paid_by = data.get('paid_by')  # Email of the payer
                items = data.get('items', [])
                shared_with = data.get('shared_with', [])
                overwrite = bool(data.get('overwrite', False))  # Ensure boolean type

                if not paid_by or not items or not shared_with:
                    logger.error("Paid by, items, or shared_with data is missing.")
                    return jsonify({'error': 'Required fields are missing.'}), 400

                with get_session() as db_session:
                    billid = session.get('billid')
                    logged_in_user = db_session.query(Users).filter_by(userid=userid).first()
                    if logged_in_user:
                        logged_in_user_email = logged_in_user.username  # Convert ID to email
                        logged_in_user_name = logged_in_user.firstname
                        logged_in_user_id = logged_in_user.userid
                    else:
                        logger.error("Logged-in user not found in Users table.")
                        return jsonify({'error': 'Logged-in user not found.'}), 400

                    #  Ensure `paid_by` is used correctly (fetch by email, not ID)
                    payer = db_session.query(SplitInvoiceUser).filter(SplitInvoiceUser.email == paid_by).first()


                    #check if payer email id loggedin user email, if yes, then fetch the loggedin userid to payerid and
                    if payer:
                        logger.info(f"Payer found: ID={payer.id}, Email={payer.email}, Name={payer.name}")
                        if payer.email == logged_in_user_email:
                            logger.info(f"Payer is the logged-in user. Updating payer ID to match Users table.")
                            payer.id = logged_in_user_id #  Ensure payer.id matches logged-in user ID
                            paid_by_email = payer.email
                        else:
                             # Ensure payer.id matches logged-in user email
                            paid_by_email = payer.email
                    else:
                            logger.error(f"Payer with email {paid_by} not found.")
                            return jsonify({'error': 'Payer not found.'}), 400

                    #  Use `payer.email` in further processing (not `payer.id`)
                    final_paid_by = payer.email

                    #  Check if bill is already split
                    existing_splits = db_session.query(SplitInvoiceDetail).filter_by(billId=billid).count()
                    if existing_splits > 0 and not overwrite:
                        logger.warning(f"Bill {billid} is already split.")
                        return jsonify({'warning': 'Bill is already split. Overwrite?', 'split_exists': True}), 200

                    #  If overwrite is confirmed, remove existing splits
                    if overwrite:
                        db_session.query(SplitInvoiceDetail).filter_by(billId=billid).delete()
                        db_session.commit()
                        logger.info(f"Previous split details for Bill ID {billid}  in SplitInvoiceDetail deleted.")
                        db_session.query(Settlements).filter_by(billId=billid).delete()
                        db_session.commit()
                        logger.info(f"Previous split details for Bill ID {billid}  in Settlements deleted.")
                        db_session.query(DebtSettlementsBills).filter_by(billId=billid).delete()
                        db_session.commit()
                        logger.info(f"Previous split details for Bill ID {billid}  in DebtSettlementsBills deleted.")
                        db_session.commit()
                        logger.info(f"Previous split details for Bill ID {billid} deleted.")

                    #   Now process items and shared users
                    groceries = models.get("groceries")
                    if not groceries:
                        logger.error("groceries model not initialized.")
                        return jsonify({'error': 'groceries table is not available.'}), 500

                    for item, users in zip(items, shared_with):
                        item_record = db_session.query(groceries).filter_by(billId=billid, item=item).first()
                        if not item_record:
                            logger.error(f"Item {item} not found in the database.")
                            continue

                        price = float(item_record.price)
                        num_users = len(users)
                        amount_per_user = price / num_users

                        for user_email in users:
                            shared_user = db_session.query(SplitInvoiceUser).filter_by(email=user_email).first()
                            if shared_user:
                                if shared_user.email == logged_in_user_email:
                                    logger.info(f"Owed user is logged-in user.")
                                    owed_by_id = logged_in_user_id
                                    owed_by_email = shared_user.email
                                    logger.info(f"Using User's ID {logged_in_user_id} from Users table.")
                                else:
                                    owed_by_id = shared_user.id
                                    owed_by_email = shared_user.email
                            else:
                                logger.error(f"User with email {user_email} not found.")
                                continue

                            #  Store `email` instead of `id`
                            try:
                                new_split_detail = SplitInvoiceDetail(
                                    billId=billid,
                                    item=item,
                                    shared_with=user_email,
                                    amount=amount_per_user,
                                    userid=userid
                                )
                                db_session.add(new_split_detail)
                            except Exception as e:
                                logger.error(f"Error during new_split_detail: {str(e)}")
                                return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500
                            try:
                                logger.info(f"Inside new_settlement:")
                                new_settlement = Settlements(
                                    billId=billid,
                                    paid_by=payer.id,
                                    owed_by=owed_by_id,
                                    paid_by_email=paid_by_email,
                                    owed_by_email=owed_by_email,
                                    amount=amount_per_user,
                                    settled=False,
                                    userid=userid
                                )

                                db_session.add(new_settlement)
                                logger.info(f"successfully added new_settlement")
                            except Exception as e:
                                logger.error(f"Error during new_settlement: {str(e)}")
                                return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500
                    db_session.commit()
                    #   Final debt calculations
                    calculate_debts_basedON_billId(billid, db_session, current_user_id=userid)
                    calculate_overall_debts_and_insert(db_session, current_user_id=userid)


                    return jsonify({'success': True}), 200
            except Exception as e:
                logger.error(f"Error during split invoice: {str(e)}")
                return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500


    except Exception as e:
        logger.error(f"Error during split invoice: {str(e)}")
        return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500



@main_bp.route('/add_split_invoice_user', methods=['POST'])
@login_required
def add_split_invoice_user():
    """
    Adds a new user to the SplitInvoiceUser table.
    """
    try:
        userid = fetch_user_id_from_session()
        if not userid:
            logger.error("User ID not found in session.")
            return jsonify({'error': 'User not authenticated or invalid session.'}), 403

        email = request.form.get('email')
        name = request.form.get('name')

        if not email or not name:
            logger.error("Email and name are required.")
            return jsonify({'error': 'Email and name are required.'}), 400

        with get_session() as db_session:
            # Check if the user already exists
            existing_user = db_session.query(SplitInvoiceUser).filter_by(email=email).first()
            if existing_user:
                logger.info(f"User with email {email} already exists.")
                return jsonify({'error': 'User already exists.'}), 400

            # Add new user
            new_user = SplitInvoiceUser(email=email, name=name, userid=userid)
            db_session.add(new_user)
            db_session.commit()

            logger.info(f"New user added: {email}")
            return jsonify({'success': True, 'message': 'User added successfully.'})

    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        db_session.rollback()  # Rollback in case of error
        return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500



@main_bp.route('/add_split_invoice_user', methods=['POST'])
@login_required
def add_split_invoice_user_new():
    """
    Adds a new user to the SplitInvoiceUser table.
    """
    try:
        userid = fetch_user_id_from_session()
        if not userid:
            logger.error("User ID not found in session.")
            return jsonify({'error': 'User not authenticated or invalid session.'}), 403

        email = request.form.get('email')
        name = request.form.get('name')

        if not email or not name:
            logger.error("Email and name are required.")
            return jsonify({'error': 'Email and name are required.'}), 400

        with get_session() as db_session:
            # Check if the user already exists
            existing_user = db_session.query(SplitInvoiceUser).filter_by(email=email).first()
            if existing_user:
                logger.info(f"User with email {email} already exists.")
                return jsonify({'error': 'User already exists.'}), 400

            # Add new user
            new_user = SplitInvoiceUser(email=email, name=name, userid=userid)
            db_session.add(new_user)
            db_session.commit()

            logger.info(f"New user added: {email}")
            return jsonify({'success': True, 'message': 'User added successfully.'})

    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        db_session.rollback()  # Rollback in case of error
        return jsonify({'error': 'An internal error occurred.', 'details': str(e)}), 500

@main_bp.route('/balances', methods=['GET'])
@login_required
def view_balances():
    """
    View overall balance details and per-person breakdown for the logged-in user.
    """
    print('Inside View_Balances')
    user_email =  session.get('username') # Fetch the logged-in user's email
    if not user_email:
        return jsonify({'error': 'User not authenticated or invalid session.'}), 403

    with get_session() as db_session:
        # Overall Totals:
        # Total Money Owed: when the user is the creditor (paid_by_email == user_email)
        total_money_owed = db_session.query(
            func.coalesce(func.sum(DebtSettlementsBills.amount), 0)
        ).filter(
            DebtSettlementsBills.paid_by_email == user_email,
            DebtSettlementsBills.owed_by_email != user_email,
            DebtSettlementsBills.settled == 0
        ).scalar()

        # Total Money Borrowed: when the user is the debtor (owed_by_email == user_email)
        total_money_borrowed = db_session.query(
            func.coalesce(func.sum(DebtSettlementsBills.amount), 0)
        ).filter(
            DebtSettlementsBills.owed_by_email == user_email,
            DebtSettlementsBills.paid_by_email != user_email,
            DebtSettlementsBills.settled == 0
        ).scalar()
        # Round the totals to two decimal places
        total_money_owed = round(total_money_owed, 2)
        total_money_borrowed = round(total_money_borrowed, 2)
        # Money You Owe (group by the counterparty who lent you money)
        owed_breakdown = db_session.query(
            DebtSettlementsBills.paid_by_email,
            func.coalesce(func.sum(DebtSettlementsBills.amount), 0).label('total')
        ).filter(
            DebtSettlementsBills.owed_by_email == user_email,
            DebtSettlementsBills.paid_by_email != user_email,
            DebtSettlementsBills.settled == 0
        ).group_by(DebtSettlementsBills.paid_by_email).all()

        #  Money Owed To You (group by the counterparty who owes you money)
        borrowed_breakdown = db_session.query(
            DebtSettlementsBills.owed_by_email,
            func.coalesce(func.sum(DebtSettlementsBills.amount), 0).label('total')
        ).filter(
            DebtSettlementsBills.paid_by_email == user_email,
            DebtSettlementsBills.owed_by_email != user_email,
            DebtSettlementsBills.settled == 0
        ).group_by(DebtSettlementsBills.owed_by_email).all()

        #  build lists of dictionaries with the counterparty details
        owed_details = []
        for paid_by_email, total in owed_breakdown:
            user_obj = db_session.query(SplitInvoiceUser).filter_by(email=paid_by_email).first()
            if user_obj:
                name = f"{user_obj.name}"
            else:
                name = "Unknown"
            owed_details.append({'email': paid_by_email, 'name': name, 'amount': round(total, 2)})

        borrowed_details = []
        for owed_by_email, total in borrowed_breakdown:
            user_obj = db_session.query(SplitInvoiceUser).filter_by(email=owed_by_email).first()
            if user_obj:
                name = f"{user_obj.name}"
            else:
                name = "Unknown"
            borrowed_details.append({'email': owed_by_email, 'name': name, 'amount': round(total, 2)})

    return render_template(
        'balances.html',
        total_money_owed=total_money_owed,
        total_money_borrowed=total_money_borrowed,
        owed_details=owed_details,
        borrowed_details=borrowed_details
    )


@main_bp.route('/settle_debt', methods=['POST'])
@login_required
def settle_debt():
    try:
        data = request.get_json()
        paid_by = data.get('paid_by')
        owed_by = data.get('owed_by')
        amount_paid = data.get('amount_paid')

        with get_session() as db_session:
            # Find the unsettled debt
            settlement = db_session.query(DebtSettlements).filter_by(
                paid_by_id=paid_by, owed_by_id=owed_by, settled=False).first()

            if settlement:
                remaining_amount = settlement.amount - settlement.paid_amount

                if amount_paid > remaining_amount:
                    return jsonify({'error': 'Payment exceeds the remaining debt.'}), 400

                # Update the paid amount
                settlement.paid_amount += amount_paid

                # If the full debt is paid, mark as settled
                if settlement.paid_amount >= settlement.amount:
                    settlement.settled = True
                    settlement.paid_amount = settlement.amount  # Ensure paid_amount doesn't exceed amount

                db_session.commit()
                return jsonify({
                    'success': True,
                    'settled': settlement.settled,
                    'remaining_amount': settlement.amount - settlement.paid_amount
                }), 200

            else:
                return jsonify({'error': 'No outstanding debt found.'}), 400
    except Exception as e:
        logger.error(f"Error settling debt: {str(e)}")
        return jsonify({'error': 'An error occurred while settling debt.'}), 500


def sanitize_input(input_str):
    """
    Sanitizes input to ensure it does not contain invalid characters.
    """
    invalid_chars = r'<>:"/\|?*'
    return not any(char in invalid_chars for char in input_str)


def fetch_user_id_from_session():
    """
        Fetches the user ID from the session and validates it against the database.
        Returns None if the user ID is invalid or missing.
        """
    username = session.get('username')
    if not username:
        from flask import current_app
        current_app.logger.warning("No username found in session.")
        return None

    try:
        with get_session() as db_session:
            user = db_session.query(Users).filter_by(username=username).first()
            if user:
                logger.info(f"Fetched user ID {user.userid} for username {username}. User ID type: {type(user.userid)}")
                return user.userid
            else:
                logger.warning(f"No user found for username {username}.")
                return None
    except Exception as e:
        logger.error(f"Error fetching user ID: {str(e)}")
        return None


def create_dataframe(pdf_path, filename, month, year, shopname, userid):
    """
    Processes a PDF file, extracts data into a DataFrame, and associates it with a user ID.

    Args:
        pdf_path (str): Path to the input PDF file.
        filename (str): Name of the PDF file without extension.
        month (str): The month associated with the data.
        year (str):The year associated with the data.
        shopname (str): The name of the shop of purchased items
        userid (int): The user ID to associate with the extracted data.

    Returns:
        pd.DataFrame: Extracted data as a pandas DataFrame.
    """
    try:
        # Convert PDF to an image
        scanned_object = None
        if shopname == 'rewe':
            extracted_text = extract_text_from_pdf(pdf_path,filename)
            scanned_object = ImageScanner('', filename, extracted_text, month, year)
            text = scanned_object.get_text()
            if not text or len(text) < 10:
                logger.warning("Insufficient text detected. Attempting secondary processing.")
                scanned_object.get_groceries_bill()
                df = scanned_object.create_data_frame()
            else:
                #scanned_object.get_groceries_bill()
                df = scanned_object.create_data_frame()
        else:
            image_path = pdf_to_jpg(pdf_path, filename, current_app.config['IMAGE_FOLDER'])
            scanned_object = ImageScanner(image_path, filename, '', month, year)
            text = scanned_object.get_text()
            if not text or len(text) < 10:
                logger.warning("Insufficient text detected. Attempting secondary processing.")
                scanned_object.get_groceries_bill()
                df = scanned_object.create_data_frame()
            else:
                scanned_object.get_groceries_bill()
                df = scanned_object.create_data_frame()
        # Validate DataFrame
        if df.empty:
            logger.error("Extracted DataFrame is empty. No data found in the PDF.")
            raise ValueError("Failed to extract valid data from the PDF.")

        # Add the user ID to the DataFrame
        df['userid'] = userid
        pd.set_option("display.max_columns", None)

        # Log the result
        logger.info(f"DataFrame created successfully for user ID {userid}.")
        logger.debug(f"Extracted DataFrame:\n{df}")

        return df

    except Exception as e:
        logger.error(f"Error creating DataFrame from PDF: {str(e)}")
        raise


def fetch_data_by_date(userid, date):
    """
    Fetch data from the groceries table for a specific user and date.

    Args:
        userid (int): User ID to filter the data.
        date (str): date to filter the data.

    Returns:
        list: A list of rows from the groceries table.
    """
    try:

        groceries = models.get('groceries')
        if not groceries:
            logger.error("groceries model not initialized.")
            return []

        with get_session() as session:
            results = session.query(groceries).filter_by(userid=userid, date=date).all()
            return [row.__dict__ for row in results]

    except Exception as e:
        logger.error(f"Error fetching groceries data: {str(e)}")
        return []


def calculate_overall_debts_and_insert(db_session,current_user_id):
    """
    This function calculates the total debt for each user based on all unsettled transactions
    and inserts the debt data into the DebtSettlements table.

    :param db_session: The active database session.
    """
    try:
        # Fetch all unsettled settlements
        settlements = db_session.query(Settlements).filter_by(settled=False).all()

        # Create a dictionary to track the total amount owed by each user to another user
        debt_summary = {}

        # Iterate through each settlement record
        for settlement in settlements:
            paid_by = settlement.paid_by_email  # Who paid
            owed_by = settlement.owed_by_email  # Who owes

            amount = settlement.amount  # Amount owed

            # Add the debt to the summary (Paid by owes to Owed by)
            if paid_by not in debt_summary:
                debt_summary[paid_by] = {}

            if owed_by not in debt_summary[paid_by]:
                debt_summary[paid_by][owed_by] = 0.0

            # Add the amount owed to the owed_by user
            debt_summary[paid_by][owed_by] += amount

        # Insert the calculated debt summary into DebtSettlements table
        for paid_by_email, owed_users in debt_summary.items():
            for owed_by_email, total_amount in owed_users.items():
                # Insert the calculated debt into the DebtSettlements table
                new_debt = DebtSettlements(
                    paid_by_email=paid_by_email,  # User who paid
                    owed_by_email=owed_by_email,  # User who owes
                    amount=total_amount,  # Total amount owed
                    settled=False,
                    userid=current_user_id# Initially not settled
                )
                db_session.add(new_debt)

        # Commit the transaction to the database
        db_session.commit()
        logger.info(
            "Debt summary for all unsettled transactions successfully calculated and inserted into DebtSettlements.")

    except Exception as e:
        db_session.rollback()  # Rollback in case of error
        logger.error(f"Error calculating and inserting overall debts: {str(e)}")
        raise


def calculate_debts_basedON_billId(billid, db_session,current_user_id):
    """
    This function fetches the details from the Settlements table, calculates the debt summary,
    and inserts the debt data into the DebtSettlements table.

    :param billid: The Bill ID for which the debt needs to be calculated.
    :param db_session: The active database session.
    """
    try:
        # Fetch all the unsettled settlements for the given bill
        settlements = db_session.query(Settlements).filter_by(billId=billid, settled=False).all()

        # Create a dictionary to track the total amount owed by each user to another user
        debt_summary = {}

        # Iterate through each settlement record
        for settlement in settlements:
            paid_by = settlement.paid_by_email  # Who paid
            owed_by = settlement.owed_by_email  # Who owes

            amount = settlement.amount  # Amount owed

            # Add the debt to the summary (Paid by owes to Owed by)
            if paid_by not in debt_summary:
                debt_summary[paid_by] = {}

            if owed_by not in debt_summary[paid_by]:
                debt_summary[paid_by][owed_by] = 0.0

            # Add the amount owed to the owed_by user
            debt_summary[paid_by][owed_by] += amount

        # Insert the calculated debt summary into DebtSettlements table
        for paid_by_email, owed_users in debt_summary.items():
            for owed_by_email, total_amount in owed_users.items():
                # Insert the calculated debt into the DebtSettlements table
                new_debt = DebtSettlementsBills(
                    billId=billid,
                    paid_by_email=paid_by_email,  # User who paid
                    owed_by_email=owed_by_email,  # User who owes
                    amount=total_amount,  # Total amount owed
                    settled=False,
                    created_by= current_user_id# Initially not settled
                )
                db_session.add(new_debt)

        # Commit the transaction to the database
        db_session.commit()
        logger.info(f"Debt summary for Bill ID {billid} successfully calculated and inserted into DebtSettlements.")

    except Exception as e:
        db_session.rollback()  # Rollback in case of error
        logger.error(f"Error calculating and inserting debts for Bill ID {billid}: {str(e)}")
        raise





def fetch_debt_settlement_details(billid):
    """
    Fetches debt settlement details (amount, paid_by, owed_by) for a specific bill ID
    and retrieves the user names from SplitInvoiceUser based on email.
    """
    try:
        with get_session() as db_session:
            logger.info(f"Fetching debt settlements for Bill ID: {billid}")

            # Define aliases for SplitInvoiceUser
            PaidByUser = aliased(SplitInvoiceUser)
            OwedByUser = aliased(SplitInvoiceUser)

            # Query DebtSettlementsBills for the specified Bill ID and join with SplitInvoiceUser using emails
            results = db_session.query(
                DebtSettlementsBills.billId,
                DebtSettlementsBills.amount,
                PaidByUser.name.label('paid_by_name'),
                OwedByUser.name.label('owed_by_name')
            ).join(
                PaidByUser, PaidByUser.email == DebtSettlementsBills.paid_by_email, isouter=True
            ).join(
                OwedByUser, OwedByUser.email == DebtSettlementsBills.owed_by_email, isouter=True
            ).filter(DebtSettlementsBills.billId == billid).all()

            if not results:
                logger.info(f"No debt settlement records found for Bill ID: {billid}")
            logger.info(f"results: {results}")
            return results
    except Exception as e:
        logger.error(f"Error fetching debt settlement details for Bill ID {billid}: {str(e)}")
        return []

def update_debt_summary(db_session):
    """
    Update the DebtSummary table with the latest totals from DebtSettlementsBills.
    """
    try:
        # Calculate totals for all user pairs
        totals = db_session.query(
            DebtSettlementsBills.paid_by_email,
            DebtSettlementsBills.owed_by_email,
            func.sum(DebtSettlementsBills.amount).label('total_amount')
        ).filter(
            DebtSettlementsBills.settled == 0
        ).group_by(
            DebtSettlementsBills.paid_by_email,
            DebtSettlementsBills.owed_by_email
        ).all()

        # Update DebtSummary table
        for paid_by_email, owed_by_email, total_amount in totals:
            # Insert or update the DebtSummary table
            debt_summary = db_session.query(DebtSummary).filter_by(
                paid_by_email=paid_by_email,
                owed_by_email=owed_by_email
            ).first()

            if debt_summary:
                # Update existing record
                debt_summary.total_amount = total_amount
                debt_summary.last_updated = datetime.now()
            else:
                # Insert new record
                new_summary = DebtSummary(
                    paid_by_email=paid_by_email,
                    owed_by_email=owed_by_email,
                    total_amount=total_amount,
                    last_updated=datetime.now()
                )
                db_session.add(new_summary)

        db_session.commit()
        logger.info("DebtSummary table updated successfully.")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating DebtSummary table: {str(e)}")
        raise