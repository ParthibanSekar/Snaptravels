from functools import wraps
from flask import session, redirect, url_for, flash, request
from app.models import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class AuthService:
    @staticmethod
    def signup(email, password):
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return {'success': False, 'error': 'Email already registered'}
        
        # Create new user
        password_hash = generate_password_hash(password)
        user = User(email=email, password_hash=password_hash, role='user')
        
        try:
            db.session.add(user)
            db.session.commit()
            return {'success': True, 'user': user}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': 'Registration failed'}
    
    @staticmethod
    def login(email, password):
        # Look up user first so we can check role before applying chaos.
        user = User.query.filter_by(email=email).first()

        # Chaos hook: injects scheduled/manual login outages.
        # Admin accounts are exempt — they must always be able to log in
        # to reach the chaos control panel and end an outage.
        is_admin = user and user.role == 'admin'
        if not is_admin:
            from app.services.chaos import maybe_fail_login, LoginChaosError
            try:
                maybe_fail_login(email=email)
            except LoginChaosError as e:
                return {'success': False, 'error': str(e)}

        if user and check_password_hash(user.password_hash, password):
            return {'success': True, 'user': user}
        else:
            return {'success': False, 'error': 'Invalid email or password'}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            user = User.query.get(session['user_id'])
            if not user or user.role != required_role:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('public.home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None