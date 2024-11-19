from datetime import datetime
from extensions import db  # Import db from extensions.py

# User model
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    organizations = db.relationship('Organization', back_populates='user', lazy=True)
    donations = db.relationship('Donation', secondary='donor_donations', lazy='subquery', back_populates='donors')

# Organization model
class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    donations = db.relationship('Donation', back_populates='organization', lazy=True)
    beneficiaries = db.relationship('Beneficiary', back_populates='organization', lazy=True)

    # Back reference for User
    user = db.relationship('User', back_populates='organizations')

    __table_args__ = {'extend_existing': True}

# Donation model
class Donation(db.Model):
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20))
    payment_method = db.Column(db.String(50))
    is_anonymous = db.Column(db.Boolean, default=False)
    next_payment_date = db.Column(db.DateTime)

    # Foreign key to Organization
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    organization = db.relationship('Organization', back_populates='donations')
    donors = db.relationship('User', secondary='donor_donations', back_populates='donations')

# Beneficiary model
class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'))

    # Relationship with Organization
    organization = db.relationship('Organization', back_populates='beneficiaries')

    # Back reference for InventoryItems
    inventory_items = db.relationship('InventoryItem', back_populates='beneficiary', lazy=True)

# InventoryItem model
class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to Beneficiary
    beneficiary_id = db.Column(db.Integer, db.ForeignKey('beneficiaries.id', ondelete='CASCADE'))

    # Relationship with Beneficiary
    beneficiary = db.relationship('Beneficiary', back_populates='inventory_items')

# Table for many-to-many relationship between User and Donation
class DonorDonation(db.Model):
    __tablename__ = 'donor_donations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    donation_id = db.Column(db.Integer, db.ForeignKey('donations.id', ondelete='CASCADE'))

    # Relationships
    user = db.relationship('User', back_populates='donor_donations')
    donation = db.relationship('Donation', back_populates='donor_donations')
