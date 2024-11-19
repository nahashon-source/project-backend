from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env file
load_dotenv()

# Import db and models from extensions and models
from extensions import db
from models import User, Organization, Donation, Beneficiary, InventoryItem

app = Flask(__name__)

# Enable CORS for the Flask app (adjust origin to match your frontend app)
CORS(app, origins=["http://localhost:5173"])

# Initialize extensions
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)  # JWT expires in 1 hour

# Initialize the database
db.init_app(app)

# JWT Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        try:
            token = token.split(" ")[1]  # "Bearer <Token>"
            decoded_token = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(decoded_token['user_id'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated_function



# Health check route
@app.route('/health')
def health_check():
    return jsonify({'status': 'ok'}), 200

# User routes
@app.route('/users', methods=['POST'])
def create_user():
    data = request.json

    # Validate input data
    if not data.get('name') or not data.get('email') or not data.get('password') or not data.get('role'):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if the user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already in use'}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password,
        role=data['role']
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()

    # Validate user credentials
    if user and bcrypt.check_password_hash(user.password, data['password']):
        token = jwt.encode(
            {'user_id': user.id, 'email': user.email, 'exp': datetime.utcnow() + timedelta(hours=1)},
            app.config['JWT_SECRET_KEY'],
            algorithm="HS256"
        )
        return jsonify({
            'token': token,
            'user': {'id': user.id, 'email': user.email, 'role': user.role}
        }), 200
    return jsonify({'error': 'Invalid credentials'}), 401

# Organization routes
@app.route('/organizations', methods=['GET', 'POST'])
@token_required
def organizations(current_user):
    if request.method == 'POST':
        data = request.json
        if not data.get('name') or not data.get('description'):
            return jsonify({'error': 'Missing required fields'}), 400

        org = Organization(
            name=data['name'],
            description=data['description'],
            user_id=current_user.id
        )
        db.session.add(org)
        db.session.commit()
        return jsonify({'message': 'Organization created successfully'}), 201
    
    # Pagination for organizations
    page = request.args.get('page', 1, type=int)
    orgs = Organization.query.paginate(page, 10, False)  # 10 per page
    return jsonify({
        'organizations': [{
            'id': org.id,
            'name': org.name,
            'description': org.description,
            'status': org.status
        } for org in orgs.items],
        'total': orgs.total
    }), 200

# Donation routes
@app.route('/donations', methods=['POST'])
@token_required
def create_donation(current_user):
    data = request.json

    # Validate donation data
    if data['amount'] <= 0:
        return jsonify({'error': 'Donation amount must be positive'}), 400
    if data['frequency'] not in ['one-time', 'monthly', 'yearly']:
        return jsonify({'error': 'Invalid donation frequency'}), 400
    if data['payment_method'] not in ['credit_card', 'mpesa', 'paypal']:
        return jsonify({'error': 'Invalid payment method'}), 400

    donation = Donation(
        amount=data['amount'],
        frequency=data['frequency'],
        payment_method=data['payment_method'],
        organization_id=data['organization_id'],
        is_anonymous=data.get('is_anonymous', False),
        next_payment_date=data.get('next_payment_date', None)
    )
    
    # If not anonymous, associate with the current user
    if not donation.is_anonymous:
        donation.donors.append(current_user)
    
    db.session.add(donation)
    db.session.commit()
    return jsonify({'message': 'Donation recorded successfully', 'donation_id': donation.id}), 201

# Inventory routes
@app.route('/inventory', methods=['POST'])
@token_required
def add_inventory(current_user):
    data = request.json
    if not data.get('name') or not data.get('quantity') or not data.get('beneficiary_id') or not data.get('date_sent'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        date_sent = datetime.strptime(data['date_sent'], '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format, should be YYYY-MM-DD'}), 400

    item = InventoryItem(
        name=data['name'],
        quantity=data['quantity'],
        beneficiary_id=data['beneficiary_id'],
        date_sent=date_sent
    )
    
    db.session.add(item)
    db.session.commit()
    return jsonify({'message': 'Inventory item added successfully'}), 201

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
