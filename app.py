from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import json
import os
from functools import wraps
import random
import string
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loan_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
mail = Mail(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    role = db.Column(db.String(20), default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.String(20), unique=True, nullable=False)
    annual_income = db.Column(db.Float)
    employment_status = db.Column(db.String(50))
    employer_name = db.Column(db.String(100))
    credit_score = db.Column(db.Integer)
    documents = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='customer_profile')

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    loan_type = db.Column(db.String(50), nullable=False)
    principal_amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    loan_term_months = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    remaining_balance = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    disbursement_date = db.Column(db.DateTime)
    first_payment_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    customer = db.relationship('Customer', backref='loans')
    approver = db.relationship('User', backref='approved_loans')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)
    payment_number = db.Column(db.Integer, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    principal_amount = db.Column(db.Float, nullable=False)
    interest_amount = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0)
    late_fee = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    loan = db.relationship('Loan', backref='payments')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    loan = db.relationship('Loan', backref='transactions')
    creator = db.relationship('User', backref='transactions')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified_at = db.Column(db.DateTime)
    
    loan = db.relationship('Loan', backref='documents')
    uploader = db.relationship('User', foreign_keys=[uploaded_by], backref='uploaded_documents')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_documents')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # loan_status, payment_reminder, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    related_loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'))
    
    user = db.relationship('User', backref='notifications')
    loan = db.relationship('Loan', backref='notifications')

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(500))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    updater = db.relationship('User', backref='updated_settings')

# Helper functions
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        user = db.session.query(User).filter_by(id=session['user_id']).first()
        if not user or user.role not in ['admin', 'manager']:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def generate_loan_number():
    return f"LN{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"

def calculate_monthly_payment(principal, annual_rate, months):
    monthly_rate = annual_rate / 100 / 12
    if monthly_rate == 0:
        return principal / months
    payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    return round(payment, 2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email_notification(user_email, subject, body, html_body=None):
    try:
        msg = Message(subject, recipients=[user_email])
        msg.body = body
        if html_body:
            msg.html = html_body
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def create_notification(user_id, title, message, notification_type, loan_id=None):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_loan_id=loan_id
    )
    db.session.add(notification)

def generate_amortization_schedule(principal, annual_rate, months):
    monthly_rate = annual_rate / 100 / 12
    monthly_payment = calculate_monthly_payment(principal, annual_rate, months)
    balance = principal
    schedule = []
    
    for month in range(1, months + 1):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        balance -= principal_payment
        
        schedule.append({
            'month': month,
            'payment': monthly_payment,
            'principal': principal_payment,
            'interest': interest_payment,
            'balance': max(0, balance)
        })
    
    return schedule

