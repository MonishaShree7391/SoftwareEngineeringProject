from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from sqlalchemy.orm import aliased
from datetime import datetime, timezone
from decimal import Decimal
from extensions import db, Base
import logging
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
logger = logging.getLogger(__name__)
debt_bp = Blueprint('debt', __name__)

# Reflect tables dynamically
#DebtSummary = Base.classes.get("DebtSummary")
#DebtSettlements = Base.classes.get("DebtSettlements")
#DebtSettlementsBills = Base.classes.get("DebtSettlementBills")
#SettlementLog = Base.classes.get("SettlementLog")
#Settlements = Base.classes.get("settlements")
#SplitInvoiceUser = Base.classes.get("users")


@debt_bp.route('/balances', methods=['GET'])
@jwt_required()
def view_balances():
    print("\nInside BALANCES\n")
    user = get_jwt_identity()
    claims = get_jwt()
    email = claims.get("username")

    try:
        Users = Base.classes['users']
        SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
        Settlements = Base.classes['settlements']
        DebtSettlementsBills = Base.classes['DebtSettlementsBills']
        DebtSummary = Base.classes['DebtSummary']
        SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
    except Exception as e:
        logger.error(f"Table reflection failed: {e}")
        return jsonify({'error': 'Failed to load database tables.'}), 500

    try:
        session = db.session

        # Update summary first
        try:
            update_debt_summary(session)
        except Exception as e:
            logger.error(f"Failed to update debt summary: {e}")

        total_money_owed = session.query(func.coalesce(func.sum(DebtSummary.total_amount), 0)).filter(
            DebtSummary.paid_by_email == email,
            DebtSummary.owed_by_email != email,
            DebtSummary.settled == False
        ).scalar()

        total_money_borrowed = session.query(func.coalesce(func.sum(DebtSummary.total_amount), 0)).filter(
            DebtSummary.owed_by_email == email,
            DebtSummary.paid_by_email != email,
            DebtSummary.settled == False
        ).scalar()

        owed_breakdown = session.query(
            DebtSummary.paid_by_email,
            func.sum(DebtSummary.total_amount).label('total')
        ).filter(
            DebtSummary.owed_by_email == email,
            DebtSummary.paid_by_email != email,
            DebtSummary.settled == False
        ).group_by(DebtSummary.paid_by_email).all()

        borrowed_breakdown = session.query(
            DebtSummary.owed_by_email,
            func.sum(DebtSummary.total_amount).label('total')
        ).filter(
            DebtSummary.paid_by_email == email,
            DebtSummary.owed_by_email != email,
            DebtSummary.settled == False
        ).group_by(DebtSummary.owed_by_email).all()

        owed_details = []
        for paid_by_email, total in owed_breakdown:
            user = session.query(SplitInvoiceUser).filter_by(email=paid_by_email).first()
            owed_details.append({
                'email': paid_by_email,
                'name': user.name if user else 'Unknown',
                'amount': round(total, 2)
            })

        borrowed_details = []
        for owed_by_email, total in borrowed_breakdown:
            user = session.query(SplitInvoiceUser).filter_by(email=owed_by_email).first()
            borrowed_details.append({
                'email': owed_by_email,
                'name': user.name if user else 'Unknown',
                'amount': round(total, 2)
            })

        return jsonify({
            'total_money_owed': round(total_money_owed, 2),
            'total_money_borrowed': round(total_money_borrowed, 2),
            'owed_details': owed_details,
            'borrowed_details': borrowed_details
        })

    except Exception as e:
        logger.error(f"Error fetching balances: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@debt_bp.route('/settle_debt', methods=['POST'])
@jwt_required()
def settle_debt():
    print("\nInside SETTLE DEBT\n")
    data = request.get_json()
    paid_by = data.get('paid_by')
    owed_by = data.get('owed_by')
    amount_paid = data.get('amount_paid')
    full = data.get('full_settlement')
    method = data.get('method')
    note = data.get('note')
    Users = Base.classes['users']
    SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
    Settlements = Base.classes['settlements']
    DebtSettlementsBills = Base.classes['DebtSettlementsBills']
    DebtSummary = Base.classes['DebtSummary']
    SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
    SettlementLog = Base.classes['SettlementLog']
    Settlements = Base.classes['settlements']
    if not paid_by or not owed_by:
        return jsonify({'error': 'Missing required fields'}), 400

    if amount_paid is not None:
        try:
            amount_paid = Decimal(str(amount_paid))
            if amount_paid <= 0:
                return jsonify({'error': 'Invalid amount'}), 400
        except:
            return jsonify({'error': 'Amount must be a valid number'}), 400

    print("paid_by and owed_by",paid_by,"owed_by",owed_by)
    existing = db.session.query(DebtSummary).all()
    for s in existing:
        print(f"DEBUG: Debt {s.paid_by_email} => {s.owed_by_email}, Amount: {s.total_amount}, Settled: {s.settled}")

    full = bool(full) if full is not None else False
    session = db.session
    try:
        settlement = session.query(DebtSummary).filter_by(
            paid_by_email=paid_by,
            owed_by_email=owed_by,
            settled=False
        ).first()

        if not settlement:
            return jsonify({'error': 'No outstanding debt found.'}), 404

        remaining = settlement.total_amount
        actual_payment = remaining if full or amount_paid is None else amount_paid

        if not full and actual_payment > remaining:
            return jsonify({'error': 'Payment exceeds remaining debt.'}), 400

        settlement.settled_amount += actual_payment
        settlement.total_amount -= actual_payment
        settlement.total_amount = max(settlement.total_amount, Decimal("0.00"))

        if settlement.total_amount == 0:
            settlement.settled = True
            settlement.last_settled_on = datetime.now(timezone.utc)
        else:
            settlement.num_partial_settlements = (settlement.num_partial_settlements or 0) + 1

        log_entry = SettlementLog(
            paid_by_email=paid_by,
            owed_by_email=owed_by,
            amount_paid=actual_payment,
            method=method,
            note=note,
            timestamp=datetime.now(timezone.utc)
        )
        session.add(log_entry)

        mark_related_debts_as_settled(session, paid_by, owed_by)
        session.commit()
        return jsonify({'success': True})

    except Exception as e:
        session.rollback()
        logger.error(f"Settle debt error: {e}")
        return jsonify({'error': 'Database error during commit.'}), 500


def update_debt_summary(session):
    try:
        #DebtSettlementsBills = Base.classes.DebtSettlementsBills
        #DebtSummary = Base.classes.DebtSummary
        #SplitInvoiceUser = Base.classes.SplitInvoiceUsers
        Users = Base.classes['users']
        SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
        Settlements = Base.classes['settlements']
        DebtSettlementsBills = Base.classes['DebtSettlementsBills']
        DebtSummary = Base.classes['DebtSummary']
        SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
        SettlementLog = Base.classes['SettlementLog']
        Settlements = Base.classes['settlements']
    except Exception as e:
        print("Failed to refelct tables: ",e)
        raise
    try:
        totals = session.query(
            DebtSettlementsBills.paid_by_email,
            DebtSettlementsBills.owed_by_email,
            func.sum(DebtSettlementsBills.amount).label('total_amount')
        ).filter(
            DebtSettlementsBills.settled == False
        ).group_by(
            DebtSettlementsBills.paid_by_email,
            DebtSettlementsBills.owed_by_email
        ).all()

        for paid_by_email, owed_by_email, total_amount in totals:
            debt_summary = session.query(DebtSummary).filter_by(
                paid_by_email=paid_by_email,
                owed_by_email=owed_by_email
            ).first()

            if debt_summary:
                previous_total = debt_summary.total_amount or 0
                previous_original = debt_summary.original_amount or 0

                debt_summary.total_amount = total_amount
                if total_amount > previous_total:
                    debt_summary.original_amount = float(previous_original) + (float(total_amount) - float(previous_total))
                if debt_summary.settled:
                    debt_summary.settled = False

                debt_summary.last_updated = datetime.utcnow()
            else:
                new_summary = DebtSummary(
                    paid_by_email=paid_by_email,
                    owed_by_email=owed_by_email,
                    total_amount=total_amount,
                    original_amount=total_amount,
                    settled_amount=0,
                    settled=False,
                    last_updated=datetime.utcnow()
                )
                session.add(new_summary)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating DebtSummary: {str(e)}")
        raise


def mark_related_debts_as_settled(session, paid_by, owed_by):
    print("\n :: INSIDE mark_related_debts_as_settled :: ")
    #DebtSettlementsBills = Base.classes.DebtSettlementsBills
    #DebtSettlements = Base.classes.DebtSettlements
    #Users = Base.classes['users']
    #SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
    #Settlements = Base.classes['settlements']
    DebtSettlementsBills = Base.classes['DebtSettlementsBills']
    DebtSettlements = Base.classes['DebtSettlements']
    #DebtSummary = Base.classes['DebtSummary']
    #SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
    #SettlementLog = Base.classes['SettlementLog']
    Settlements = Base.classes['settlements']

    session.query(DebtSettlementsBills).filter_by(
        paid_by_email=paid_by,
        owed_by_email=owed_by,
        settled=False
    ).update({"settled": True}, synchronize_session='fetch')

    session.query(DebtSettlements).filter_by(
        paid_by_email=paid_by,
        owed_by_email=owed_by,
        settled=False
    ).update({"settled": True}, synchronize_session='fetch')

    session.query(Settlements).filter_by(
        paid_by_email=paid_by,
        owed_by_email=owed_by,
        settled=False
    ).update({"settled": True}, synchronize_session='fetch')

@debt_bp.route('/calculate_from_bill/<path:bill_id>', methods=['POST'])
@jwt_required()
def trigger_calculate_debts_based_on_bill(bill_id):
    user_id = get_jwt_identity()
    session = db.session
    try:
        calculate_debts_basedON_billId(bill_id, session, current_user_id=user_id)
        return jsonify({"message": f"Debts calculated for bill {bill_id}"}), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Error in trigger_calculate_debts_based_on_bill: {e}")
        return jsonify({"error": "Failed to calculate debts for bill"}), 500


@debt_bp.route('/calculate_overall', methods=['POST'])
@jwt_required()
def trigger_calculate_overall_debts():
    user_id = get_jwt_identity()
    session = db.session
    try:
        calculate_overall_debts_and_insert(session, current_user_id=user_id)
        return jsonify({"message": "Overall debts calculated"}), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Error in trigger_calculate_overall_debts: {e}")
        return jsonify({"error": "Failed to calculate overall debts"}), 500

def calculate_debts_basedON_billId(billid, db_session, current_user_id):
    print("\nInside calculate_debts_basedON_billId implementation\n")
    print("Session object type:", type(db.session))
    # Users = Base.classes['users']
    # SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
    # Settlements = Base.classes['settlements']
    DebtSettlementsBills = Base.classes['DebtSettlementsBills']
    DebtSettlements = Base.classes['DebtSettlements']
    # DebtSummary = Base.classes['DebtSummary']
    # SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
    # SettlementLog = Base.classes['SettlementLog']
    Settlements = Base.classes['settlements']
    try:
        settlements = db_session.query(Settlements).filter_by(
            billId=billid,
            settled=False,
            userid=current_user_id
        ).all()
        if settlements:
            print("++++Settlements data available")

        debt_summary = {}

        for settlement in settlements:
            paid_by = settlement.paid_by_email
            owed_by = settlement.owed_by_email
            amount = settlement.amount

            if paid_by not in debt_summary:
                debt_summary[paid_by] = {}

            if owed_by not in debt_summary[paid_by]:
                debt_summary[paid_by][owed_by] = 0.0

            debt_summary[paid_by][owed_by] += amount
        if debt_summary:
            print("+++debt_summary details preapred to add in db: ",debt_summary)

        #DebtSettlementsBills = Base.classes.DebtSettlementsBills
        #print("DebtSettlementsBills class:", DebtSettlementsBills)
        #assert DebtSettlementsBills is not None, " DebtSettlementsBills model not reflected!"

        for paid_by_email, owed_users in debt_summary.items():
            for owed_by_email, total_amount in owed_users.items():
                new_debt = DebtSettlementsBills(
                    billId=billid,
                    paid_by_email=paid_by_email,
                    owed_by_email=owed_by_email,
                    amount=total_amount,
                    settled=False,
                    created_by=current_user_id
                )
                db_session.add(new_debt)
                print("\n new_debt")
                print(new_debt)
        try:
            db_session.commit()
        except Exception as e:
            print("db_session.commit() failed",e)
        logger.info(f"Debt summary for Bill ID {billid} successfully calculated.")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error calculating debts for Bill ID {billid}: {str(e)}")
        raise


def calculate_overall_debts_and_insert(db_session, current_user_id):
    try:
        # Users = Base.classes['users']
        # SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
        # Settlements = Base.classes['settlements']
        DebtSettlementsBills = Base.classes['DebtSettlementsBills']
        DebtSettlements = Base.classes['DebtSettlements']
        # DebtSummary = Base.classes['DebtSummary']
        # SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
        # SettlementLog = Base.classes['SettlementLog']
        Settlements = Base.classes['settlements']
        settlements = db_session.query(Settlements).filter_by(settled=False).all()
        debt_summary = {}

        for settlement in settlements:
            paid_by = settlement.paid_by_email
            owed_by = settlement.owed_by_email
            amount = settlement.amount

            if paid_by not in debt_summary:
                debt_summary[paid_by] = {}

            if owed_by not in debt_summary[paid_by]:
                debt_summary[paid_by][owed_by] = 0.0

            debt_summary[paid_by][owed_by] += amount

        for paid_by_email, owed_users in debt_summary.items():
            for owed_by_email, total_amount in owed_users.items():
                new_debt = DebtSettlements(
                    paid_by_email=paid_by_email,
                    owed_by_email=owed_by_email,
                    amount=total_amount,
                    settled=False,
                    userid=current_user_id
                )
                db_session.add(new_debt)

        db_session.commit()
        logger.info("Overall debt summary calculated.")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error calculating overall debts: {str(e)}")
        raise

@debt_bp.route('/settlements/<path:bill_id>', methods=['GET'])
@jwt_required()
def fetch_debt_settlement_details(bill_id):
    try:
        session = db.session
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400


        # Get models
        #DebtSettlementsBills = Base.classes.DebtSettlementsBills
        #DebtSettlementsBills = Base.classes.get("DebtSettlementBills")
        #SplitInvoiceUser = Base.classes.SplitInvoiceUsers
        #SplitInvoiceUser =  Base.classes.get("SplitInvoiceUsers")  # depends on your reflection
        #assert DebtSettlementsBills is not None, "DebtSettlementBills not reflected"
        #assert SplitInvoiceUser is not None, "SplitInvoiceUser not reflected"
        # Users = Base.classes['users']
        # SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
        # Settlements = Base.classes['settlements']
        DebtSettlementsBills = Base.classes['DebtSettlementsBills']
        DebtSettlements = Base.classes['DebtSettlements']
        # DebtSummary = Base.classes['DebtSummary']
        SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
        # SettlementLog = Base.classes['SettlementLog']
        # Settlements = Base.classes['settlements']

        # Aliases for joining on names
        PaidByUser = aliased(SplitInvoiceUser)
        OwedByUser = aliased(SplitInvoiceUser)

        results = session.query(
            DebtSettlementsBills.billId,
            DebtSettlementsBills.amount,
            DebtSettlementsBills.paid_by_email,
            DebtSettlementsBills.owed_by_email,
            PaidByUser.name.label("paid_by_name"),
            OwedByUser.name.label("owed_by_name")
        ).join(
            PaidByUser, PaidByUser.email == DebtSettlementsBills.paid_by_email, isouter=True
        ).join(
            OwedByUser, OwedByUser.email == DebtSettlementsBills.owed_by_email, isouter=True
        ).filter(
            DebtSettlementsBills.billId == bill_id,
            DebtSettlementsBills.created_by == int(user_id)
        ).all()

        response = [
            {
                "bill_id": r.billId,
                "amount": float(r.amount),
                "paid_by": r.paid_by_email,
                "owed_by": r.owed_by_email,
                "paid_by_name": r.paid_by_name,
                "owed_by_name": r.owed_by_name
            }
            for r in results
        ]

        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching debt settlements for bill {bill_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@debt_bp.route('/settlement_log', methods=['GET'])
@jwt_required()
def get_settlement_history():
    try:
        #user_data = get_jwt_identity()
        #user_email = user_data.get('username')

        user = get_jwt_identity()
        claims = get_jwt()
        user_id = get_jwt_identity()

        # Access other attributes from the 'claims' dictionary
        user_email = claims.get("username")
        # firstname = claims.get("firstname")
        # lastname = claims.get("lastname")
        is_admin = claims.get("is_admin")
        # name = f"{firstname} {lastname}"
        # Example: Log the user details
        # data = request.get_json()
        # email = data.get("email")
        # name = data.get("name")
        # email = user.get("username")

        # Users = Base.classes['users']
        # SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
        # Settlements = Base.classes['settlements']
        DebtSettlementsBills = Base.classes['DebtSettlementsBills']
        DebtSettlements = Base.classes['DebtSettlements']
        # DebtSummary = Base.classes['DebtSummary']
        SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
        SettlementLog = Base.classes['SettlementLog']
        # Settlements = Base.classes['settlements']

        session = db.session
        history = session.query(SettlementLog).filter(
            (SettlementLog.paid_by_email == user_email) |
            (SettlementLog.owed_by_email == user_email)
        ).order_by(SettlementLog.timestamp.desc()).all()

        results = []
        for entry in history:
            results.append({
                "id": entry.id,
                "paid_by": entry.paid_by_email,
                "owed_by": entry.owed_by_email,
                "amount": float(entry.amount_paid),
                "method": entry.method,
                "note": entry.note,
                "timestamp": entry.timestamp.isoformat()
            })

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error fetching settlement history: {e}")
        return jsonify({"error": "Internal server error"}), 500
