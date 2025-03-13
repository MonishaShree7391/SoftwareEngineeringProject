from flask_login import UserMixin
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import Column, Integer, String,ForeignKey ,Float, Boolean
from app.services.DatabaseConnection import db, Base
from flask import current_app
from sqlalchemy.orm import Session, relationship
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
# Explicit Model for Users
class Users(UserMixin, db.Model):
    __tablename__ = 'USERDATA'
    userid = Column(Integer, primary_key=True, autoincrement=True)
    firstname = Column(String(30), nullable=False)
    lastname = Column(String(30), nullable=False)
    username = Column(String(250), unique=True, nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)  # Renamed column

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute.")

    @password.setter
    def password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


    def get_userdetails(self):
        return self.username, self.firstname, self.lastname

    def get_userid(self):
        return self.userid

    def get_id(self):
        """
        Override the default `get_id` method to return `userid`.
        """
        return str(self.userid)

    # Model for SplitInvoiceUser
class SplitInvoiceUser(db.Model):
        __tablename__ = 'SplitInvoiceUsers'
        id = Column(Integer, primary_key=True, autoincrement=True)
        email = Column(String(100), unique=True, nullable=False)
        name = Column(String(100), nullable=False)
        userid = Column(Integer, ForeignKey('USERDATA.userid'),
                        nullable=False)  # Link to the user who added this person


class SplitInvoiceDetail(db.Model):
    __tablename__ = 'SplitInvoiceDetail'
    id = Column(Integer, primary_key=True, autoincrement=True)
    billId = Column(String(100), nullable=False)  # Link to the bill
    item = Column(String(100), nullable=False)  # Item name
    shared_with = Column(String(100), nullable=False)  # Comma-separated list of emails
    userid = Column(Integer, ForeignKey('USERDATA.userid'), nullable=False)  # Link to the user
    amount = Column(Float)


class Settlements(db.Model):
    __tablename__ = 'settlements'
    id = Column(Integer, primary_key=True)
    billId = Column(String(100), nullable=False)
    paid_by = Column(Integer,nullable=False)  # Can be any user, not just the logged-in user
    owed_by = Column(Integer,nullable=False)
    paid_by_email=Column(String(100), nullable=False)
    owed_by_email = Column(String(100), nullable=False)
    amount = Column(Float)
    settled = Column(Boolean, default=False)
    userid = Column(Integer, ForeignKey('USERDATA.userid'), nullable=False)  # Link to the user
    # Relationships to the SplitInvoiceUser table
    # Relationships to SplitInvoiceUsers

class DebtSettlements(db.Model):
    __tablename__ = 'DebtSettlements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    paid_by_email = Column(String(100), ForeignKey('SplitInvoiceUsers.email'), nullable=False)  # New column for email reference
    owed_by_email = Column(String(100), ForeignKey('SplitInvoiceUsers.email'), nullable=False)  # New column for email reference
    amount = Column(Float, nullable=False)  # Amount owed
    settled = Column(Boolean, default=False)  # Whether the debt is settled (default: False)
    userid = Column(Integer, ForeignKey('USERDATA.userid'), nullable=False)  # Link to the user

    # Relationships
    paid_by = relationship('SplitInvoiceUser', foreign_keys=[paid_by_email], primaryjoin="DebtSettlements.paid_by_email == SplitInvoiceUser.email")
    owed_by = relationship('SplitInvoiceUser', foreign_keys=[owed_by_email], primaryjoin="DebtSettlements.owed_by_email == SplitInvoiceUser.email")

    def __repr__(self):
        return f"<DebtSettlements(paid_by={self.paid_by_email}, owed_by={self.owed_by_email}, amount={self.amount}, settled={self.settled})>"

class DebtSettlementsBills(db.Model):
    __tablename__ = 'DebtSettlementsBills'

    id = Column(Integer, primary_key=True, autoincrement=True)
    billId = Column(String(100), nullable=False)  # Link to the bill
    paid_by_email = Column(String(100), ForeignKey('SplitInvoiceUsers.email'), nullable=False)  # New column for email reference
    owed_by_email = Column(String(100), ForeignKey('SplitInvoiceUsers.email'), nullable=False)  # New column for email reference
    amount = Column(Float, nullable=False)  # Amount owed
    settled = Column(Boolean, default=False)  # Whether the debt is settled (default: False)
    created_by = Column(Integer, ForeignKey('USERDATA.userid'), nullable=False)  # Link to the user

    # Relationships
    paid_by = relationship('SplitInvoiceUser', foreign_keys=[paid_by_email], primaryjoin="DebtSettlementsBills.paid_by_email == SplitInvoiceUser.email")
    owed_by = relationship('SplitInvoiceUser', foreign_keys=[owed_by_email], primaryjoin="DebtSettlementsBills.owed_by_email == SplitInvoiceUser.email")

    def __repr__(self):
        return f"<DebtSettlementsBills(bill_id={self.billId}, paid_by={self.paid_by_email}, owed_by={self.owed_by_email}, amount={self.amount}, settled={self.settled})>"

# Automap Base for dynamic models
Base = automap_base()
models = {}  # Shared container for dynamically reflected models

def init_models():
    """
    Initializes models by reflecting the database schema.
    Must be called within the app context.
    """
    try:
        engine = current_app.engine  # Access the engine from the app context
        Base.prepare(engine, reflect=True)  # Reflect database schema

        current_app.logger.info(f"Tables reflected: {list(Base.classes.keys())}")
        #models["User"] = Base.classes.get("USERDATA")  # Reflect USER_DATA table dynamically
        models["groceries"] = Base.classes.get("groceries")  # Reflect groceries table dynamically

        #if not models["User"]:
         #   raise Exception("USER_DATA table not found in the database schema.")
        #else:
         #   models["User"].__table__.columns.keys()
        if models["groceries"]:
            current_app.logger.info(f"groceries table columns: {[col.name for col in models['groceries'].__table__.columns]}")
        else:
            raise Exception("groceries table not found in the database schema.")
    except Exception as e:
        print(f"Error during model initialization: {str(e)}")
def get_session():
    """
    Creates and returns a new SQLAlchemy session using the app's engine.
    Must be called within the app context.
    """
    try:
        engine = current_app.engine
        return Session(engine)
    except Exception as e:
        print(f"Error creating database session: {str(e)}")
        raise