from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from vulnleap.models.mortgage_quote import MortgageQuote
from vulnleap.models import db, User, Session, OrgLevelSetting
import bcrypt
import random
import uuid
import re

main = Blueprint('main', __name__)

# Generate a random interest rate between 2.5% and 5.5%
interest_rate = round(random.uniform(2.5, 5.5), 2)

def is_valid_number(value):
    # Check for any case of 'nan' and ensure it's a valid number
    if isinstance(value, str) and value.strip().lower() == 'nan':
        return False
    # Check if value is a valid int or float string
    return re.match(r'^-?\d+(\.\d+)?$', value.strip()) is not None

def is_nan_str(val):
    return isinstance(val, str) and val.strip().lower() == 'nan'

def safe_int(val):
    if is_nan_str(val):
        return None
    try:
        return int(val)
    except Exception:
        return None

def safe_float(val):
    if is_nan_str(val):
        return None
    try:
        return float(val)
    except Exception:
        return None

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/quote', methods=['GET', 'POST'])
def quote():
    if request.method == 'POST':
        loan_term_str = request.form['loan_term']
        home_cost_str = request.form['home_cost']
        credit_score_str = request.form['credit_score']
        down_payment_str = request.form['down_payment']
        loan_term = safe_int(loan_term_str)
        home_cost = safe_float(home_cost_str)
        credit_score = safe_int(credit_score_str)
        down_payment = safe_float(down_payment_str)
        ssn_number = request.form['ssn_number']

        if loan_term is None or home_cost is None or credit_score is None or down_payment is None:
            flash("Invalid input: Please enter valid numbers and do not use 'NaN'.", "danger")
            return redirect(url_for('main.quote'))
        
        if down_payment > home_cost:
            flash("Down payment cannot be greater than home cost.", "danger")
            return redirect(url_for('main.quote'))
        
        if down_payment < 0:
            flash("Down payment cannot be negative.", "danger")
            return redirect(url_for('main.quote'))
        
        if home_cost < 0:
            flash("Home cost cannot be negative.", "danger")
            return redirect(url_for('main.quote'))
        
        if credit_score < 0 or credit_score > 850:
            flash("Credit score must be between 0 and 850.", "danger")
            return redirect(url_for('main.quote'))
        
        final_loan_amount = home_cost - down_payment
        # Calculate the final interest rate based on the credit score - higher credit score = lower interest rate
        final_interest_rate = interest_rate - (credit_score - 600) / 1000
        if final_interest_rate < 0.2:
            final_interest_rate = 0.2  # Set a minimum interest rate
        monthly_interest_rate = final_interest_rate / 100 / 12
        num_payments = loan_term * 12

        if monthly_interest_rate == 0:
            monthly_payment = final_loan_amount / num_payments
        else:
            monthly_payment = final_loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** num_payments) / ((1 + monthly_interest_rate) ** num_payments - 1)

        quote_amount = monthly_payment * num_payments
        total_interest = quote_amount - final_loan_amount

        user_id = None
        if 'user_id' in session and session['user_id'] is not None:
            user_id = session['user_id']

        # Make a new quote object
        if user_id is not None:
            quote = MortgageQuote(property_value=home_cost, credit_score=credit_score, down_payment=down_payment, loan_amount=final_loan_amount, interest_rate=final_interest_rate, term_years=loan_term, monthly_payment=monthly_payment, status='quote', user_id=user_id, total_interest=total_interest, ssn_number=ssn_number)
        else:
            quote = MortgageQuote(property_value=home_cost, credit_score=credit_score, down_payment=down_payment, loan_amount=final_loan_amount, interest_rate=final_interest_rate, term_years=loan_term, monthly_payment=monthly_payment, status='quote', total_interest=total_interest, ssn_number=ssn_number)
        db.session.add(quote)
        db.session.commit()

        return render_template('quote.html',
                               interest_rate=interest_rate,
                               quote_amount=quote_amount,
                               monthly_payment=monthly_payment,
                               total_interest=total_interest,
                               loan_term=loan_term,
                               quote_id=quote.id)
    return render_template('quote.html', interest_rate=interest_rate)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session and session['user_id'] is not None:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template('register.html', username=username)
        
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        quote_id = None
        if 'quote_id' in request.form:
            quote_id = request.form['quote_id']

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', username=username)
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        # TODO: Figure out why SQLAlchemy is throwing an error and move back to standard SQLAlchemy usage - see below
        # Have to escape this so that SQLAlchemy doesn't throw an error
        escaped_password = hashed_password.decode('utf-8').replace("'", "''")

        # Create a new user object
        # TODO: Figure out why SQLAlchemy is throwing an error and move back to standard SQLAlchemy usage
        from sqlalchemy import text
        query_result = None
        try:
            sql_query = f"INSERT INTO users (username, password_hash, user_type) VALUES ('{username}', '{escaped_password}', '{role}')"
            query_result = db.session.execute(text(sql_query))
            db.session.commit()
        except Exception as e:
            flash("Error creating user: " + str(e) + " - " + str(query_result), "danger")
            return redirect(url_for('main.register'))

        try:
            user = User.query.filter_by(username=username).first()
            if not user:
                flash("Error creating user: User not found after creation", "danger")
                return redirect(url_for('main.register'))
        except Exception as e:
            flash("Error creating user: " + str(e), "danger")
            return redirect(url_for('main.register'))

        if quote_id:
            quote = MortgageQuote.query.get(quote_id)
            quote.user_id = user.id
            db.session.commit()

        # Create a flask session
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_type'] = user.user_type
        session['session_token'] = str(uuid.uuid4())
        session.permanent = True
        db.session.add(Session(user_id=user.id, session_token=session['session_token']))

        return redirect(url_for('main.index'))

    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    # Check if the user is already logged in
    if 'user_id' in session and session['user_id'] is not None:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Invalid username.", "danger")
            return redirect(url_for('main.login'))
        
        # Ensure password_hash is bytes for bcrypt
        password_hash = user.password_hash
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        # Check if the password is correct
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            flash("Invalid password.", "danger")
            return redirect(url_for('main.login'))
        
        # Create a flask session
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_type'] = user.user_type
        session['session_token'] = str(uuid.uuid4())
        session.permanent = True
        db.session.add(Session(user_id=user.id, session_token=session['session_token']))

        return redirect(url_for('main.index'))
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('session_token', None)
    return redirect(url_for('main.index'))

