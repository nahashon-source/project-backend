from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import jwt
import os
import stripe
from dotenv import load_dotenv
from functools import wraps
from extensions import db
from models import Donation, User

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# CORS for frontend
CORS(app, origins=["http://localhost:5173"])

# Database and Stripe configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Initialize extensions
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
db.init_app(app)

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        try:
            token = token.split(" ")[1]
            decoded_token = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(decoded_token['user_id'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated_function


@app.route('/create-payment-intent', methods=['POST'])
@token_required
def create_payment_intent(current_user):
    try:
        data = request.json
        if 'amount' not in data or 'currency' not in data or 'organization_id' not in data:
            return jsonify({'error': 'Missing required data!'}), 400

        amount = int(data['amount'] * 100)  # Convert dollars to cents
        if amount <= 0:
            return jsonify({'error': 'Invalid donation amount!'}), 400

        # Create Donation record
        donation = Donation(
            amount=data['amount'],
            frequency=data['frequency'],
            payment_method=data['payment_method'],
            organization_id=data['organization_id'],
            is_anonymous=data.get('is_anonymous', False),
            donors=[current_user] if not data.get('is_anonymous', False) else []
        )
        db.session.add(donation)
        db.session.commit()

        # Create Payment Intent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=data['currency'],
            payment_method_types=data.get('payment_method_types', ['card']),
            metadata={'donation_id': donation.id}
        )

        # Save Payment Intent ID
        donation.stripe_payment_intent_id = intent['id']
        db.session.commit()

        return jsonify({'clientSecret': intent['client_secret']}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        return jsonify({'error': 'Webhook secret not configured!'}), 400

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            donation_id = payment_intent['metadata']['donation_id']
            donation = Donation.query.get(donation_id)
            if donation:
                donation.status = 'completed'
                db.session.commit()

        return jsonify({'status': 'success'}), 200
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return jsonify({'error': str(e)}), 400


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok'}), 200


@app.route('/test-stripe')
def test_stripe():
    return jsonify({'status': 'Stripe integration is working!'}), 200


@app.route('/test-db')
def test_db():
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'Database connection is working!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Run app
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
