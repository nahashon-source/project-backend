from datetime import datetime
from extensions import db

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

    # Back reference for User
    user = db.relationship('User', back_populates='organizations')


# Donation model
class Donation(db.Model):
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20))
    payment_method = db.Column(db.String(50))
    is_anonymous = db.Column(db.Boolean, default=False)
    next_payment_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    stripe_payment_intent_id = db.Column(db.String(100))

    # Foreign key to Organization
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    organization = db.relationship('Organization', back_populates='donations')
    donors = db.relationship('User', secondary='donor_donations', back_populates='donations')


# Table for many-to-many relationship between User and Donation
class DonorDonation(db.Model):
    __tablename__ = 'donor_donations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    donation_id = db.Column(db.Integer, db.ForeignKey('donations.id', ondelete='CASCADE'))

    # Relationships
    user = db.relationship('User', back_populates='donations')
    donation = db.relationship('Donation', back_populates='donors')