@main.route('/user', methods=['GET', 'POST'])
def user():
    if not session or 'user_id' not in session or session['user_id'] is None:
        flash("You must be logged in to access this page.", "danger")
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        
        user = User.query.get(session['user_id'])
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('main.login'))
        
        if "password" in request.form:
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for('main.user'))
            user.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for('main.user'))
    quotes = MortgageQuote.query.filter_by(user_id=session['user_id']).all()
    return render_template('user_page.html', quotes=quotes)

@main.route('/quote/<int:quote_id>')
def quote_page(quote_id):
    if not session or 'user_id' not in session or session['user_id'] is None:
        flash("You must be logged in to access this page.", "danger")
        return redirect(url_for('main.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")

    quote = MortgageQuote.query.get(quote_id)
    if not quote:
        flash("Quote not found.", "danger")
        return redirect(url_for('main.user'))
    return render_template('existing_quote.html', quote=quote)

@main.route('/admin')
def admin():
    if not session or 'user_id' not in session or session['user_id'] is None:
        flash("You must be logged in to access this page.", "danger")
        return redirect(url_for('main.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('main.login'))
    
    # Check if the user is an admin
    if user.user_type != 'superadmin' and user.user_type != 'admin':
        flash("You do not have access to this page.", "danger")
        return redirect(url_for('main.index'))
    

    # Get a list of all users and their roles
    users = User.query.all()
    user_roles = {}
    for user in users:
        user_roles[user.id] = user.user_type

    # Get a list of all quotes and their user ids
    quotes = MortgageQuote.query.all()
    quote_users = {}
    for quote in quotes:
        quote_users[quote.id] = quote.user_id
    
    return render_template('admin.html', user=user, users=users, user_roles=user_roles, quotes=quotes, quote_users=quote_users)


@main.route('/remove_user/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    if not session or 'user_id' not in session or session['user_id'] is None:
        flash("You must be logged in to access this page.", "danger")
        return redirect(url_for('main.login'))
    
    current_user = User.query.get(session['user_id'])
    if not current_user:
        flash("User not found.", "danger")
        return redirect(url_for('main.login'))
    
    # Check if the current user is an admin or superadmin
    if current_user.user_type != 'superadmin' and current_user.user_type != 'admin':
        flash("You do not have permission to remove users.", "danger")
        return redirect(url_for('main.admin'))
    
    # Get the user to be removed
    user_to_remove = User.query.get(user_id)
    if not user_to_remove:
        flash("User to remove not found.", "danger")
        return redirect(url_for('main.admin'))
    
    # Prevent admins from removing superadmins (only superadmins can remove superadmins)
    if current_user.user_type == 'admin' and user_to_remove.user_type == 'superadmin':
        flash("You do not have permission to remove superadmin users.", "danger")
        return redirect(url_for('main.admin'))
    
    # Prevent users from removing themselves
    if current_user.id == user_to_remove.id:
        flash("You cannot remove yourself.", "danger")
        return redirect(url_for('main.admin'))
    
    try:
        # Remove all sessions for this user
        Session.query.filter_by(user_id=user_id).delete()
        
        # Remove all quotes associated with this user
        MortgageQuote.query.filter_by(user_id=user_id).delete()
        
        # Remove the user
        db.session.delete(user_to_remove)
        db.session.commit()
        
        flash(f"User '{user_to_remove.username}' has been successfully removed.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error removing user: {str(e)}", "danger")
    
    return redirect(url_for('main.admin'))


@main.route('/orgadmin')
def orgadmin():
    if 'user_id' not in session or session['user_id'] is None:
        flash("You must be logged in to access this page.", "danger")
        return redirect(url_for('main.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('main.login'))
    
    # Check if the user is an org admin
    if user.user_type != 'superadmin':
        flash("You do not have access to this page.", "danger")
        return redirect(url_for('main.index'))
    
    # Functionality to add new admins and superadmins
    if request.method == 'POST':
        # Check if this is a new user creation or a setting change
        if 'username' in request.form:
            # New user creation
            username = request.form['username']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            role = request.form['role']
                    
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for('main.orgadmin'))
            
            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create a new user object
            new_user = User(username=username, password_hash=hashed_password, user_type=role)
            db.session.add(new_user)
            db.session.commit()
            flash("User created successfully.", "success")
            return redirect(url_for('main.orgadmin'))
        else:
            # Setting change
            setting_key = request.form['setting_key']
            setting_value = request.form['setting_value']
            
            # Create a new org level setting object
            new_setting = OrgLevelSetting(setting_key=setting_key, setting_value=setting_value, last_modified_by=user.id)
            db.session.add(new_setting)
            db.session.commit()
            flash("Setting updated successfully.", "success")
            return redirect(url_for('main.orgadmin'))
    
    # Get all org level settings for the current org
    org_settings = OrgLevelSetting.query.all()
    return render_template('orgadmin.html', user=user, org_settings=org_settings)