def generate_loan_report(loan):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph("Loan Report", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Loan details
    loan_data = [
        ['Loan Number:', loan.loan_number],
        ['Customer:', loan.customer.user.full_name],
        ['Loan Type:', loan.loan_type],
        ['Principal Amount:', f"₹{loan.principal_amount:,.2f}"],
        ['Interest Rate:', f"{loan.interest_rate}%"],
        ['Term (Months):', str(loan.loan_term_months)],
        ['Monthly Payment:', f"₹{loan.monthly_payment:,.2f}"],
        ['Total Amount:', f"₹{loan.total_amount:,.2f}"],
        ['Status:', loan.status.title()],
        ['Created:', loan.created_at.strftime('%Y-%m-%d')]
    ]
    
    loan_table = Table(loan_data, colWidths=[150, 200])
    loan_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(loan_table)
    story.append(Spacer(1, 20))
    
    # Amortization schedule
    story.append(Paragraph("Amortization Schedule", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    schedule = generate_amortization_schedule(loan.principal_amount, loan.interest_rate, loan.loan_term_months)
    schedule_data = [['Month', 'Payment', 'Principal', 'Interest', 'Balance']]
    
    for payment in schedule[:12]:  # Show first 12 months
        schedule_data.append([
            str(payment['month']),
            f"₹{payment['payment']:,.2f}",
            f"₹{payment['principal']:,.2f}",
            f"₹{payment['interest']:,.2f}",
            f"₹{payment['balance']:,.2f}"
        ])
    
    if len(schedule) > 12:
        schedule_data.append(['...', '...', '...', '...', '...'])
        schedule_data.append([
            str(len(schedule)),
            f"₹{schedule[-1]['payment']:,.2f}",
            f"₹{schedule[-1]['principal']:,.2f}",
            f"₹{schedule[-1]['interest']:,.2f}",
            f"₹{schedule[-1]['balance']:,.2f}"
        ])
    
    schedule_table = Table(schedule_data, colWidths=[60, 80, 80, 80, 80])
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(schedule_table)
    doc.build(story)
    
    buffer.seek(0)
    return buffer

# Routes
@app.route('/api/loan-calculator', methods=['POST'])
def api_loan_calculator():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        principal = float(data.get('principal', 0))
        rate = float(data.get('rate', 0))
        term = int(data.get('term', 0))
        
        if principal <= 0 or rate < 0 or term <= 0:
            return jsonify({'error': 'Invalid input parameters'}), 400
        
        monthly_payment = calculate_monthly_payment(principal, rate, term)
        total_payment = monthly_payment * term
        total_interest = total_payment - principal
        
        schedule = generate_amortization_schedule(principal, rate, term)
        
        return jsonify({
            'monthly_payment': monthly_payment,
            'total_payment': total_payment,
            'total_interest': total_interest,
            'amortization_schedule': schedule
        })
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid data type: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': 'Server error processing loan calculator'}), 500

@app.route('/upload-document/<int:loan_id>', methods=['POST'])
@login_required
def upload_document(loan_id):
    try:
        loan = db.session.query(Loan).filter_by(id=loan_id).first()
        if not loan:
            flash('Loan not found', 'error')
            return redirect(url_for('dashboard'))
        
        user_role = session.get('role', 'customer')
        user_id = session.get('user_id')
        if user_role not in ['admin', 'manager'] and loan.customer.user_id != user_id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('loan_detail', loan_id=loan_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('loan_detail', loan_id=loan_id))
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            document = Document(
                loan_id=loan_id,
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                file_type=filename.rsplit('.', 1)[1].lower(),
                file_size=os.path.getsize(file_path),
                uploaded_by=session.get('user_id')
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Document uploaded successfully!', 'success')
        else:
            flash('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS), 'error')
    except Exception as e:
        db.session.rollback()
        flash('Error uploading document', 'error')
    
    return redirect(url_for('loan_detail', loan_id=loan_id))

@app.route('/download-document/<int:document_id>')
@login_required
def download_document(document_id):
    try:
        document = db.session.query(Document).filter_by(id=document_id).first()
        if not document:
            flash('Document not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Check if user has access to this document
        user_role = session.get('role', 'customer')
        user_id = session.get('user_id')
        if user_role not in ['admin', 'manager'] and document.loan.customer.user_id != user_id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        if not os.path.exists(document.file_path):
            flash('File not found', 'error')
            return redirect(url_for('dashboard'))
        
        return send_file(document.file_path, as_attachment=True, download_name=document.original_filename)
    except Exception as e:
        flash('Error downloading document', 'error')
        return redirect(url_for('dashboard'))

@app.route('/loan/<int:loan_id>/report')
@login_required
def download_loan_report(loan_id):
    try:
        loan = db.session.query(Loan).filter_by(id=loan_id).first()
        if not loan:
            flash('Loan not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Check if user has access to this loan
        user_role = session.get('role', 'customer')
        user_id = session.get('user_id')
        if user_role not in ['admin', 'manager'] and loan.customer.user_id != user_id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        buffer = generate_loan_report(loan)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"loan_report_{loan.loan_number}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        flash('Error generating report', 'error')
        return redirect(url_for('dashboard'))

@app.route('/notifications')
@login_required
def notifications():
    try:
        user = db.session.query(User).filter_by(id=session.get('user_id')).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('login'))
        
        notifications_list = db.session.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
        return render_template('notifications.html', notifications=notifications_list)
    except Exception as e:
        flash('Error loading notifications', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        notification = db.session.query(Notification).filter_by(id=notification_id).first()
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        if notification.user_id != session.get('user_id'):
            return jsonify({'error': 'Access denied'}), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error updating notification'}), 500

@app.route('/loan-calculator')
def loan_calculator():
    return render_template('loan_calculator.html')

@app.route('/credit-score')
@login_required
def credit_score():
    try:
        user = db.session.query(User).filter_by(id=session.get('user_id')).first()
        customer = db.session.query(Customer).filter_by(user_id=user.id).first() if user else None
        raw_score = customer.credit_score if customer and customer.credit_score is not None else 680
        try:
            score = int(raw_score)
        except Exception:
            score = 680
        score = max(300, min(850, score))
        return render_template('credit_score.html', credit_score=score)
    except Exception:
        flash('Unable to load credit score right now.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/settings')
@admin_required
def admin_settings():
    try:
        settings = db.session.query(SystemSettings).all()
        settings_dict = {setting.key: setting.value for setting in settings}
        
        # Get system stats
        total_users = db.session.query(db.func.count(User.id)).scalar() or 0
        active_loans = db.session.query(db.func.count(Loan.id)).filter_by(status='active').scalar() or 0
        
        return render_template('admin_settings.html', 
                             settings=settings, 
                             settings_dict=settings_dict,
                             total_users=total_users,
                             active_loans=active_loans,
                             current_time=datetime.utcnow())
    except Exception as e:
        flash('Error loading settings', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/settings/update', methods=['POST'])
@admin_required
def update_setting():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        key = data.get('key', '').strip()
        value = data.get('value', '').strip()
        
        if not key or not value:
            return jsonify({'error': 'Key and value are required'}), 400
        
        setting = db.session.query(SystemSettings).filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_by = session.get('user_id')
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSettings(
                key=key,
                value=value,
                updated_by=session.get('user_id')
            )
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error updating setting'}), 500

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('login.html')
            
            user = db.session.query(User).filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            flash('Error during login. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            
            # Validation
            if not all([username, email, password, full_name, phone]):
                flash('All fields are required.', 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('register.html')
            
            if db.session.query(User).filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return render_template('register.html')
            
            if db.session.query(User).filter_by(email=email).first():
                flash('Email already exists.', 'error')
                return render_template('register.html')
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                full_name=full_name,
                phone=phone,
                role='customer'
            )
            db.session.add(user)
            db.session.flush()
            
            customer = Customer(
                user_id=user.id,
                customer_id=f"CUST{user.id:05d}"
            )
            db.session.add(customer)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error during registration. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        user = db.session.query(User).filter_by(id=session.get('user_id')).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('login'))
        
        if user.role == 'customer':
            customer = db.session.query(Customer).filter_by(user_id=user.id).first()
            loans = db.session.query(Loan).filter_by(customer_id=customer.id).all() if customer else []
            return render_template('customer_dashboard.html', user=user, loans=loans)
        
        elif user.role in ['admin', 'manager']:
            total_loans = db.session.query(db.func.count(Loan.id)).scalar() or 0
            active_loans = db.session.query(db.func.count(Loan.id)).filter_by(status='active').scalar() or 0
            pending_loans = db.session.query(db.func.count(Loan.id)).filter_by(status='pending').scalar() or 0
            total_amount = db.session.query(db.func.sum(Loan.principal_amount)).scalar() or 0
            
            recent_loans = db.session.query(Loan).order_by(Loan.created_at.desc()).limit(5).all()
            return render_template('admin_dashboard.html', user=user, total_loans=total_loans,
                                 active_loans=active_loans, pending_loans=pending_loans,
                                 total_amount=total_amount, recent_loans=recent_loans)
    except Exception as e:
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/loans')
@login_required
def loans():
    try:
        user = db.session.query(User).filter_by(id=session.get('user_id')).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('login'))
        
        if user.role == 'customer':
            customer = db.session.query(Customer).filter_by(user_id=user.id).first()
            loans_list = db.session.query(Loan).filter_by(customer_id=customer.id).all() if customer else []
        else:
            loans_list = db.session.query(Loan).all()
        
        return render_template('loans.html', loans=loans_list)
    except Exception as e:
        flash('Error loading loans', 'error')
        return redirect(url_for('dashboard'))

@app.route('/loan/<int:loan_id>')
@login_required
def loan_detail(loan_id):
    try:
        loan = db.session.query(Loan).filter_by(id=loan_id).first()
        if not loan:
            flash('Loan not found', 'error')
            return redirect(url_for('loans'))
        
        user_role = session.get('role', 'customer')
        user_id = session.get('user_id')
        if user_role not in ['admin', 'manager'] and loan.customer.user_id != user_id:
            flash('Access denied', 'error')
            return redirect(url_for('loans'))
        
        payments = db.session.query(Payment).filter_by(loan_id=loan_id).order_by(Payment.payment_number).all()
        return render_template('loan_detail.html', loan=loan, payments=payments)
    except Exception as e:
        flash('Error loading loan details', 'error')
        return redirect(url_for('loans'))

@app.route('/apply-loan', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        try:
            customer = db.session.query(Customer).filter_by(user_id=session.get('user_id')).first()
            if not customer:
                flash('Customer profile not found.', 'error')
                return redirect(url_for('dashboard'))
            
            loan_type = request.form.get('loan_type', '').strip()
            principal = float(request.form.get('principal_amount', 0))
            interest_rate = float(request.form.get('interest_rate', 0))
            term_months = int(request.form.get('loan_term', 0))
            
            # Validation
            if principal <= 0 or interest_rate < 0 or term_months <= 0:
                flash('Invalid loan parameters. Principal and term must be positive.', 'error')
                return render_template('apply_loan.html')
            
            if not loan_type:
                flash('Loan type is required.', 'error')
                return render_template('apply_loan.html')
            
            monthly_payment = calculate_monthly_payment(principal, interest_rate, term_months)
            total_amount = monthly_payment * term_months
            
            loan = Loan(
                loan_number=generate_loan_number(),
                customer_id=customer.id,
                loan_type=loan_type,
                principal_amount=principal,
                interest_rate=interest_rate,
                loan_term_months=term_months,
                monthly_payment=monthly_payment,
                total_amount=total_amount,
                remaining_balance=total_amount
            )
            
            db.session.add(loan)
            db.session.commit()
            
            flash('Loan application submitted successfully!', 'success')
            return redirect(url_for('loans'))
        except (ValueError, TypeError) as e:
            db.session.rollback()
            flash('Invalid input values. Please check your entries.', 'error')
            return render_template('apply_loan.html')
        except Exception as e:
            db.session.rollback()
            flash('Error submitting loan application.', 'error')
            return render_template('apply_loan.html')
    
    return render_template('apply_loan.html')

@app.route('/api/loan/<int:loan_id>/approve', methods=['POST'])
@admin_required
def approve_loan(loan_id):
    try:
        loan = db.session.query(Loan).filter_by(id=loan_id).first()
        if not loan:
            return jsonify({'error': 'Loan not found'}), 404
        
        loan.status = 'approved'
        loan.disbursement_date = datetime.utcnow()
        loan.first_payment_date = datetime.utcnow() + timedelta(days=30)
        loan.approved_by = session.get('user_id')
        
        # Create payment schedule
        for i in range(1, loan.loan_term_months + 1):
            payment = Payment(
                loan_id=loan.id,
                payment_number=i,
                payment_date=loan.first_payment_date + timedelta(days=30*(i-1)),
                amount_due=loan.monthly_payment,
                principal_amount=0,  # Will be calculated based on amortization
                interest_amount=0   # Will be calculated based on amortization
            )
            db.session.add(payment)
        
        # Create notification
        create_notification(
            loan.customer.user_id,
            "Loan Approved",
            f"Your loan application {loan.loan_number} has been approved!",
            "loan_status",
            loan_id
        )
        
        # Send email notification
        subject = "Loan Application Approved"
        body = f"""
Dear {loan.customer.user.full_name},

Your loan application {loan.loan_number} has been approved!

Loan Details:
- Amount: ₹{loan.principal_amount:,.2f}
- Interest Rate: {loan.interest_rate}%
- Term: {loan.loan_term_months} months
- Monthly Payment: ₹{loan.monthly_payment:,.2f}

First payment due: {loan.first_payment_date.strftime('%Y-%m-%d')}

Thank you for choosing our loan services.

Best regards,
Loan Management Team
        """
        
        send_email_notification(loan.customer.user.email, subject, body)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error approving loan'}), 500

@app.route('/api/loan/<int:loan_id>/reject', methods=['POST'])
@admin_required
def reject_loan(loan_id):
    try:
        loan = db.session.query(Loan).filter_by(id=loan_id).first()
        if not loan:
            return jsonify({'error': 'Loan not found'}), 404
        
        loan.status = 'rejected'
        
        # Create notification
        create_notification(
            loan.customer.user_id,
            "Loan Rejected",
            f"Your loan application {loan.loan_number} has been rejected. Please contact us for more information.",
            "loan_status",
            loan_id
        )
        
        # Send email notification
        subject = "Loan Application Status Update"
        body = f"""
Dear {loan.customer.user.full_name},

Your loan application {loan.loan_number} has been rejected.

We appreciate your interest in our loan services. If you have any questions or would like to discuss alternative options, please don't hesitate to contact us.

Thank you for considering our services.

Best regards,
Loan Management Team
        """
        
        send_email_notification(loan.customer.user.email, subject, body)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error rejecting loan'}), 500

@app.route('/make-payment/<int:loan_id>', methods=['POST'])
@login_required
def make_payment(loan_id):
    try:
        loan = db.session.query(Loan).filter_by(id=loan_id).first()
        if not loan:
            flash('Loan not found', 'error')
            return redirect(url_for('loans'))
        
        user_role = session.get('role', 'customer')
        user_id = session.get('user_id')
        if user_role not in ['admin', 'manager'] and loan.customer.user_id != user_id:
            flash('Access denied', 'error')
            return redirect(url_for('loan_detail', loan_id=loan_id))
        
        amount = float(request.form.get('amount', 0))
        
        # Validation
        if amount <= 0:
            flash('Payment amount must be greater than zero.', 'error')
            return redirect(url_for('loan_detail', loan_id=loan_id))
        
        # Find next pending payment
        payment = db.session.query(Payment).filter_by(loan_id=loan_id, status='pending').order_by(Payment.payment_number).first()
        
        if payment:
            # Validate payment amount (allow up to 110% of due amount)
            if amount > payment.amount_due * 1.1:
                flash(f'Payment amount exceeds maximum allowed (₹{payment.amount_due * 1.1:,.2f})', 'error')
                return redirect(url_for('loan_detail', loan_id=loan_id))
            
            payment.amount_paid = amount
            payment.status = 'paid'
            payment.payment_method = request.form.get('payment_method', 'online')
            
            # Update loan balance
            loan.remaining_balance = max(0, loan.remaining_balance - amount)
            
            # Create transaction record
            transaction = Transaction(
                loan_id=loan.id,
                transaction_type='payment',
                amount=amount,
                description=f'Payment for installment {payment.payment_number}',
                created_by=session.get('user_id')
            )
            db.session.add(transaction)
            
            db.session.commit()
            flash('Payment processed successfully!', 'success')
        else:
            flash('No pending payments found.', 'error')
    except (ValueError, TypeError) as e:
        db.session.rollback()
        flash('Invalid payment amount. Please enter a valid number.', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Error processing payment. Please try again.', 'error')
    
    return redirect(url_for('loan_detail', loan_id=loan_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
