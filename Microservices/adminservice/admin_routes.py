from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import aliased

from extensions import db, Base
from sqlalchemy import func
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


#Users = Base.classes['users']
#DebtSettlements = Base.classes['DebtSettlements']

@admin_bp.route("/users/promote/<int:user_id>", methods=["POST"])
@jwt_required()
def promote_user(user_id):
    Users = Base.classes['users']
    DebtSettlements = Base.classes['DebtSettlements']
    session = db.session
    user = session.query(Users).get(user_id)
    if user and not user.is_admin:
        user.is_admin = True
        session.commit()
        return jsonify({"success": True, "message": "User promoted to admin."})
    return jsonify({"error": "User not found or already an admin."}), 400

@admin_bp.route("/users/demote/<int:user_id>", methods=["POST"])
@jwt_required()
def demote_user(user_id):
    Users = Base.classes['users']
    DebtSettlements = Base.classes['DebtSettlements']
    session = db.session
    user = session.query(Users).get(user_id)
    if user and user.is_admin:
        user.is_admin = False
        session.commit()
        return jsonify({"success": True, "message": "Admin demoted to user."})
    return jsonify({"error": "User not found or not an admin."}), 400

@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@jwt_required()
def delete_user(user_id):
    Users = Base.classes['users']
    DebtSettlements = Base.classes['DebtSettlements']
    requester_id = get_jwt_identity()
    session = db.session
    user = session.query(Users).get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.id == requester_id:
        return jsonify({"error": "Admins cannot delete themselves."}), 403

    if user.is_admin:
        admin_count = session.query(Users).filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify({"error": "At least one admin must remain."}), 403

    session.delete(user)
    session.commit()
    return jsonify({"success": True, "message": "User deleted successfully."})

@admin_bp.route("/settlements/complete/<int:settlement_id>", methods=["POST"])
@jwt_required()
def mark_settlement_complete(settlement_id):
    print("\n INSIDE mark_settlement_complete")
    Users = Base.classes['users']
    DebtSummary = Base.classes['DebtSummary']
    session = db.session
    settlement = session.query(DebtSummary).get(settlement_id)
    if settlement and not settlement.settled:
        settlement.settled = True
        session.commit()
        return jsonify({"success": True, "message": "Settlement marked as complete."})
    return jsonify({"error": "Settlement not found or already completed."}), 400

@admin_bp.route("/settlements/delete/<int:settlement_id>", methods=["POST"])
@jwt_required()
def delete_settlement(settlement_id):
    Users = Base.classes['users']
    DebtSummary = Base.classes['DebtSummary']
    session = db.session
    settlement = session.query(DebtSummary).get(settlement_id)
    if settlement:
        session.delete(settlement)
        session.commit()
        return jsonify({"success": True, "message": "Settlement deleted successfully."})
    return jsonify({"error": "Settlement not found."}), 404

@admin_bp.route("/total_users", methods=["GET"])
@jwt_required()
def total_users():
    session = db.session
    Users = Base.classes['users']
    count = session.query(func.count()).select_from(Users).scalar()
    return jsonify({"count": count})

@admin_bp.route("/total_invoices", methods=["GET"])
@jwt_required()
def total_invoices():
    session = db.session
    groceries = Base.classes['groceries']
    count = session.query(func.count(func.distinct(groceries.billId))).scalar()
    return jsonify({"count": count})

@admin_bp.route("/total_splits", methods=["GET"])
@jwt_required()
def total_splits():
    session = db.session
    SplitInvoiceDetail = Base.classes['SplitInvoiceDetail']
    count = session.query(func.count()).select_from(SplitInvoiceDetail).scalar()
    return jsonify({"count": count})

@admin_bp.route("/total_settled", methods=["GET"])
@jwt_required()
def total_settled():
    session = db.session
    DebtSettlements = Base.classes['DebtSettlements']
    total = session.query(func.coalesce(func.sum(DebtSettlements.amount), 0)).filter_by(settled=True).scalar()
    return jsonify({"total": round(float(total), 2)})

@admin_bp.route("api/settlements", methods=["GET"])
@jwt_required()
def settlements():
    print("\nInside ADMIN settlements\n")
    DebtSummary = Base.classes['DebtSummary']
    SplitInvoiceUser = Base.classes['SplitInvoiceUsers']
    session = db.session

    PaidBy = aliased(SplitInvoiceUser)
    OwedBy = aliased(SplitInvoiceUser)

    results = session.query(
        DebtSummary,
        PaidBy.name.label("paid_by_name"),
        OwedBy.name.label("owed_by_name")
    ).join(
        PaidBy, DebtSummary.paid_by_email == PaidBy.email
    ).join(
        OwedBy, DebtSummary.owed_by_email == OwedBy.email
    ).all()

    response = [
        {
            "id": r.DebtSummary.id,  #   Add this
            "paid_by": r.paid_by_name,
            "owed_by": r.owed_by_name,
            "total_amount": float(r.DebtSummary.original_amount or 0),
            "settled_amount": float(r.DebtSummary.settled_amount or 0),
            "settled": r.DebtSummary.settled  #   Also needed for status check
        }
        for r in results
    ]

    return jsonify(response)
