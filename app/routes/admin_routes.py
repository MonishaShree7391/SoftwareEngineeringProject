from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
from app.models.models import Users, DebtSettlements, db, DebtSummary
from app.utils.decorators import admin_required
from app.logs.admin_logs import log_admin_action

admin_bp = Blueprint("admin", __name__)

from sqlalchemy.orm import aliased
from app.models.models import DebtSummary, SplitInvoiceUser

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    # Get all regular users and settlements as before
    users = Users.query.all()
    settlements = DebtSettlements.query.all()

    # Create aliases for SplitInvoiceUser to join twice:
    PaidByUser = aliased(SplitInvoiceUser)
    OwedByUser = aliased(SplitInvoiceUser)

    # Query DebtSummary and join to get the names for paid_by and owed_by.
    # This assumes that SplitInvoiceUser.name contains the desired "firstname_lastname" string.
    debt_summary_data = db.session.query(
        DebtSummary,
        PaidByUser.name.label("paid_by_name"),
        OwedByUser.name.label("owed_by_name")
    ).join(PaidByUser, DebtSummary.paid_by_email == PaidByUser.email
    ).join(OwedByUser, DebtSummary.owed_by_email == OwedByUser.email
    ).all()

    return render_template(
        "admin_dashboard.html",
        users=users,
        settlements=settlements,
        debt_summary=debt_summary_data
    )



@admin_bp.route("/settlements")
@login_required
@admin_required
def settlements():
    settlements = DebtSummary.query.all()
    return render_template("admin_settlements.html", settlements=settlements)

@admin_bp.route("/users/promote/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def promote_user(user_id):
    user = Users.query.get(user_id)
    if user and not user.is_admin:
        user.is_admin = True
        db.session.commit()
        log_admin_action(current_user, "PROMOTE", user.username)
        return jsonify({"success": True, "message": "User promoted to admin."})
    return jsonify({"error": "User not found or already an admin."}), 400

@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Admin can delete users, but not themselves & must keep at least one admin."""
    user = Users.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # 🚨 Prevent Admin from Deleting Themselves
    if user.userid == current_user.userid:
        return jsonify({"error": "Admins cannot delete themselves."}), 403

    # 🚨 Ensure at least One Admin Exists
    if user.is_admin:
        admin_count = Users.query.filter_by(is_admin=True).count()
        if admin_count == 1:
            return jsonify({"error": "At least one admin must remain."}), 403

    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": "User deleted successfully."})

@admin_bp.route("/users/demote/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def demote_user(user_id):
    """Demote an admin back to a regular user"""
    user = Users.query.get(user_id)
    if user and user.is_admin:
        user.is_admin = False
        db.session.commit()
        return jsonify({"success": True, "message": "Admin demoted to user."})
    return jsonify({"error": "User not found or not an admin."}), 400

@admin_bp.route("/settlements/complete/<int:settlement_id>", methods=["POST"])
@login_required
@admin_required
def mark_settlement_complete(settlement_id):
    """Mark a settlement as complete"""
    settlement = DebtSettlements.query.get(settlement_id)
    if settlement and not settlement.settled:
        settlement.settled = True
        db.session.commit()
        return jsonify({"success": True, "message": "Settlement marked as complete."})
    return jsonify({"error": "Settlement not found or already completed."}), 400

@admin_bp.route("/settlements/delete/<int:settlement_id>", methods=["POST"])
@login_required
@admin_required
def delete_settlement(settlement_id):
    """Delete a settlement"""
    settlement = DebtSettlements.query.get(settlement_id)
    if settlement:
        db.session.delete(settlement)
        db.session.commit()
        return jsonify({"success": True, "message": "Settlement deleted successfully."})
    return jsonify({"error": "Settlement not found."}), 404
