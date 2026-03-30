from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
import re
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import secrets
from functools import wraps
import requests
import qrcode
from io import BytesIO
import smtplib
import ssl
from email.message import EmailMessage
from flask_socketio import SocketIO, emit
import csv
import io
from flask import make_response
from ml_engine import LogisticsAI
from geopy.distance import geodesic

ai_engine = LogisticsAI()

app = Flask(__name__)

app.config['SECRET_KEY'] = '1234'

# --- NEW: Email Configuration for OTP (UPDATE THESE) ---
EMAIL_SENDER = 'og.capstone@gmail.com' 
EMAIL_PASSWORD = 'ddvv xrme zvnj qyma' # Use an App Password if using Gmail
EMAIL_SMTP_SERVER = 'smtp.gmail.com' # Change if not using Gmail
EMAIL_SMTP_PORT = 587 

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MySQL Database Configuration
db_config = {
    'host': "vaahansetu-server.mysql.database.azure.com",
    'user': "ruxnlbvker",
    'password': "Rohith1202bn*",
    'database': "vaahansetu",
    'port': 3306,
    'ssl_ca': "MysqlflexGlobalRootCA.crt.pem"
}

# --- Initialization ---
bcrypt = Bcrypt(app)

# Initialize SocketIO after 'app' definition
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Database Connection Function ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None
    
'''def create_database_if_not_exists():
    """
    Connects to MySQL server without a specific database 
    and creates the 'vaahansetu' database if it doesn't exist.
    """
    try:
        # 1. Connect to MySQL Server ONLY (No Database specified yet)
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        
        # 2. Create the database
        db_name = db_config['database']
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database '{db_name}' checked/created successfully.")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Error as e:
        print(f"Error creating database: {e}")'''
    

# ADD THIS DECORATOR FOR ADMIN SECURITY
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('You must be logged in as an admin to view this page.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ADD THIS NEW DECORATOR for driver security
def driver_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'driver_logged_in' not in session:
            flash('You must be logged in as a driver to view this page.', 'danger')
            return redirect(url_for('driver_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Function to Create Tables (MODIFIED to include otp_codes table) ---
def create_tables():
    conn = get_db_connection()
    if conn is None:
        print("Could not connect to the database. Table creation failed.")
        return
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # MODIFIED: Added is_verified column to users table
      # Updated users table definition in app.py
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                phone_number VARCHAR(20),
                is_verified BOOLEAN DEFAULT FALSE,
                age INT,
                gender VARCHAR(20),
                register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'Active'
            )
        """)
        conn.commit()
        print("Table 'users' checked/created successfully.")

        # NEW TABLE: otp_codes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL,
                otp_code VARCHAR(10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("Table 'otp_codes' checked/created successfully.")


        # --- MODIFIED CREATE TABLE drivers STATEMENT ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                application_id VARCHAR(25) NOT NULL UNIQUE,
                application_status VARCHAR(50) NOT NULL DEFAULT 'Submitted',
                full_name VARCHAR(255) NOT NULL,
                dob DATE NOT NULL,
                contact_number VARCHAR(15) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                address TEXT NOT NULL,
                city VARCHAR(100) NOT NULL,
                pincode VARCHAR(10) NOT NULL,
                profile_photo_path VARCHAR(255),
                vehicle_photo_path VARCHAR(255),
                license_number VARCHAR(50) NOT NULL UNIQUE,
                license_expiry_date DATE NOT NULL,
                vehicle_type VARCHAR(50) NOT NULL,
                vehicle_model VARCHAR(255),
                vehicle_reg_no VARCHAR(50) NOT NULL UNIQUE,
                has_insurance VARCHAR(3) NOT NULL,
                insurance_policy_no VARCHAR(255),
                insurance_expiry_date DATE, 
                driving_license_path VARCHAR(255),
                aadhaar_path VARCHAR(255),
                pan_path VARCHAR(255),
                rc_path VARCHAR(255),
                insurance_path VARCHAR(255),
                acc_holder_name VARCHAR(255) NOT NULL,
                acc_number VARCHAR(50) NOT NULL,
                ifsc_code VARCHAR(20) NOT NULL,
                bank_name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Table 'drivers' checked/created successfully.")

        # Inside the create_tables() function
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                driver_id INT,
                vehicle_model VARCHAR(255),
                has_insurance VARCHAR(3) NOT NULL,
                insurance_policy_no VARCHAR(255),
                insurance_expiry_date DATE,
                insurance_path VARCHAR(255),
                vehicle_photo_path VARCHAR(255),
                vehicle_reg_no VARCHAR(50) NOT NULL UNIQUE,
                vehicle_type VARCHAR(50) NOT NULL,
                rc_path VARCHAR(255),
                status VARCHAR(50) NOT NULL DEFAULT 'Submitted',
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("Table 'vehicles' checked/created successfully.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL,           -- NEW: Required for profile
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'admin',      -- Preserving your existing field
                last_login TIMESTAMP NULL,             -- Preserving your existing field
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- NEW: Required for profile
            )
        """)
        conn.commit()
        print("Table 'admins' checked/created successfully.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id INT AUTO_INCREMENT PRIMARY KEY,
                driver_id INT,
                booked_by VARCHAR(100), -- NEW COLUMN: Stores logged-in user's email
                pnr_number VARCHAR(20) UNIQUE,
                customer_name VARCHAR(255),
                customer_email VARCHAR(100),
                customer_phone VARCHAR(20),
                customer_gender VARCHAR(10),
                customer_age INT,
                pickup_location TEXT,
                pickup_lat DECIMAL(10, 8),
                pickup_lng DECIMAL(11, 8),
                drop_location TEXT,
                drop_lat DECIMAL(10, 8),
                drop_lng DECIMAL(11, 8),
                fare VARCHAR(50),
                load_weight VARCHAR(50),
                vehicle_type_booked VARCHAR(50),
                status VARCHAR(50) DEFAULT 'Pending',
                toll_tax DECIMAL(10, 2) DEFAULT 0.00,
                payment_method VARCHAR(50) DEFAULT 'Cash',
                total_fare DECIMAL(10, 2) DEFAULT 0.00,
                rating INT DEFAULT NULL,
                feedback TEXT DEFAULT NULL,
                booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("Table 'trips' checked/created successfully.")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS declined_trips (
                id INT AUTO_INCREMENT PRIMARY KEY,
                trip_id INT,
                driver_id INT,
                declined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("Table 'declined_trips' checked/created successfully.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS developers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(100) NOT NULL,
                reg_no VARCHAR(50) NOT NULL,
                year_study VARCHAR(20) NOT NULL,
                department VARCHAR(100) NOT NULL,
                college VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                linkedin VARCHAR(255),
                github VARCHAR(255),
                is_leader BOOLEAN DEFAULT FALSE,
                photo_path VARCHAR(255)
            )
        """)
        conn.commit()
        print("Table 'developers' checked/created successfully.")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guides (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                designation VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL,
                college VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                photo_path VARCHAR(255)
            )
        """)
        conn.commit()
        print("Table 'guides' checked/created successfully.")

        # Check if the admins table is empty
        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            print("Admins table is empty. Creating default admin...")
            
            # Default Credentials
            username = "admin"
            email = "admin@quickload.com"  # <--- ADDED EMAIL
            password = "admin"
            
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # UPDATED QUERY: Included 'email' column and value
            cursor.execute(
                "INSERT INTO admins (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            conn.commit()
            print(f"Default admin user '{username}' created successfully.")
        # --- END OF BLOCK ---
    except Error as e:
        print(f"Error creating table: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn.is_connected():
            conn.close()

# --- NEW HELPER FUNCTIONS FOR OTP ---

def generate_otp():
    """Generates a 6-digit OTP."""
    return secrets.randbelow(900000) + 100000

def send_otp_email(recipient_email, otp_code, username):
    """Sends the OTP code to the recipient via email using an HTML template."""
    
    # --- HTML Email Body ---
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
            .header {{ background-color: #e78c56; padding: 20px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .content {{ padding: 30px; text-align: center; color: #333333; }}
            .otp-box {{ background-color: #ffe8d6; border: 1px solid #e78c56; padding: 20px; border-radius: 6px; margin: 25px 0; display: inline-block; }}
            .otp-code {{ font-size: 36px; font-weight: bold; letter-spacing: 5px; color: #e78c56; margin: 0; }}
            .greeting {{ font-size: 18px; margin-bottom: 20px; text-align: left; }}
            .action-text {{ font-size: 16px; line-height: 1.5; text-align: left; }}
            .security-note {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dddddd; text-align: left; font-size: 14px; color: #777777; }}
            .security-note p {{ margin-bottom: 5px; }}
            .footer {{ background-color: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #aaaaaa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>QuickLoad Verification</h1>
            </div>
            <div class="content">
                <p class="greeting">Dear <strong>{username}</strong>,</p>

                <p class="action-text">
                    You recently requested an **One-Time Password (OTP)** to verify your email address. 
                    Please use the code below to complete your sign-up or login process.
                </p>

                <div class="otp-box">
                    <p>Your Verification Code:</p>
                    <p class="otp-code">{otp_code}</p>
                </div>

                <p class="action-text">
                    **This code is valid for 5 minutes.** Please enter it immediately on the verification page. 
                    Do not share this code with anyone.
                </p>

                <div class="security-note">
                    <p><strong>Security Tip:</strong></p>
                    <p>If you did not request this OTP, please **ignore this email**. It means someone else may have entered your email address by mistake. Your account remains secure unless you share this code.</p>
                </div>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} QuickLoad. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    # --- END HTML Email Body ---


    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = "Your One-Time Password (OTP) for QuickLoad" # Subject should be simple
    
    # Set the content type to HTML
    em.set_content(html_body, subtype='html') 

    # Add SSL (layer of security)
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    

def send_password_reset_email(recipient_email, username, otp_code):
    """Sends a specific Password Reset OTP email."""
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
            .container {{ max-width: 500px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb; }}
            .header {{ background-color: #dc2626; padding: 25px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 20px; color: #ffffff; font-weight: 700; }}
            .content {{ padding: 30px; color: #374151; text-align: center; }}
            .icon-circle {{ width: 60px; height: 60px; background: #fee2e2; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }}
            .otp-box {{ background-color: #f9fafb; border: 2px dashed #dc2626; padding: 15px; border-radius: 8px; margin: 25px 0; display: inline-block; }}
            .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #dc2626; margin: 0; }}
            .warning-text {{ font-size: 13px; color: #6b7280; background: #f3f4f6; padding: 10px; border-radius: 6px; margin-top: 20px; text-align: left; }}
            .footer {{ background-color: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <div class="icon-circle">
                    <span style="font-size: 30px; color: #dc2626;">&#128274;</span> </div>
                <p style="font-size: 16px; margin-bottom: 5px;">Hello <strong>{username}</strong>,</p>
                <p style="color: #6b7280; font-size: 14px;">We received a request to reset your QuickLoad driver password.</p>

                <div class="otp-box">
                    <div class="otp-code">{otp_code}</div>
                </div>

                <p style="font-size: 14px;">Enter this code to proceed with resetting your password.</p>
                
                <div class="warning-text">
                    <strong>Security Alert:</strong> This code expires in 5 minutes. If you did not request a password reset, please ignore this email and your account will remain secure.
                </div>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} QuickLoad. Secure System.
            </div>
        </div>
    </body>
    </html>
    """

    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = "Action Required: Reset Your Password"
    em.set_content(html_body, subtype='html')

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending reset email: {e}")
        return False
    
def store_and_send_reset_otp(conn, email, username):
    """Generates and sends a Password Reset OTP."""
    otp_code = str(generate_otp()) # Reuses your existing 6-digit generator
    expires_at = datetime.now() + timedelta(minutes=5)
    
    cursor = conn.cursor()
    try:
        # Clear old OTPs
        cursor.execute("DELETE FROM otp_codes WHERE email = %s", (email,))
        
        # Insert new OTP
        cursor.execute("INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (%s, %s, %s)",
                       (email, otp_code, expires_at))
        conn.commit()
        
        # Send the "Password Reset" specific email
        if send_password_reset_email(email, username, otp_code):
            return True, "Reset code sent to your email."
        else:
            return False, "Failed to send email."
    except Error as e:
        print(f"DB Error: {e}")
        return False, "Database error."
    finally:
        cursor.close()

def store_and_send_otp(conn, email, first_name):
    """Generates, stores, and sends a new OTP."""
    otp_code = str(generate_otp())
    expires_at = datetime.now() + timedelta(minutes=5) # OTP valid for 5 minutes
    
    cursor = conn.cursor()
    try:
        # Clear any old OTPs for this user
        cursor.execute("DELETE FROM otp_codes WHERE email = %s", (email,))
        conn.commit()

        # Store the new OTP
        cursor.execute("INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (%s, %s, %s)",
                       (email, otp_code, expires_at))
        conn.commit()
        
        # Send the email
        if send_otp_email(email, otp_code, first_name):
            return True, "OTP sent successfully. Please check your inbox."
        else:
            # Failed to send email, delete OTP from DB to prevent false success
            cursor.execute("DELETE FROM otp_codes WHERE email = %s AND otp_code = %s", (email, otp_code))
            conn.commit()
            return False, "Failed to send OTP email. Check server configuration."
            
    except Error as e:
        print(f"DB Error during OTP storage: {e}")
        return False, "A database error occurred during OTP process."
    finally:
        cursor.close()

# --- ROUTES (MODIFIED/NEW) ---


# --- UPDATED LANDING PAGE ROUTES (Fetch Team from DB) ---

@app.route('/')
@app.route('/landing_page')
def landing_page():
    conn = get_db_connection()
    
    # Initialize lists to avoid errors if DB fails
    developers = []
    guides = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Fetch Developers (Sort by Leader first, then Name)
            cursor.execute("SELECT * FROM developers ORDER BY is_leader DESC, name ASC")
            developers = cursor.fetchall()
            
            # 2. Fetch Guides
            cursor.execute("SELECT * FROM guides ORDER BY name ASC")
            guides = cursor.fetchall()
            
            # 3. Process Images for Public Access
            default_img = url_for('static', filename='images/default_profile.png')
            
            for p in developers + guides:
                # Use the helper function 'get_public_url' you already have in app.py
                p['photo_url'] = get_public_url(p.get('photo_path')) or default_img

        except Error as e:
            print(f"Error fetching team data: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template('landing_page.html', developers=developers, guides=guides)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_candidate = request.form.get('password')

        if not email or not password_candidate:
            flash('Please enter both email and password.', 'danger')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'danger')
            return redirect(url_for('login'))

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Ensure 'status' is selected. 'SELECT *' covers this if the column exists.
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                # --- [NEW CHECK START] ---
                # Check for Account Suspension FIRST
                # This prevents suspended users from proceeding even if they have the correct password.
                if user.get('status') == 'Suspended':
                    flash('Your account has been Suspended. Please contact support.', 'danger')
                    return redirect(url_for('login'))
                # --- [NEW CHECK END] ---

                if bcrypt.check_password_hash(user['password'], password_candidate):
                    # Existing Check: User must be verified
                    if not user['is_verified']:
                        session['unverified_email'] = user['email']
                        session['unverified_first_name'] = user['first_name']
                        flash('Your email is not verified. Please verify your email to log in.', 'warning')
                        return redirect(url_for('verify_email'))
                    
                    session['logged_in'] = True
                    session['email'] = user['email']
                    session['first_name'] = user['first_name']
                    session['last_name'] = user['last_name']  # <--- ADD THIS LINE
                    # Optional: Store user ID if needed for other features
                    session['user_id'] = user['id'] 
                    
                    return redirect(url_for('home'))
                else:
                    flash('Invalid email or password.', 'danger')
                    return redirect(url_for('login'))
            else:
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('login'))

        except Error as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('login'))
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        errors = {}
        form_data = request.form

        first_name = form_data.get('first_name', '').strip()
        last_name = form_data.get('last_name', '').strip()
        email = form_data.get('email', '').strip()
        password = form_data.get('password', '')
        confirm_password = form_data.get('confirm_password', '')

        if not first_name: errors['first_name'] = 'First name is required.'
        if not last_name: errors['last_name'] = 'Last name is required.'
        if not email: errors['email'] = 'Email is required.'
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email): errors['email'] = 'Invalid email address.'
        if len(password) < 8: errors['password'] = 'Password must be at least 8 characters long.'
        elif not re.search("[0-9]", password): errors['password'] = 'Password must contain at least one number.'
        elif not re.search("[A-Z]", password): errors['password'] = 'Password must contain at least one uppercase letter.'
        if password != confirm_password: errors['confirm_password'] = 'Passwords do not match.'

        # --- FIX 1: Flash specific validation errors ---
        if errors:
            for msg in errors.values():
                flash(msg, 'danger')  # This makes the alert appear
            
            session['form_errors'] = errors
            session['form_data'] = dict(form_data)
            return redirect(url_for('register'))
        # -----------------------------------------------

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('register'))

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # 1. Check if email is already registered
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()

            # --- FIX 2: Flash "Email Exists" error ---
            if existing_user:
                if existing_user['is_verified']:
                    msg = 'This email is already registered and verified.'
                    flash(msg, 'danger')  # This makes the alert appear
                    
                    session['form_errors'] = {'email': msg}
                    session['form_data'] = dict(form_data)
                    return redirect(url_for('register'))
                else:
                    # If user exists but is not verified, redirect to verification page
                    session['unverified_email'] = email
                    session['unverified_first_name'] = first_name
                    flash('This email is already registered but unverified. Please enter the OTP sent to your email.', 'info')
                    return redirect(url_for('verify_email'))
            # -----------------------------------------

            # 2. Insert new user (unverified by default)
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("INSERT INTO users(first_name, last_name, email, password, is_verified) VALUES(%s, %s, %s, %s, FALSE)",
                           (first_name, last_name, email, hashed_password))
            conn.commit()
            
            # 3. Store info in session for OTP verification
            session['unverified_email'] = email
            session['unverified_first_name'] = first_name
            
            # 4. Send the initial OTP and check result
            success, msg = store_and_send_otp(conn, email, first_name)
            
            if success:
                flash(msg, 'success')
                return redirect(url_for('verify_email'))
            else:
                # If email sending failed, we should still proceed to the verification page but show the error
                flash(msg, 'danger')
                return redirect(url_for('verify_email'))

        except Error as e:
            flash(f'A database error occurred: {str(e)}', 'danger')
            session['form_data'] = dict(form_data)
            return redirect(url_for('register'))
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
    
    errors = session.pop('form_errors', {})
    form_data = session.pop('form_data', {})
    return render_template('register.html', errors=errors, form_data=form_data)

# --- NEW: OTP Verification Routes ---

# --- MODIFIED: /verify_email route ---
@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    email = session.get('unverified_email')
    
    # 1. Fetch user details to get first name and original email
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'danger')
        return redirect(url_for('register'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT first_name, email FROM users WHERE email = %s", (email,))
    user_data = cursor.fetchone()
    
    if not user_data:
        # If user data is missing (e.g., session expired), redirect to register
        flash('Verification failed: Please start registration again.', 'danger')
        return redirect(url_for('register'))

    first_name = user_data['first_name']
    
    if request.method == 'POST':
        otp_entered = request.form.get('otp', '').strip()
        
        # Re-establish connection for transactional logic
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'danger')
            return redirect(url_for('register'))
        cursor = conn.cursor()
        
        try:
            # 2. Check for valid, unexpired OTP
            cursor.execute("""
                SELECT id FROM otp_codes 
                WHERE email = %s AND otp_code = %s AND expires_at > NOW()
            """, (email, otp_entered))
            
            otp_record = cursor.fetchone()
            
            if otp_record:
                # 3. Mark user as verified
                cursor.execute("UPDATE users SET is_verified = TRUE WHERE email = %s", (email,))
                
                # 4. Delete OTP record to prevent reuse
                cursor.execute("DELETE FROM otp_codes WHERE email = %s", (email,))
                conn.commit()
                
                # 5. Clear unverified session data
                session.pop('unverified_email', None)
                session.pop('unverified_first_name', None)
                
                # 6. Send the Welcome Email (WITHOUT team members)
                send_welcome_email(email, first_name)
                
                # 7. Store greeting data and redirect
                session['greeting_name'] = first_name # For the HTML success page
                
                flash('Email verified successfully!', 'success')
                
                return redirect(url_for('login')) 
            else:
                flash('Invalid or expired OTP. Please try again or resend the code.', 'danger')
                return render_template('otp_verification.html', email=email)
                
        except Error as e:
            conn.rollback()
            flash(f'An error occurred during verification: {e}', 'danger')
            return render_template('otp_verification.html', email=email)
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()
    
    # GET request
    return render_template('otp_verification.html', email=email)

# --- NEW: Welcome Email Function ---
def send_welcome_email(recipient_email, username):
    """Sends a congratulatory and welcoming email with platform details and developer info."""
    
    # --- HTML Email Body ---
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border-top: 5px solid #e78c56; }}
            .header {{ background-color: #e78c56; padding: 20px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .content {{ padding: 30px; color: #333333; }}
            .greeting {{ font-size: 22px; margin-bottom: 20px; color: #e78c56; font-weight: 600; text-align: center; }}
            .info-box {{ background-color: #f8f8f8; border: 1px solid #eeeeee; padding: 20px; border-radius: 6px; margin: 20px 0; }}
            .info-box h3 {{ color: #e78c56; margin-bottom: 10px; font-size: 18px; }}
            .feature-list {{ list-style-type: none; padding: 0; }}
            .feature-list li {{ margin-bottom: 10px; padding-left: 20px; position: relative; font-size: 15px; line-height: 1.4; }}
            .feature-list li::before {{ content: '\\2705'; /* Green Checkmark */ position: absolute; left: 0; color: #2ecc71; font-weight: bold; }}
            .action-btn {{ display: inline-block; background-color: #2ecc71; color: white !important; padding: 12px 25px; text-decoration: none; border-radius: 50px; margin-top: 20px; font-weight: 600; transition: background-color 0.3s; }}
            .action-btn:hover {{ background-color: #27ae60; }}
            .footer {{ background-color: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #aaaaaa; border-top: 1px solid #eeeeee; }}
            .team-section {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eeeeee; text-align: left; }}
            .team-section h4 {{ color: #333; margin-bottom: 10px; font-weight: 600; font-size: 14px; }}
            .team-section ul {{ list-style-type: disc; padding-left: 20px; margin: 0; font-size: 13px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to QuickLoad!</h1>
            </div>
            <div class="content">
                <p class="greeting">Hello, {username},</p>

                <p style="font-size: 16px; line-height: 1.5;">
                    Congratulations! Your account has been successfully verified. You are now ready to explore **QuickLoad**, the real-time smart booking platform connecting customers with goods vehicle services.
                </p>

                <div class="info-box">
                    <h3>Key Features Await You:</h3>
                    <ul class="feature-list">
                        <li>**Smart Matching:** Get instantly connected with the perfect goods vehicle for your cargo needs.</li>
                        <li>**Direct Connection:** Communicate directly with drivers/customers—no middlemen, lower costs!</li>
                        <li>**Real-Time Tracking:** Monitor your transport requests from booking to completion.</li>
                        <li>**Increased Earnings/Affordability:** Drivers earn more; customers save more.</li>
                    </ul>
                </div>
                
                <p style="text-align: center;">
                    <a href="{url_for('login', _external=True)}" class="action-btn">
                        Log In to Start Booking!
                    </a>
                </p>

                <div class="team-section">
                    <h4>Developed by Team UNIQUE:</h4>
                    <ul>
                        <li>Boppana Rohith</li>
                        <li>Bachula Yaswanth Babu</li>
                        <li>Anisetty Sai Prajwin</li>
                        <li>Yerla Vinayasree</li>
                    </ul>
                </div>

                <p style="text-align: center; margin-top: 30px; font-size: 14px; color: #777;">
                    Thank you for joining our platform. We are dedicated to providing you with a seamless and efficient logistics experience.
                </p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} QuickLoad. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    # --- END HTML Email Body ---


    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = "🥳 Welcome to QuickLoad! Your Account is Ready."
    
    em.set_content(html_body, subtype='html') 

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending welcome email to {recipient_email}: {e}")
        return False
    


def send_booking_confirmation_email(recipient_email, customer_name, driver_name, pnr, pickup, drop, fare):
    """Sends a professional booking confirmation email to the customer once a driver accepts."""
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #ef4444, #dc2626); padding: 30px; text-align: center; color: #ffffff; }}
            .content {{ padding: 40px; color: #1f2937; }}
            .pnr-badge {{ background-color: #fef2f2; color: #dc2626; padding: 8px 16px; border-radius: 8px; font-weight: 800; display: inline-block; margin-bottom: 20px; border: 1px solid #fee2e2; }}
            .info-grid {{ display: grid; gap: 15px; background-color: #f1f5f9; padding: 20px; border-radius: 12px; margin: 20px 0; }}
            .info-item {{ border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }}
            .info-label {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 700; }}
            .info-value {{ font-size: 16px; font-weight: 600; color: #0f172a; }}
            .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px;">Booking Confirmed!</h1>
            </div>
            <div class="content">
                <p style="font-size: 18px; font-weight: 500;">Hello {customer_name},</p>
                <p>Great news! A professional driver has accepted your transport request. Your vehicle is now being prepared for pickup.</p>
                
                <div class="pnr-badge">BOOKING ID: {pnr}</div>

                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Driver Name</div>
                        <div class="info-value">{driver_name}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Pickup Point</div>
                        <div class="info-value">{pickup}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Drop Location</div>
                        <div class="info-value">{drop}</div>
                    </div>
                    <div class="info-item" style="border:none;">
                        <div class="info-label">Estimated Fare</div>
                        <div class="info-value" style="color: #10b981;">{fare}</div>
                    </div>
                </div>

                <p style="text-align: center; margin-top: 30px;">
                    <a href="{url_for('my_bookings', _external=True)}" style="background-color: #0f172a; color: #ffffff !important; padding: 14px 28px; border-radius: 50px; text-decoration: none; font-weight: 700;">Track My Shipment</a>
                </p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} VaahanSetu QuickLoad. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = f"Shipment Confirmed: {pnr} | VaahanSetu"
    em.set_content(html_body, subtype='html') 

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending confirmation email: {e}")
        return False
    

def send_customer_reset_email(recipient_email, first_name, otp_code):
    """Sends a Customer-specific Password Reset OTP email."""
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Plus Jakarta Sans', Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
            .email-container {{ max-width: 500px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; color: #ffffff; font-weight: 700; letter-spacing: -0.5px; }}
            .content {{ padding: 35px 30px; color: #334155; text-align: center; }}
            .greeting {{ font-size: 18px; font-weight: 600; color: #0f172a; margin-bottom: 10px; }}
            .otp-box {{ background-color: #fef2f2; border: 2px dashed #fca5a5; padding: 15px; border-radius: 12px; margin: 25px auto; display: inline-block; min-width: 150px; }}
            .otp-code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #dc2626; margin: 0; font-family: monospace; }}
            .instructions {{ color: #64748b; font-size: 15px; line-height: 1.6; margin-bottom: 20px; }}
            .btn {{ display: inline-block; background-color: #0f172a; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 10px; }}
            .footer {{ background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>QuickLoad</h1>
            </div>
            <div class="content">
                <div class="greeting">Hi {first_name},</div>
                <p class="instructions">We received a request to reset the password for your QuickLoad customer account. Use the code below to verify your identity.</p>

                <div class="otp-box">
                    <div class="otp-code">{otp_code}</div>
                </div>

                <p class="instructions" style="font-size: 13px;">This code expires in <strong>5 minutes</strong>.<br>If you didn't request this, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} QuickLoad Logistics. All rights reserved.<br>
                Secure System Automated Message.
            </div>
        </div>
    </body>
    </html>
    """

    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = "Reset Your Customer Password"
    em.set_content(html_body, subtype='html')

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending customer reset email: {e}")
        return False
    
def store_and_send_customer_reset_otp(conn, email, first_name):
    """Generates and sends a Password Reset OTP specifically for CUSTOMERS."""
    otp_code = str(generate_otp())
    expires_at = datetime.now() + timedelta(minutes=5)
    
    cursor = conn.cursor()
    try:
        # Clear old OTPs for this email
        cursor.execute("DELETE FROM otp_codes WHERE email = %s", (email,))
        
        # Insert new OTP
        cursor.execute("INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (%s, %s, %s)",
                       (email, otp_code, expires_at))
        conn.commit()
        
        # --- KEY CHANGE: Calls the Customer Email Function ---
        if send_customer_reset_email(email, first_name, otp_code):
            return True, "Reset code sent to your email."
        else:
            return False, "Failed to send email."
    except Error as e:
        print(f"DB Error: {e}")
        return False, "Database error."
    finally:
        cursor.close()


@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    email = session.get('unverified_email')
    first_name = session.get('unverified_first_name')
    if not email:
        return jsonify({'success': False, 'message': 'Verification session expired.'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error.'}), 500

    # Before sending, check if the user is verified to prevent unnecessary operations
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and user[0]:
            return jsonify({'success': False, 'message': 'User is already verified.'})
    except:
        pass # Ignore errors here, continue with resend

    success, msg = store_and_send_otp(conn, email, first_name)
    
    if success:
        return jsonify({'success': True, 'message': msg})
    else:
        return jsonify({'success': False, 'message': msg}), 500
    


# --- CUSTOMER PASSWORD RESET ROUTES (Add to app.py) ---

@app.route('/forgot-password/request-otp', methods=['POST'])
def customer_request_reset_otp():
    data = request.json
    email = data.get('email')
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database error'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Check if CUSTOMER exists
        cursor.execute("SELECT id, first_name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'Email not found in our records.'})
            
        # 2. Use the CUSTOMER-SPECIFIC helper function
        success, msg = store_and_send_customer_reset_otp(conn, email, user['first_name'])
        
        if success:
            return jsonify({'success': True, 'message': 'OTP sent successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send OTP. Try again.'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/forgot-password/verify-otp', methods=['POST'])
def customer_verify_reset_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check OTP in otp_codes table
        cursor.execute("""
            SELECT * FROM otp_codes 
            WHERE email = %s AND otp_code = %s AND expires_at > NOW()
        """, (email, otp))
        
        record = cursor.fetchone()
        
        if record:
            session['reset_verified_email_customer'] = email
            return jsonify({'success': True, 'message': 'OTP Verified'})
        else:
            return jsonify({'success': False, 'message': 'Invalid or expired OTP'})
    finally:
        cursor.close()
        conn.close()

@app.route('/forgot-password/reset', methods=['POST'])
def customer_reset_password_final():
    data = request.json
    email = data.get('email')
    new_password = data.get('password')
    
    # Security check
    if session.get('reset_verified_email_customer') != email:
        return jsonify({'success': False, 'message': 'Unauthorized request. Please verify OTP first.'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Update 'users' table
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()
        
        # Cleanup
        cursor.execute("DELETE FROM otp_codes WHERE email = %s", (email,))
        conn.commit()
        session.pop('reset_verified_email_customer', None)
        
        return jsonify({'success': True, 'message': 'Password reset successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

# --- End of NEW OTP Verification Routes ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file_storage, field_name, identifier):
    if file_storage and allowed_file(file_storage.filename):
        filename = secure_filename(f"{field_name}_{identifier}_{file_storage.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file_storage.save(filepath)
        return filepath.replace(os.sep, '/')
    return None

# --- MODIFIED driver_register route ---
@app.route('/driver_register', methods=['GET', 'POST'])
def driver_register():
    if request.method == 'POST':
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        data = request.form
        files = request.files
        profile_photo_path = save_file(files.get('profilePhoto'), 'profile', data['contactNumber'])
        vehicle_photo_path = save_file(files.get('vehiclePhoto'), 'vehicle_photo', data['contactNumber'])
        driving_license_path = save_file(files.get('drivingLicense'), 'driving_license', data['contactNumber'])
        aadhaar_path = save_file(files.get('aadhaar'), 'aadhaar', data['contactNumber'])
        pan_path = save_file(files.get('pan'), 'pan', data['contactNumber'])
        rc_path = save_file(files.get('rc'), 'rc', data['contactNumber'])
        
        if data.get('hasInsurance') == 'yes':
            insurance_policy_no = data.get('insuranceNumber')
            insurance_expiry_date = data.get('insuranceExpiry')
            # Only try to save the file if the user has insurance
            insurance_path = save_file(files.get('insurance'), 'insurance', data['contactNumber'])
        else:
            insurance_policy_no = None
            insurance_expiry_date = None
            # Ensure the path is None if there is no insurance
            insurance_path = None

        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'danger')
            return redirect(url_for('driver_register'))
        cursor = None
        try:
            cursor = conn.cursor()
            date_str = datetime.now().strftime("%Y%m%d")
            random_str = secrets.token_hex(4).upper()
            application_id = f"VSD-{date_str}-{random_str}"
            sql = """
                INSERT INTO drivers (
                    application_id, full_name, dob, contact_number, email, address, city, pincode,
                    profile_photo_path, vehicle_photo_path, license_number, license_expiry_date,
                    vehicle_type, vehicle_model, vehicle_reg_no, has_insurance, insurance_policy_no, insurance_expiry_date,
                    driving_license_path, aadhaar_path, pan_path, rc_path, insurance_path,
                    acc_holder_name, acc_number, ifsc_code, bank_name, password
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                application_id, data['fullName'], data['dob'], data['contactNumber'], data['email'], data['address'], data['city'], data['pincode'],
                profile_photo_path, vehicle_photo_path, data['licenseNumber'], data['licenseExpiry'],
                data['vehicleType'], data['vehicleModel'], data['vehicleRegNo'], data['hasInsurance'], insurance_policy_no, insurance_expiry_date,
                driving_license_path, aadhaar_path, pan_path, rc_path, insurance_path,
                data['accHolderName'], data['accNumber'], data['ifsc'], data['bankName'], hashed_password
            )
            cursor.execute(sql, values)
            conn.commit()
            flash(f'Registration successful! Your Application ID is {application_id}. Please save it for future reference.', 'success')
            # --- MODIFIED REDIRECTION ON SUCCESS ---
            # Store the application ID in the session for the success page to use
            session['last_application_id'] = application_id
            
            # Redirect to the new success page
            return redirect(url_for('application_success')) 
            # ---------------------------------------
        except Error as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('driver_register'))
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()

    return render_template('driver_registration.html')

# --- NEW ROUTE: QR Code Generator ---
@app.route('/qr_code/<string:app_id>')
def qr_code(app_id):
    """Generates and serves a QR code image for a given Application ID."""
    try:
        # 1. Create QR Code object
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # We encode the Application ID into the QR code
        qr.add_data(f"QuickLoad Application ID: {app_id}")
        qr.make(fit=True)

        # 2. Convert to an image (Pillow Image object)
        img = qr.make_image(fill_color="black", back_color="white")

        # 3. Save the image to an in-memory byte stream
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # 4. Serve the image using send_file
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name=f'qr_{app_id}.png'
        )
    except Exception as e:
        print(f"Error generating QR code for {app_id}: {e}")
        # Return a simple 1x1 transparent GIF as a fallback (optional, but robust)
        # 1x1 transparent GIF data (minimal size)
        transparent_gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
        buffer = BytesIO(transparent_gif)
        return send_file(buffer, mimetype='image/gif', as_attachment=False)

# app.py

# ... (Existing imports: from datetime import datetime, date is already there)

# ... (Existing driver_register function)
# ... (Existing check_status function)

# --- NEW ROUTE TO FETCH APPLICATION DATA FOR PRINT/REVIEW ---
@app.route('/get_application_data/<string:app_id>', methods=['GET'])
def get_application_data(app_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error.'}), 500

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch data from the drivers table
        cursor.execute("SELECT * FROM drivers WHERE application_id = %s", (app_id,))
        app_data = cursor.fetchone()

        if app_data:
            # Convert Date objects to strings for JSON serialization
            for key, value in app_data.items():
                if isinstance(value, date):
                    app_data[key] = value.strftime('%Y-%m-%d')
                
            # --- CORRECTION: Ensure URL generation is correct ---
            profile_photo_url = ''
            if app_data['profile_photo_path']:
                # The path stored is relative to the app root (e.g., static/uploads/filename.jpg)
                # We use url_for('static', filename=...) to generate the correct public URL.
                # We need to strip "static/" from the path before passing it to url_for.
                # Since we stored the full path from app.config['UPLOAD_FOLDER'] (which is static/uploads), we can just pass the path.
                
                # Check if the path contains 'static/' to avoid double static injection
                relative_path = app_data['profile_photo_path'].replace(os.sep, '/')
                if relative_path.startswith('static/'):
                    # Remove 'static/' part
                    filename_in_static = relative_path[len('static/'):]
                    profile_photo_url = url_for('static', filename=filename_in_static)
                else:
                     # This is a fallback if the path was stored incorrectly, but still safer
                    profile_photo_url = url_for('static', filename='uploads/' + os.path.basename(relative_path))
            # --------------------------------------------------
            qr_code_url = url_for('qr_code', app_id=app_id)

            return jsonify({
                # Personal Info
                'applicationId': app_data['application_id'], 
                'fullName': app_data['full_name'],
                'dob': app_data['dob'],
                'contactNumber': app_data['contact_number'],
                'email': app_data['email'],
                'address': app_data['address'],
                'city': app_data['city'],
                'pincode': app_data['pincode'],
                'profilePhoto': profile_photo_url,
                'qrCode': qr_code_url, # NEW KEY
                
                # Vehicle/License
                'licenseNumber': app_data['license_number'],
                'licenseExpiry': app_data['license_expiry_date'],
                'vehicleType': app_data['vehicle_type'],
                'vehicleModel': app_data['vehicle_model'],
                'vehicleRegNo': app_data['vehicle_reg_no'],
                'hasInsurance': app_data['has_insurance'],
                'insuranceNumber': app_data['insurance_policy_no'],

                # Bank Details
                'accHolderName': app_data['acc_holder_name'],
                'accNumber': app_data['acc_number'],
                'ifsc': app_data['ifsc_code'],
                'bankName': app_data['bank_name'],
            })
        else:
            return jsonify({'error': 'Application not found.'}), 404
            
    except Error as e:
        print(f"Database error fetching application data: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()


# --- NEW ROUTE: Application Success Page ---
@app.route('/application/success')
def application_success():
    # Retrieve data from session and clear it
    application_id = session.pop('last_application_id', 'N/A')
    
    # Render the success page, passing the ID
    return render_template('application_success.html', application_id=application_id)

# ... (Existing application_print_preview route is correct)

# Add this new route anywhere in your app.py


@app.route('/application/print')
def application_print_preview():
    return render_template('application_print.html')

@app.route('/check_status', methods=['GET', 'POST'])
def check_status():
    status_data = None
    if request.method == 'POST':
        app_id = request.form.get('application_id', '').strip()
        if not app_id:
            flash('Please enter an Application ID.', 'danger')
            return redirect(url_for('check_status'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'danger')
            return redirect(url_for('check_status'))
        
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT full_name, application_status, registration_date FROM drivers WHERE application_id = %s", (app_id,))
            driver_data = cursor.fetchone()

            if driver_data:
                status_data = driver_data
            else:
                flash('Application ID not found.', 'danger')

        except Error as e:
            flash(f'An error occurred: {e}', 'danger')
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()

    return render_template('check_status.html', status_data=status_data)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password_candidate = request.form.get('password')

        if not username or not password_candidate:
            flash('Please enter both username and password.', 'danger')
            return redirect(url_for('admin_login'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'danger')
            return redirect(url_for('admin_login'))

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Query the 'admins' table for the entered username
            cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
            admin = cursor.fetchone()

            # Verify the admin exists and the hashed password is correct
            if admin and bcrypt.check_password_hash(admin['password'], password_candidate):
                session['admin_logged_in'] = True
                session['admin_username'] = admin['username']
                
                # Update last_login timestamp
                cursor.execute("UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (admin['id'],))
                conn.commit()

                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid credentials. Please try again.', 'danger')
                return redirect(url_for('admin_login'))
        except Error as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('admin_login'))
        finally:
            if cursor:
                cursor.close()
            if conn.is_connected():
                conn.close()

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Summary Cards Data
        cursor.execute("SELECT SUM(total_fare) as revenue FROM trips WHERE status = 'Completed'")
        rev_result = cursor.fetchone()
        revenue = rev_result['revenue'] if rev_result and rev_result['revenue'] else 0

        cursor.execute("SELECT COUNT(*) as count FROM trips")
        total_trips = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM drivers WHERE application_status = 'Approved'")
        active_drivers = cursor.fetchone()['count']

        # --- [FIX START: Count BOTH Drivers and Vehicles] ---
        # Count 1: New Driver Applications
        cursor.execute("SELECT COUNT(*) as count FROM drivers WHERE application_status = 'Submitted'")
        pending_drivers = cursor.fetchone()['count']

        # Count 2: New Vehicle Submissions (from existing drivers)
        cursor.execute("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Submitted'")
        pending_vehicles = cursor.fetchone()['count']
        
        pending_apps_count = pending_drivers + pending_vehicles
        # --- [FIX END] ---

        # 2. Chart Data (Last 7 Days)
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            date_val = datetime.now() - timedelta(days=i)
            date_str = date_val.strftime('%Y-%m-%d')
            display_date = date_val.strftime('%d %b')
            cursor.execute("SELECT COUNT(*) as count FROM trips WHERE DATE(booking_date) = %s", (date_str,))
            count = cursor.fetchone()['count']
            chart_labels.append(display_date)
            chart_data.append(count)

        # 3. Recent Pending List (Combine & Sort)
        recent_apps = []
        
        # Get pending drivers
        cursor.execute("""
            SELECT full_name, vehicle_type, registration_date as sort_date 
            FROM drivers WHERE application_status = 'Submitted' 
            ORDER BY registration_date DESC LIMIT 5
        """)
        recent_apps.extend(cursor.fetchall())

        # Get pending vehicles (Join to get driver name)
        cursor.execute("""
            SELECT d.full_name, v.vehicle_type, v.submission_date as sort_date
            FROM vehicles v JOIN drivers d ON v.driver_id = d.id
            WHERE v.status = 'Submitted'
            ORDER BY v.submission_date DESC LIMIT 5
        """)
        recent_apps.extend(cursor.fetchall())

        # Sort combined list by date (newest first) and take top 5
        recent_apps.sort(key=lambda x: x['sort_date'], reverse=True)
        recent_apps = recent_apps[:5]

        summary = {
            'revenue': "{:,.2f}".format(revenue),
            'total_trips': total_trips,
            'active_drivers': active_drivers,
            'pending_apps': pending_apps_count
        }

        return render_template('admin_dashboard.html', 
                             summary=summary, 
                             chart_labels=chart_labels, 
                             chart_data=chart_data,
                             recent_apps=recent_apps)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/driver-applications')
@admin_required
def admin_driver_applications():
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please ensure the MySQL server is running and the credentials are correct.', 'danger')
        return render_template('admin_driver-applications.html', applications=[], summary={})

    cursor = None
    applications = []
    try:
        cursor = conn.cursor(dictionary=True)

        # Use LEFT JOIN to get all driver applications and their corresponding vehicle data
        cursor.execute("""
            SELECT 
                d.*, 
                v.id AS vehicle_id,
                v.status AS vehicle_status,
                v.submission_date AS vehicle_submission_date,
                v.vehicle_photo_path AS vehicle_photo_path_vehicle,
                v.rc_path AS rc_path_vehicle,
                v.insurance_path AS insurance_path_vehicle,
                v.vehicle_type AS vehicle_type_vehicle,
                v.vehicle_model AS vehicle_model_vehicle,
                v.vehicle_reg_no AS vehicle_reg_no_vehicle,
                v.has_insurance AS has_insurance_vehicle,
                v.insurance_policy_no AS insurance_policy_no_vehicle,
                v.insurance_expiry_date AS insurance_expiry_date_vehicle
            FROM drivers d
            LEFT JOIN vehicles v ON d.id = v.driver_id
            ORDER BY d.registration_date DESC
        """)
        
        raw_applications = cursor.fetchall()

        # Combine the data to present a single view for each driver
        for app in raw_applications:
            combined_app = {
                'id': app['id'],
                'application_id': app['application_id'],
                'full_name': app['full_name'],
                'contact_number': app['contact_number'],
                # FIX: Use the correct vehicle details based on the vehicle_id
                'vehicle_type': app['vehicle_type_vehicle'] if app['vehicle_id'] else app['vehicle_type'],
                'vehicle_model': app['vehicle_model_vehicle'] if app['vehicle_id'] else app['vehicle_model'],
                'vehicle_reg_no': app['vehicle_reg_no_vehicle'] if app['vehicle_id'] else app['vehicle_reg_no'],
                'has_insurance': app['has_insurance_vehicle'] if app['vehicle_id'] else app['has_insurance'],
                'insurance_policy_no': app['insurance_policy_no_vehicle'] if app['vehicle_id'] else app['insurance_policy_no'],
                'insurance_expiry_date': app['insurance_expiry_date_vehicle'] if app['vehicle_id'] else app['insurance_expiry_date'],

                'registration_date': app['vehicle_submission_date'].strftime('%d %b %Y %H:%M') if app['vehicle_submission_date'] else app['registration_date'].strftime('%d %b %Y %H:%M'),
                'application_status': app['application_status'],
                
                # Use vehicle status if it exists and is more recent, otherwise use driver status
                'status': app['vehicle_status'] if app['vehicle_status'] else app['application_status'],
                'type': 'vehicle_submission' if app['vehicle_id'] else 'driver_application',
                'view_id': app['vehicle_id'] if app['vehicle_id'] else app['application_id'],
                
                # Documents & Info - prioritize vehicle table if it exists
                'profile_photo_path': app['profile_photo_path'],
                'vehicle_photo_path': app['vehicle_photo_path_vehicle'] if app['vehicle_photo_path_vehicle'] else app['vehicle_photo_path'],
                'license_number': app['license_number'],
                'license_expiry_date': app['license_expiry_date'],
                'driving_license_path': app['driving_license_path'],
                'aadhaar_path': app['aadhaar_path'],
                'pan_path': app['pan_path'],
                'rc_path': app['rc_path_vehicle'] if app['rc_path_vehicle'] else app['rc_path'],
                'insurance_path': app['insurance_path_vehicle'] if app['insurance_path_vehicle'] else app['insurance_path'],
                'dob': app['dob'],
                'email': app['email'],
                'address': app['address'],
                'city': app['city'],
                'pincode': app['pincode'],
                'acc_holder_name': app['acc_holder_name'],
                'acc_number': app['acc_number'],
                'ifsc_code': app['ifsc_code'],
                'bank_name': app['bank_name'],
            }
            applications.append(combined_app)

        # Calculate summary counts based on the updated logic
        pending_count = sum(1 for app in applications if app['status'] == 'Submitted')
        approved_count = sum(1 for app in applications if app['status'] == 'Approved' or app['status'] == 'Verified')
        rejected_count = sum(1 for app in applications if app['status'] == 'Rejected')
        
        summary_data = {
            'total_pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count,
            'new_vehicles': sum(1 for app in applications if app['type'] == 'vehicle_submission' and app['status'] == 'Submitted'),
        }

        return render_template('admin_driver-applications.html', applications=applications, summary=summary_data)

    except Error as e:
        flash(f'An error occurred while fetching data: {e}', 'danger')
        return render_template('admin_driver-applications.html', applications=[], summary={})
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()
        
# --- MODIFIED APPROVE DRIVER ROUTE ---
@app.route('/admin/approve/<string:app_id>')
@admin_required
def approve_driver(app_id):
    conn = get_db_connection()
    cursor = None
    try:
        # Use dictionary=True to access by column name
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch all required data from the drivers table, including the new vehicle-related columns
        cursor.execute("""
            SELECT 
                id, 
                vehicle_reg_no, 
                vehicle_type, 
                vehicle_model,
                has_insurance,
                insurance_policy_no,
                insurance_expiry_date,
                insurance_path,
                vehicle_photo_path,
                rc_path
            FROM drivers 
            WHERE application_id = %s
        """, (app_id,))
        driver_data = cursor.fetchone()

        if driver_data:
            driver_id = driver_data['id']
            # Get all the values from the fetched data
            vehicle_reg_no = driver_data['vehicle_reg_no']
            vehicle_type = driver_data['vehicle_type']
            vehicle_model = driver_data['vehicle_model']
            has_insurance = driver_data['has_insurance']
            insurance_policy_no = driver_data['insurance_policy_no']
            insurance_expiry_date = driver_data['insurance_expiry_date']
            insurance_path = driver_data['insurance_path']
            vehicle_photo_path = driver_data['vehicle_photo_path']
            rc_path = driver_data['rc_path']

            # Check if a vehicle entry already exists based on registration number
            cursor.execute("SELECT id FROM vehicles WHERE vehicle_reg_no = %s", (vehicle_reg_no,))
            existing_vehicle = cursor.fetchone()

            if existing_vehicle:
                # If vehicle exists, update its status, model, and other details
                sql_update_vehicle = """
                    UPDATE vehicles SET 
                        status = 'Verified', 
                        vehicle_model = %s, 
                        vehicle_type = %s, 
                        driver_id = %s,
                        has_insurance = %s,
                        insurance_policy_no = %s,
                        insurance_expiry_date = %s,
                        insurance_path = %s,
                        vehicle_photo_path = %s,
                        rc_path = %s
                    WHERE vehicle_reg_no = %s
                """
                cursor.execute(sql_update_vehicle, (
                    vehicle_model, 
                    vehicle_type, 
                    driver_id, 
                    has_insurance,
                    insurance_policy_no,
                    insurance_expiry_date,
                    insurance_path,
                    vehicle_photo_path,
                    rc_path,
                    vehicle_reg_no
                ))
            else:
                # If no vehicle entry, insert a new one with all details
                sql_insert_vehicle = """
                    INSERT INTO vehicles (
                        driver_id, 
                        vehicle_reg_no, 
                        vehicle_type, 
                        vehicle_model, 
                        has_insurance, 
                        insurance_policy_no,
                        insurance_expiry_date,
                        insurance_path,
                        vehicle_photo_path,
                        rc_path,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Verified')
                """
                cursor.execute(sql_insert_vehicle, (
                    driver_id, 
                    vehicle_reg_no, 
                    vehicle_type, 
                    vehicle_model, 
                    has_insurance,
                    insurance_policy_no,
                    insurance_expiry_date,
                    insurance_path,
                    vehicle_photo_path,
                    rc_path
                ))

            # 2. Update the driver's application status to 'Approved'
            cursor.execute("UPDATE drivers SET application_status = 'Approved' WHERE application_id = %s", (app_id,))

            conn.commit()
            flash(f'Application {app_id} has been approved.', 'success')
        else:
            flash(f'Application {app_id} not found.', 'danger')

    except Error as e:
        if conn:
            conn.rollback()
        flash(f'Error updating status: {e}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for('admin_driver_applications'))
    
@app.route('/admin/reject/<string:app_id>')
@admin_required
def reject_driver(app_id):
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE drivers SET application_status = 'Rejected' WHERE application_id = %s", (app_id,))
        conn.commit()
        flash(f'Application {app_id} has been rejected.', 'warning')
    except Error as e:
        flash(f'Error updating status: {e}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn.is_connected():
            conn.close()
    return redirect(url_for('admin_driver_applications'))

@app.route('/admin/delete/<string:app_id>')
@admin_required
def delete_driver(app_id):
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_driver_applications'))
    
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # First, get the file paths before deleting the record
        cursor.execute("SELECT profile_photo_path, driving_license_path, aadhaar_path, pan_path, rc_path, insurance_path FROM drivers WHERE application_id = %s", (app_id,))
        driver_files = cursor.fetchone()

        # Delete the record from the database
        cursor.execute("DELETE FROM drivers WHERE application_id = %s", (app_id,))
        conn.commit()

        # If the record was found and deleted, now delete the associated files
        if driver_files:
            for file_path in driver_files.values():
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")

        flash(f'Application {app_id} has been permanently deleted.', 'success')

    except Error as e:
        flash(f'Error deleting application: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()
        
    return redirect(url_for('admin_driver_applications'))


# --- NEW ROUTE TO DELETE A VEHICLE ---
@app.route('/admin/delete_vehicle/<int:vehicle_id>')
@admin_required
def admin_delete_vehicle(vehicle_id):
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_driver_applications'))
    
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # First, get the file paths before deleting the record
        cursor.execute("SELECT vehicle_photo_path, rc_path, insurance_path FROM vehicles WHERE id = %s", (vehicle_id,))
        vehicle_files = cursor.fetchone()

        # Delete the record from the database
        cursor.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        conn.commit()
        
        # If the record was found and deleted, now delete the associated files
        if vehicle_files:
            for file_path in vehicle_files.values():
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")

        flash(f'Vehicle with ID {vehicle_id} has been permanently deleted.', 'success')

    except Error as e:
        flash(f'Error deleting vehicle: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()
        
    return redirect(url_for('admin_driver_applications'))

# --- NEW ROUTE TO APPROVE A VEHICLE ---
@app.route('/admin/approve_vehicle/<int:vehicle_id>')
@admin_required
def approve_vehicle(vehicle_id):
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE vehicles SET status = 'Verified' WHERE id = %s", (vehicle_id,))
        conn.commit()
        flash(f'Vehicle with ID {vehicle_id} has been verified.', 'success')
    except Error as e:
        if conn:
            conn.rollback()
        flash(f'Error verifying vehicle: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()
    return redirect(url_for('admin_driver_applications'))

# --- NEW ROUTE TO REJECT A VEHICLE ---
@app.route('/admin/reject_vehicle/<int:vehicle_id>')
@admin_required
def reject_vehicle(vehicle_id):
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE vehicles SET status = 'Rejected' WHERE id = %s", (vehicle_id,))
        conn.commit()
        flash(f'Vehicle with ID {vehicle_id} has been rejected.', 'warning')
    except Error as e:
        if conn:
            conn.rollback()
        flash(f'Error rejecting vehicle: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()
    return redirect(url_for('admin_driver_applications'))

# --- NEW MY VEHICLES ROUTE ---
@app.route('/driver/my-vehicles')
@driver_required
def my_vehicles():
    """
    Fetches all vehicles for the logged-in driver and renders them on the 'My Vehicles' page.
    Vehicles are separated into 'Verified' and 'Pending' lists.
    """
    driver_email = session.get('driver_email')
    if not driver_email:
        flash('Could not identify driver. Please log in again.', 'danger')
        return redirect(url_for('driver_login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'danger')
        return redirect(url_for('driver_dashboard'))

    cursor = None
    verified_vehicles = []
    pending_vehicles = []
    rejected_vehicles = []
    try:
        cursor = conn.cursor(dictionary=True)
        # First, get the driver's ID from their email
        cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()

        if driver:
            driver_id = driver['id']
            # Now, fetch all vehicles associated with that driver ID
            cursor.execute("SELECT * FROM vehicles WHERE driver_id = %s", (driver_id,))
            vehicles = cursor.fetchall()
            
            # Separate vehicles by status
            for vehicle in vehicles:
                if isinstance(vehicle.get('insurance_expiry_date'), date):
                    vehicle['insurance_expiry_date'] = vehicle['insurance_expiry_date'].strftime('%d %b %Y')
                    
                if vehicle['status'] == 'Verified':
                    verified_vehicles.append(vehicle)
                elif vehicle['status'] == 'Submitted':
                    pending_vehicles.append(vehicle)
                elif vehicle['status'] == 'Rejected': # Add this condition
                    rejected_vehicles.append(vehicle)
        else:
            flash('Driver profile not found.', 'danger')

    except Error as e:
        flash(f'An error occurred: {e}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn.is_connected():
            conn.close()

    return render_template('my_vehicles.html', verified_vehicles=verified_vehicles, pending_vehicles=pending_vehicles, rejected_vehicles=rejected_vehicles)


@app.route('/driver/add_vehicle', methods=['POST'])
@driver_required
def add_vehicle():
    """
    Handles the form submission for adding a new vehicle.
    Saves file uploads and creates a new entry in the vehicles table.
    """
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    driver_email = session.get('driver_email')
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error.'})
        
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
        driver_data = cursor.fetchone()
        
        if not driver_data:
            return jsonify({'success': False, 'message': 'Driver not found.'})
            
        driver_id = driver_data['id']
        data = request.form
        files = request.files

        # Using a unique identifier for filenames to avoid clashes
        identifier = f"{driver_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        vehicle_photo_path = save_file(files.get('vehiclePhoto'), 'vehicle_photo', identifier)
        rc_path = save_file(files.get('rc'), 'rc', identifier)
        
        insurance_path = None
        insurance_policy_no = None
        insurance_expiry_date = None
        if data.get('hasInsurance') == 'yes':
            insurance_path = save_file(files.get('insurance'), 'insurance', identifier)
            insurance_policy_no = data.get('insuranceNumber')
            insurance_expiry_date = data.get('insuranceExpiry')

        sql = """
            INSERT INTO vehicles (
                driver_id, vehicle_model, vehicle_reg_no, vehicle_type, has_insurance, 
                insurance_policy_no, insurance_expiry_date, insurance_path, vehicle_photo_path, rc_path, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Submitted')
        """
        values = (
            driver_id, data['vehicleModel'], data['vehicleRegNo'], data['vehicleType'], data['hasInsurance'],
            insurance_policy_no, insurance_expiry_date, insurance_path, vehicle_photo_path, rc_path
        )
        
        cursor.execute(sql, values)
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Vehicle submitted for review successfully.'})

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Error adding new vehicle: {e}")
        return jsonify({'success': False, 'message': f'A database error occurred: {e}'})
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()

# --- NEW: Edit Vehicle Route ---
@app.route('/driver/edit_vehicle/<int:vehicle_id>', methods=['POST'])
@driver_required
def edit_vehicle(vehicle_id):
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error.'})

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        data = request.form
        files = request.files

        # Fetch existing vehicle data to get old file paths for deletion
        cursor.execute("SELECT * FROM vehicles WHERE id = %s", (vehicle_id,))
        existing_vehicle = cursor.fetchone()
        
        if not existing_vehicle:
            return jsonify({'success': False, 'message': 'Vehicle not found.'})

        # Process new file uploads and keep old paths if not updated
        vehicle_photo_path = existing_vehicle['vehicle_photo_path']
        rc_path = existing_vehicle['rc_path']
        
        new_vehicle_photo = files.get('vehiclePhoto')
        if new_vehicle_photo and new_vehicle_photo.filename != '':
            vehicle_photo_path = save_file(new_vehicle_photo, 'vehicle_photo', str(vehicle_id))
            if existing_vehicle['vehicle_photo_path'] and os.path.exists(existing_vehicle['vehicle_photo_path']):
                os.remove(existing_vehicle['vehicle_photo_path'])
        
        new_rc = files.get('rc')
        if new_rc and new_rc.filename != '':
            rc_path = save_file(new_rc, 'rc', str(vehicle_id))
            if existing_vehicle['rc_path'] and os.path.exists(existing_vehicle['rc_path']):
                os.remove(existing_vehicle['rc_path'])

        insurance_path = existing_vehicle['insurance_path']
        insurance_policy_no = data.get('insuranceNumber')
        insurance_expiry_date = data.get('insuranceExpiry')
        
        if data.get('hasInsurance') == 'yes':
            new_insurance_file = files.get('insurance')
            if new_insurance_file and new_insurance_file.filename != '':
                insurance_path = save_file(new_insurance_file, 'insurance', str(vehicle_id))
            
            # If the old insurance path exists and is being replaced, delete the old file
            if insurance_path != existing_vehicle['insurance_path'] and existing_vehicle['insurance_path'] and os.path.exists(existing_vehicle['insurance_path']):
                os.remove(existing_vehicle['insurance_path'])
        else:
            insurance_path = None
            insurance_policy_no = None
            insurance_expiry_date = None
            # If insurance is removed, delete the old insurance file
            if existing_vehicle['insurance_path'] and os.path.exists(existing_vehicle['insurance_path']):
                os.remove(existing_vehicle['insurance_path'])
        
        # SQL query to update the vehicle details
        sql = """
            UPDATE vehicles SET 
                vehicle_model = %s, vehicle_reg_no = %s, vehicle_type = %s, has_insurance = %s, 
                insurance_policy_no = %s, insurance_expiry_date = %s, insurance_path = %s, 
                vehicle_photo_path = %s, rc_path = %s, status = 'Submitted'
            WHERE id = %s
        """
        values = (
            existing_vehicle['vehicle_model'], # Not editable
            existing_vehicle['vehicle_reg_no'], # Not editable
            existing_vehicle['vehicle_type'], # Not editable
            data['hasInsurance'],
            insurance_policy_no,
            insurance_expiry_date,
            insurance_path,
            vehicle_photo_path,
            rc_path,
            vehicle_id
        )
        
        cursor.execute(sql, values)
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Vehicle updated and submitted for re-verification successfully.'})

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Error editing vehicle: {e}")
        return jsonify({'success': False, 'message': f'A database error occurred: {e}'})
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()

# --- NEW: Delete Vehicle Route ---
@app.route('/driver/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@driver_required
def driver_delete_vehicle(vehicle_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error.'})
    
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch file paths before deleting the record
        cursor.execute("SELECT vehicle_photo_path, rc_path, insurance_path FROM vehicles WHERE id = %s", (vehicle_id,))
        vehicle_files = cursor.fetchone()

        # Delete the record from the database
        cursor.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        conn.commit()
        
        # Delete associated files if they exist
        if vehicle_files:
            for file_path in vehicle_files.values():
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")
        
        return jsonify({'success': True, 'message': 'Vehicle removed successfully.'})

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Error deleting vehicle: {e}")
        return jsonify({'success': False, 'message': f'A database error occurred: {e}'})
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()

@app.route('/driver/trip-requests')
@driver_required
def trip_requests():
    """Fetches pending trips, excluding those previously declined by the current driver."""
    driver_email = session.get('driver_email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Select trips that are 'Pending' AND have no entry in 'declined_trips' for this driver
    query = """
        SELECT t.* FROM trips t
        WHERE t.status = 'Pending'
        AND t.id NOT IN (
            SELECT dt.trip_id FROM declined_trips dt
            JOIN drivers d ON dt.driver_id = d.id
            WHERE d.email = %s
        )
        ORDER BY t.booking_date DESC
    """
    cursor.execute(query, (driver_email,))
    pending_trips = cursor.fetchall()
    
    conn.close()
    return render_template('trip_requests.html', pending_trips=pending_trips)

@app.route('/driver/my-trips')
@driver_required
def my_trips():
    driver_email = session.get('driver_email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch driver ID
    cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
    driver = cursor.fetchone()
    
    trips = []
    if driver:
        # Fetch all trips for this driver, ordered by newest first
        cursor.execute("SELECT * FROM trips WHERE driver_id = %s ORDER BY booking_date DESC", (driver['id'],))
        trips = cursor.fetchall()
        
    return render_template('my_trips.html', trips=trips)


@app.route('/driver/my-earnings')
@driver_required
def my_earnings():
    filter_type = request.args.get('filter', 'week')  # Default to 'week'
    driver_email = session.get('driver_email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Get Driver ID
        cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()
        
        if not driver:
            return redirect(url_for('driver_logout'))

        # 2. Determine Start Date based on Filter
        today = date.today()
        if filter_type == 'month':
            # Start of the current month
            start_date = today.replace(day=1)
        else:
            # Start of the current week (Monday)
            start_date = today - timedelta(days=today.weekday())

        # 3. Fetch filtered completed trips
        cursor.execute("""
            SELECT total_fare, toll_tax, fare, booking_date, pnr_number, pickup_location, drop_location 
            FROM trips 
            WHERE driver_id = %s AND status = 'Completed' AND booking_date >= %s
            ORDER BY booking_date DESC
        """, (driver['id'], start_date))
        completed_trips = cursor.fetchall()

        # 4. Calculate Summary Stats
        total_earnings = sum(float(t['total_fare'] or 0) for t in completed_trips)
        total_trips = len(completed_trips)
        avg_per_trip = total_earnings / total_trips if total_trips > 0 else 0

        # 5. Prepare Weekly Chart Data (Always shows last 7 days for visual consistency)
        weekly_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_total = sum(float(t['total_fare'] or 0) for t in completed_trips 
                            if t['booking_date'].date() == day)
            weekly_data.append({
                'day': day.strftime('%a'),
                'amount': day_total,
                'height': min(100, (day_total / 5000) * 100) if day_total > 0 else 5
            })

        return render_template('my_earnings.html', 
                               trips=completed_trips,
                               total_earnings=total_earnings,
                               total_trips=total_trips,
                               avg_per_trip=avg_per_trip,
                               weekly_data=weekly_data,
                               filter_type=filter_type) # Pass filter_type to template
    finally:
        cursor.close()
        conn.close()

# --- HELPER FUNCTION FOR PUBLIC URLS (Add this outside any route, near save_file) ---
# This helper function ensures the 'static/static/' error is fixed by removing the 'static/' prefix
# before passing the path to url_for('static', ...).
def get_public_url(path):
    """Safely converts a stored file path (e.g., static/uploads/file.jpg) to a public Flask URL."""
    if not path:
        return None
    
    # Normalize path separators for consistency
    relative_path = path.replace(os.sep, '/')
    
    # If the path starts with the folder name defined in UPLOAD_FOLDER (e.g., 'static/uploads'), 
    # we need to extract the path relative to the 'static' folder (e.g., 'uploads/file.jpg').
    if relative_path.startswith('static/'):
        # Remove 'static/' part
        filename_in_static = relative_path[len('static/'):] 
        return url_for('static', filename=filename_in_static)
    
    # Fallback for paths that might have been stored differently (less common)
    return url_for('static', filename=relative_path)

# --- NEW HELPER FUNCTION FOR DISTANCE API CALL (OSRM REPLACEMENT) ---
def get_osrm_distance(lat1, lon1, lat2, lon2):
    """
    Calls the public OSRM API to get driving distance and duration.
    Note: OSRM uses (longitude, latitude) order for coordinates in URLs.
    """
    try:
        # Format: /route/v1/driving/start_lon,start_lat;end_lon,end_lat
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 'Ok' and data.get('routes'):
                route = data['routes'][0]
                # OSRM returns distance in meters and duration in seconds
                distance_km = route['distance'] / 1000
                duration_mins = route['duration'] / 60
                return distance_km, duration_mins
    except Exception as e:
        print(f"Error calling OSRM API: {e}")
    
    return None, None


# --- HELPER FUNCTION TO MAP DB DATA TO FRONTEND FORMAT (MODIFIED) ---
# --- HELPER: Map DB Data to Frontend Format ---
def map_vehicle_details(vehicle_db_data, total_distance_km):
    v_type = vehicle_db_data['vehicle_type']
    
    # Configuration for different vehicle types
    details = {
        '3-wheeler': {"capacity": "500 kg", "base_fare": 250, "rate_per_km": 15, "eta_factor": 1.2, "rating": 4.8, "image": 'images/3-wheeler.png'},
        'mini-truck': {"capacity": "1 Ton", "base_fare": 350, "rate_per_km": 20, "eta_factor": 1.1, "rating": 4.7, "image": 'images/mini truck.png'},
        'pickup': {"capacity": "1.5 Ton", "base_fare": 500, "rate_per_km": 25, "eta_factor": 1.05, "rating": 4.5, "image": 'images/pickup.png'},
        'tempo': {"capacity": "2 Ton", "base_fare": 700, "rate_per_km": 30, "eta_factor": 1.0, "rating": 4.6, "image": 'images/tempo.png'},
        'truck': {"capacity": "2+ Ton", "base_fare": 1000, "rate_per_km": 40, "eta_factor": 0.95, "rating": 4.4, "image": 'images/truck.png'},
    }
    
    # Default to mini-truck if type not found
    default_details = details.get(v_type, details['mini-truck'])
    
    # 1. Calculate Price: Base Fare + (Distance * Rate)
    calculated_price_num = default_details['base_fare'] + (total_distance_km * default_details['rate_per_km'])
    calculated_price_str = f"₹ {calculated_price_num:,.0f}" # Formats as ₹ 1,250

    # 2. Calculate ETA: (Distance / Speed) + Buffer
    # Assuming avg speed 25km/h for city logistics
    mock_duration_mins = int((total_distance_km / 25) * 60 * default_details['eta_factor']) + 10 
    
    # 3. Determine Image URL
    # Use uploaded photo if available, otherwise use default static asset
    image_url = get_public_url(vehicle_db_data['vehicle_photo_path']) 
    if not image_url:
        image_url = url_for('static', filename=default_details['image'])

    return {
        "id": vehicle_db_data['id'],
        "type": f"{vehicle_db_data['vehicle_model']} ({v_type.title()})",
        "capacity": default_details['capacity'],
        "price": calculated_price_str, 
        "price_raw": calculated_price_num,
        "eta": f"{mock_duration_mins} mins",
        "rating": default_details['rating'], # Will be overwritten by real rating
        "image": image_url,
        "driver_name": vehicle_db_data['full_name'],
        "vehicle_reg_no": vehicle_db_data['vehicle_reg_no']
    }


# ... (Existing driver dashboard, home, and logout routes)

@app.route('/driver/my-profile')
@driver_required
def my_profile():
    """Fetches the logged-in driver's complete profile, aggregate rating, and primary vehicle details."""
    driver_email = session.get('driver_email')
    
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'danger')
        return redirect(url_for('driver_dashboard'))
    
    cursor = None
    profile_data = None
    vehicle_summary = None

    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Fetch Driver Profile Details
        cursor.execute("SELECT * FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()

        if driver:
            # --- NEW: Calculate Aggregate Rating from Trips Table ---
            cursor.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(rating) as total_reviews 
                FROM trips 
                WHERE driver_id = %s AND rating IS NOT NULL
            """, (driver['id'],))
            rating_data = cursor.fetchone()
            
            # Format to 1 decimal place (e.g., 4.5) or default to 0.0 if no reviews exist
            driver['overall_rating'] = round(float(rating_data['avg_rating']), 1) if rating_data['avg_rating'] else 0.0
            driver['review_count'] = rating_data['total_reviews']
            # ----------------------------------------------------------------------

            # Format dates for display
            if driver.get('dob') and isinstance(driver['dob'], date):
                driver['dob'] = driver['dob'].strftime('%d %b %Y')
            
            if driver.get('license_expiry_date') and isinstance(driver['license_expiry_date'], date):
                driver['license_expiry_date'] = driver['license_expiry_date'].strftime('%Y-%m-%d')
                
            if driver.get('insurance_expiry_date') and isinstance(driver['insurance_expiry_date'], date):
                driver['insurance_expiry_date'] = driver['insurance_expiry_date'].strftime('%d %b %Y')

            # Public URL conversion
            driver['profile_photo_url'] = get_public_url(driver.get('profile_photo_path')) or url_for('static', filename='images/default_profile.png')
            
            driver['driving_license_url'] = get_public_url(driver.get('driving_license_path'))
            driver['aadhaar_url'] = get_public_url(driver.get('aadhaar_path'))
            driver['pan_url'] = get_public_url(driver.get('pan_path'))
            driver['rc_url'] = get_public_url(driver.get('rc_path'))
            driver['insurance_url'] = get_public_url(driver.get('insurance_path'))
            
            profile_data = driver
            
            # 2. Fetch Primary Vehicle Summary
            cursor.execute("""
                SELECT vehicle_type, vehicle_model, vehicle_reg_no 
                FROM vehicles 
                WHERE driver_id = %s AND status = 'Verified'
                ORDER BY submission_date DESC LIMIT 1
            """, (driver['id'],))
            vehicle_summary = cursor.fetchone()

            if not vehicle_summary:
                vehicle_summary = {
                    'vehicle_type': driver['vehicle_type'],
                    'vehicle_model': driver['vehicle_model'],
                    'vehicle_reg_no': driver['vehicle_reg_no']
                }

    except Error as e:
        flash(f'An error occurred while loading profile: {e}', 'danger')
        print(f"Error loading profile: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('my_profile.html', profile=profile_data, vehicle=vehicle_summary)


# --- FILE HELPER FUNCTION (Crucial for update_profile to work) ---
def update_document(file_storage, field_name, identifier, old_path):
    """
    Saves a new file if provided, and returns the new path.
    If a new file is saved, the old file at old_path is deleted.
    If no new file is provided, the old path is retained.
    """
    # 1. Check if a new, valid file was provided
    if file_storage and file_storage.filename != '' and allowed_file(file_storage.filename):
        # Generate a unique filename using a combination of field, identifier, and timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = secure_filename(f"{field_name}_{identifier}_{timestamp}_{file_storage.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            # 2. Save the new file
            file_storage.save(filepath)
            
            # 3. Delete old file if it exists and is different from the new one
            if old_path and os.path.exists(old_path) and os.path.abspath(old_path) != os.path.abspath(filepath):
                # We need to ensure we don't accidentally delete the default image path
                if 'default_profile.png' not in old_path.lower(): 
                    os.remove(old_path)
            
            # 4. Return the new path for the database
            return filepath.replace(os.sep, '/')
        except Exception as e:
            print(f"Error saving new file or deleting old file: {e}")
            return old_path # Fallback to old path on save error
            
    # If no new file was submitted, return the existing path
    return old_path


# --- UPDATE PROFILE ROUTE (As provided, now fully contextualized) ---
@app.route('/driver/update-profile', methods=['POST'])
@driver_required
def update_profile():
    """Handles the update of all editable fields and document uploads on the driver profile."""
    driver_email = session.get('driver_email')
    data = request.form
    files = request.files
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error.'})
        
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True) 

        # 1. Fetch current driver data (ID and ALL old file paths, INCLUDING profile_photo_path)
        cursor.execute("SELECT id, profile_photo_path, driving_license_path, aadhaar_path, pan_path FROM drivers WHERE email = %s", (driver_email,))
        driver_current = cursor.fetchone()
        
        if not driver_current:
            return jsonify({'success': False, 'message': 'Driver profile not found.'})

        driver_id = driver_current['id']
        identifier = str(driver_id) 

        # --- UNIQUENESS CHECKS (unchanged) ---
        cursor.execute("SELECT id FROM drivers WHERE contact_number = %s AND email != %s", 
                       (data['contactNumber'], driver_email))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Contact number is already registered by another driver.'})
            
        cursor.execute("SELECT id FROM drivers WHERE license_number = %s AND email != %s", 
                       (data['licenseNumber'], driver_email))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'License number is already registered by another driver.'})

        # --- DOCUMENT & EXPIRY DATE HANDLING ---
        
        # Process profile photo upload (key is 'profilePhotoFile' from HTML)
        new_profile_photo_path = update_document(
            files.get('profilePhotoFile'), 
            'profile_photo', 
            identifier, 
            driver_current.get('profile_photo_path')
        )
        

        # Process other documents
        new_dl_path = update_document(files.get('drivingLicenseFile'), 'driving_license', identifier, driver_current['driving_license_path'])
        new_aadhaar_path = update_document(files.get('aadhaarFile'), 'aadhaar', identifier, driver_current['aadhaar_path'])
        new_pan_path = update_document(files.get('panFile'), 'pan', identifier, driver_current['pan_path'])

        license_expiry_date = data.get('licenseExpiryDate') 
        if license_expiry_date == '':
            license_expiry_date = None
            
        # --- PREPARE SQL UPDATE STATEMENT (ALL editable fields) ---
        # MODIFIED: Added profile_photo_path to the UPDATE list
        sql = """
            UPDATE drivers SET 
                full_name = %s, 
                contact_number = %s, 
                address = %s, 
                city = %s, 
                pincode = %s,
                license_number = %s,
                license_expiry_date = %s,
                acc_holder_name = %s,
                acc_number = %s,
                ifsc_code = %s,
                bank_name = %s,
                profile_photo_path = %s,
                driving_license_path = %s,
                aadhaar_path = %s,
                pan_path = %s
            WHERE email = %s
        """
        values = (
            data['fullName'],
            data['contactNumber'],
            data['address'],
            data['city'],
            data['pincode'],
            data['licenseNumber'],
            license_expiry_date, 
            data['accHolderName'],
            data['accNumber'],
            data['ifscCode'],
            data['bankName'],
            new_profile_photo_path, 
            new_dl_path,
            new_aadhaar_path,
            new_pan_path,
            driver_email
        )
        
        cursor.execute(sql, values)
        conn.commit()
        
        session['driver_name'] = data.get('fullName', session.get('driver_name'))
        
        return jsonify({'success': True, 'message': 'Profile and documents updated successfully.'})

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Error updating profile: {e}")
        return jsonify({'success': False, 'message': f'A database error occurred: {e}'})
    finally:
        if cursor: cursor.close()
        if conn.is_connected(): conn.close()



@app.route('/driver/support')
@driver_required
def support():
    return render_template('support.html')

@app.route('/admin/view_application/<app_type>/<view_id>')
@admin_required
def admin_view_application(app_type, view_id):
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_driver_applications'))
    
    cursor = None
    application_data = None
    try:
        cursor = conn.cursor(dictionary=True)
        if app_type == 'driver_application':
            cursor.execute("SELECT * FROM drivers WHERE application_id = %s", (view_id,))
            application_data = cursor.fetchone()
        elif app_type == 'vehicle_submission':
            cursor.execute("""
                SELECT v.*, d.full_name, d.email, d.contact_number, d.profile_photo_path
                FROM vehicles v
                JOIN drivers d ON v.driver_id = d.id
                WHERE v.id = %s
            """, (view_id,))
            application_data = cursor.fetchone()

        if not application_data:
            flash(f'Application {view_id} not found.', 'danger')
            return redirect(url_for('admin_driver_applications'))

        # Format dates for display
        for key, value in application_data.items():
            if isinstance(value, date):
                application_data[key] = value.strftime('%d %b %Y')

    except Error as e:
        flash(f'An error occurred while fetching application details: {e}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn.is_connected():
            conn.close()

    return render_template('view_application.html', app_data=application_data, app_type=app_type)


@app.route('/driver/login', methods=['GET', 'POST'])
def driver_login():
    if 'driver_logged_in' in session:
        return redirect(url_for('driver_dashboard')) 

    if request.method == 'POST':
        email = request.form.get('email')
        password_candidate = request.form.get('password')

        if not email or not password_candidate:
            flash('Please enter both email and password.', 'danger')
            return redirect(url_for('driver_login'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'danger')
            return redirect(url_for('driver_login'))

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Find the driver by email first
            cursor.execute("SELECT * FROM drivers WHERE email = %s", (email,))
            driver = cursor.fetchone()

            # Now check if the driver exists and if the password and application status are correct
            if driver:
                if bcrypt.check_password_hash(driver['password'], password_candidate):
                    if driver['application_status'] == 'Approved':
                        session['driver_logged_in'] = True
                        session['driver_email'] = driver['email']
                        session['driver_name'] = driver['full_name']
                        session['driver_id'] = driver['id']
                        
                        flash('Login successful!', 'success')
                        return redirect(url_for('driver_dashboard'))
                    else:
                        flash('Your application has not yet been approved.', 'danger')
                        return redirect(url_for('driver_login'))
                else:
                    flash('Invalid credentials. Please try again.', 'danger')
                    return redirect(url_for('driver_login'))
            else:
                flash('Invalid credentials or application not yet approved.', 'danger')
                return redirect(url_for('driver_login'))
        except Error as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('driver_login'))
        finally:
            if cursor:cursor.close()
            if conn.is_connected(): conn.close()

    return render_template('driver_login.html')

# Driver Dashboard
@app.route('/driver/dashboard')
@driver_required
def driver_dashboard():
    driver_email = session.get('driver_email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Get Driver ID
        cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()
        
        if not driver:
            return redirect(url_for('driver_logout'))
        

        cursor.execute("""
            SELECT total_fare FROM trips 
            WHERE driver_id = %s AND status = 'Completed'
        """, (driver['id'],))
        completed_trips = cursor.fetchall()
        
        # Sum the total_fare column directly (handles None/Null automatically)
        total_earnings = sum(trip['total_fare'] for trip in completed_trips if trip['total_fare'])


        # 3. Fetch Initial Pending Trips (not declined)
        cursor.execute("""
            SELECT * FROM trips 
            WHERE status = 'Pending' 
            AND id NOT IN (SELECT trip_id FROM declined_trips WHERE driver_id = %s)
            ORDER BY booking_date DESC LIMIT 5
        """, (driver['id'],))
        live_requests = cursor.fetchall()

        return render_template('driver_dashboard.html', 
                               driver_name=session['driver_name'],
                               earnings=f"₹ {total_earnings:,}",
                               completed_count=len(completed_trips),
                               pending_trips=live_requests)
    finally:
        cursor.close()
        conn.close()

# Inside app.py

@app.route('/home')
def home():
    if 'logged_in' in session:
        # Construct full name safely
        full_name = f"{session.get('first_name', '')} {session.get('last_name', '')}".strip()
        return render_template('home.html', name=full_name)
    else:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # Remove only customer-specific keys
    session.pop('logged_in', None)
    session.pop('email', None)
    session.pop('first_name', None)
    session.pop('user_id', None)
    
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/admin_logout')
def admin_logout():
    # Remove only admin-specific keys
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/driver_logout')
def driver_logout():
    # Remove only driver-specific keys
    session.pop('driver_logged_in', None)
    session.pop('driver_email', None)
    session.pop('driver_name', None)
    session.pop('driver_id', None)
    
    flash('You have been logged out.', 'success')
    return redirect(url_for('driver_login'))


# [In app.py] Replace your my_bookings function

@app.route('/my-bookings')
def my_bookings():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    user_email = session.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # FETCH LOGIC: Get trips where I am the 'booked_by' owner OR the 'customer_email' contact
    # This ensures bookings made FOR you and bookings made BY you both appear.
    cursor.execute("""
        SELECT t.*, d.full_name as driver_name, d.contact_number as driver_phone, d.vehicle_reg_no
        FROM trips t
        LEFT JOIN drivers d ON t.driver_id = d.id
        WHERE t.booked_by = %s OR t.customer_email = %s
        ORDER BY t.booking_date DESC
    """, (user_email, user_email))
    
    bookings = cursor.fetchall()
    
    conn.close()
    return render_template('my_bookings.html', bookings=bookings, name=session.get('first_name'))


@app.route('/track-live/<int:trip_id>')
def track_live(trip_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch live trip data including vehicle and driver details
    cursor.execute("""
        SELECT t.*, d.full_name as driver_name, d.vehicle_reg_no, d.contact_number as driver_phone
        FROM trips t
        JOIN drivers d ON t.driver_id = d.id
        WHERE t.id = %s
    """, (trip_id,))
    trip = cursor.fetchone()
    conn.close()
    
    if not trip:
        flash("Tracking information not available.", "danger")
        return redirect(url_for('my_bookings'))
        
    return render_template('customer_track_live.html', trip=trip)

@app.route('/customer-profile')
def customer_profile():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    email = session.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch customer details
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        flash("User profile not found.", "danger")
        return redirect(url_for('home'))
        
    return render_template('customer_profile.html', user=user)


@app.route('/update-customer-profile', methods=['POST'])
def update_customer_profile():
    if 'logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.json
    email = session.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update first_name, last_name, age, gender AND phone_number
        sql = """
            UPDATE users 
            SET first_name = %s, last_name = %s, age = %s, gender = %s, phone_number = %s 
            WHERE email = %s
        """
        cursor.execute(sql, (
            data.get('firstName'), 
            data.get('lastName'), 
            data.get('age'), 
            data.get('gender'), 
            data.get('phoneNumber'),  # NEW: Save phone number
            email
        ))
        conn.commit()
        
        # Update session name just in case
        session['first_name'] = data.get('firstName')
        
        return jsonify({'success': True, 'message': 'Profile updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


# --- UPDATED ROUTE: Handle Booking Form Submission and Redirect ---
@app.route('/process_booking', methods=['POST'])
def process_booking():
    data = request.json
    
    # 1. Extract Data
    pickup_coords = (float(data['pickupLat']), float(data['pickupLng']))
    drop_coords = (float(data['dropLat']), float(data['dropLng']))
    vehicle_type = data['vehicleType']
    weight = float(data['loadWeight'])
    
    # 2. Calculate Distance using Geodesic (More accurate than simple math)
    trip_distance = geodesic(pickup_coords, drop_coords).km
    
    # 3. CALL THE AI PRICING ENGINE
    pricing_result = ai_engine.calculate_dynamic_price(
        distance_km=trip_distance,
        weight_kg=weight,
        vehicle_type=vehicle_type
    )
    
    # 4. STORE IN SESSION (To show on the next page)
    session['booking_data'] = {
        **data,
        "trip_distance": pricing_result['distance_km'],
        "estimated_price": pricing_result['estimated_price'],
        "surge_applied": pricing_result['surge_applied']
    }
    
    # 5. Redirect (As you had before)
    return jsonify({
        'success': True,
        'redirect_url': url_for('select_vehicle_page') 
        # Note: You need to create this page to show the price!
    })

@app.route('/select_vehicle')
def select_vehicle_page():
    booking_data = session.get('booking_data')
    if not booking_data:
        return redirect(url_for('home'))
    
    return render_template('booking_summary.html', booking=booking_data)

# --- NEW ROUTE: Available Vehicles Page (MODIFIED FOR DB FETCH & API CALL) ---
@app.route('/available_vehicles')
def available_vehicles():
    booking_data = session.get('booking_data')
    if not booking_data:
        flash('Please fill out the booking form first.', 'warning')
        return redirect(url_for('home'))
        
    requested_type = booking_data.get('vehicleType') # e.g., 'mini-truck'
    
    # 1. Retrieve the AI Estimated Price from the previous step
    # This ensures the price matches what the user just saw on the Summary page
    ai_price_baseline = float(booking_data.get('estimated_price', 0))

    # 2. Distance Calculation (Keep existing logic)
    total_distance_km = booking_data.get('tripDistanceKm')
    if not total_distance_km:
        p_lat = booking_data.get('pickupLat')
        p_lng = booking_data.get('pickupLng')
        d_lat = booking_data.get('dropLat')
        d_lng = booking_data.get('dropLng')
        
        if p_lat and p_lng and d_lat and d_lng:
            dist, dur = get_osrm_distance(p_lat, p_lng, d_lat, d_lng)
            total_distance_km = dist if dist else 15.0
        else:
            total_distance_km = 15.0

    total_distance_km = float(total_distance_km)
    
    # Update session for the UI
    booking_data['real_distance'] = round(total_distance_km, 2)
    booking_data['real_duration'] = int((total_distance_km / 25) * 60)

    conn = get_db_connection()
    vehicle_options = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 3. REAL DATABASE QUERY
            sql = """
                SELECT 
                    v.id, 
                    v.vehicle_model, 
                    v.vehicle_type,
                    v.vehicle_reg_no,
                    v.vehicle_photo_path,
                    d.id as driver_id,
                    d.full_name,
                    COALESCE(ROUND(AVG(t.rating), 1), 4.5) as avg_rating,
                    COUNT(t.rating) as review_count
                FROM vehicles v
                JOIN drivers d ON v.driver_id = d.id
                LEFT JOIN trips t ON d.id = t.driver_id
                WHERE v.status = 'Verified' AND v.vehicle_type = %s
                GROUP BY v.id, d.id
            """
            cursor.execute(sql, (requested_type,))
            db_vehicles = cursor.fetchall()
            
            # 4. Format Data & Apply AI Price
            import random 

            for vehicle in db_vehicles:
                # Get basic details (ETA, Capacity, etc.)
                formatted_vehicle = map_vehicle_details(vehicle, total_distance_km)
                
                # --- CRITICAL FIX: OVERRIDE PRICE WITH AI QUOTE ---
                # We add a small random variance (-2% to +2%) to make drivers look competitive
                # independent of the hardcoded logic in map_vehicle_details
                if ai_price_baseline > 0:
                    #variance = random.uniform(0.98, 1.02)
                    driver_specific_price = round(ai_price_baseline) # Use exact price
                    
                    formatted_vehicle['price_raw'] = driver_specific_price
                    formatted_vehicle['price'] = f"₹ {driver_specific_price:,.0f}"

                # Overwrite with Real DB Rating
                formatted_vehicle['rating'] = float(vehicle['avg_rating'])
                formatted_vehicle['review_count'] = vehicle['review_count']
                
                vehicle_options.append(formatted_vehicle)
                
        except Error as e:
            print(f"Error fetching vehicles: {e}")
            flash('Error retrieving available vehicles.', 'danger')
        finally:
            cursor.close()
            conn.close()

    #if not vehicle_options:
        #flash(f'No verified {requested_type}s found nearby. Please try a different vehicle type.', 'info')
        #return redirect(url_for('home'))

    return render_template('available_vehicles.html', booking=booking_data, vehicles=vehicle_options)


# [In app.py] Replace your confirm_final_booking function

@app.route('/confirm_final_booking', methods=['POST'])
def confirm_final_booking():
    booking_data = session.get('booking_data')
    if not booking_data:
        return jsonify({'success': False, 'message': 'No booking data found'}), 400

    incoming_data = request.json
    base_price = incoming_data.get('price', '₹ 0')
    booked_vehicle_name = incoming_data.get('vehicle_type_text', 'General Goods Vehicle')

    toll_pref = booking_data.get('tollPreference')
    final_fare = f"{base_price} (Tolls extra at Plaza)" if toll_pref == 'pay_at_plaza' else f"{base_price} + Extra Tolls"

    customer_name = booking_data.get('fullName', 'QuickLoad User')
    
    # --- KEY CHANGE: Identify the Booker ---
    # We use the session email as the 'owner' of the booking
    booked_by_email = session.get('email') 
    # The email in the form is the 'contact' for OTPs/Receipts
    contact_email = booking_data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Insert 'booked_by' AND 'customer_email' separately
        sql = """
            INSERT INTO trips (
                booked_by, customer_name, customer_email, customer_phone, 
                customer_gender, customer_age, vehicle_type_booked,
                pickup_location, pickup_lat, pickup_lng, 
                drop_location, drop_lat, drop_lng, fare, load_weight, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
        """
        values = (
            booked_by_email,                  # The logged-in user (Owner)
            customer_name,
            contact_email,                    # The form email (Contact Person)
            booking_data.get('mobile'),
            booking_data.get('gender'),
            booking_data.get('age'),
            booked_vehicle_name,
            booking_data.get('pickupLocation'),
            booking_data.get('pickupLat'),
            booking_data.get('pickupLng'),
            booking_data.get('dropLocation'),
            booking_data.get('dropLat'),
            booking_data.get('dropLng'),
            final_fare,
            booking_data.get('loadWeight')
        )
        cursor.execute(sql, values)
        trip_id = cursor.lastrowid
        conn.commit()

        # Update Socket payload
        trip_payload = {
            'trip_id': trip_id,
            'customer_name': customer_name,
            'customer_phone': booking_data.get('mobile'),
            'fare': final_fare,
            'pickup': booking_data.get('pickupLocation'),
            'drop': booking_data.get('dropLocation'),
            'weight': booking_data.get('loadWeight'),
            'vehicle': booked_vehicle_name
        }
        socketio.emit('new_trip_request', trip_payload)
        
        return jsonify({'success': True, 'message': 'Request saved and sent!'})
    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({'success': False, 'message': 'Could not save trip'}), 500
    finally:
        cursor.close()
        conn.close()

# Function to send Start-Trip OTP to Customer
def send_trip_start_otp(recipient_email, customer_name, otp_code, pnr):
    html_body = f"""
    <html>
    <body style="font-family: 'Inter', sans-serif; color: #1f2937;">
        <div style="max-width: 500px; margin: auto; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden;">
            <div style="background: #0f172a; padding: 20px; text-align: center; color: white;">
                <h2 style="margin:0;">Security Verification</h2>
            </div>
            <div style="padding: 30px; text-align: center;">
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>Your driver is ready to start trip <strong>{pnr}</strong>. Please share the OTP below with the driver only after they have successfully picked up your goods.</p>
                <div style="background: #f1f5f9; padding: 20px; border-radius: 12px; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: 800; letter-spacing: 5px; color: #dc2626;">{otp_code}</span>
                </div>
                <p style="font-size: 12px; color: #64748b;">If you did not authorize this trip, please contact support immediately.</p>
            </div>
        </div>
    </body>
    </html>
    """
    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = f"OTP to Start Shipment: {pnr}"
    em.set_content(html_body, subtype='html')
    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())

# Updated Route
@app.route('/request_start_otp/<int:trip_id>', methods=['POST'])
@driver_required
def request_start_otp(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
        trip = cursor.fetchone()
        
        otp = secrets.randbelow(9000) + 1000  # Generate 4-digit OTP
        session[f'trip_otp_{trip_id}'] = str(otp) # Store in session for verification
        
        send_trip_start_otp(trip['customer_email'], trip['customer_name'], otp, trip['pnr_number'])
        return jsonify({'success': True, 'message': 'OTP sent to customer email.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/verify_start_otp', methods=['POST'])
@driver_required
def verify_start_otp():
    data = request.json
    trip_id = data.get('trip_id')
    entered_otp = data.get('otp')
    
    if session.get(f'trip_otp_{trip_id}') == entered_otp:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE trips SET status = 'Ongoing' WHERE id = %s", (trip_id,))
        conn.commit()
        cursor.close()
        conn.close()
        session.pop(f'trip_otp_{trip_id}', None)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid OTP. Please try again.'})

def send_trip_completion_email(recipient_email, customer_name, pnr, base_fare, toll_tax, total_fare, payment_method):
    """Sends a professional trip completion summary and receipt to the customer."""
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0; }}
            .header {{ background: #0f172a; padding: 30px; text-align: center; color: #ffffff; }}
            .content {{ padding: 40px; color: #1f2937; }}
            .receipt-card {{ background-color: #f1f5f9; padding: 25px; border-radius: 12px; margin: 20px 0; }}
            .price-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
            .total-row {{ display: flex; justify-content: space-between; padding: 15px 0; font-weight: 800; font-size: 18px; color: #dc2626; }}
            .payment-badge {{ background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 50px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
            .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px;">Trip Completed Successfully!</h1>
            </div>
            <div class="content">
                <p style="font-size: 18px; font-weight: 600;">Hello {customer_name},</p>
                <p>Thank you for choosing <strong>VaahanSetu QuickLoad</strong>. Your shipment for Booking ID <strong>{pnr}</strong> has been delivered.</p>
                
                <div class="receipt-card">
                    <h3 style="margin-top:0; border-bottom: 2px solid #0f172a; padding-bottom: 5px;">Payment Summary</h3>
                    <div class="price-row">
                        <span>Base Trip Fare</span>
                        <span>₹ {base_fare:,.2f}</span>
                    </div>
                    <div class="price-row">
                        <span>Toll & Extra Charges</span>
                        <span>₹ {toll_tax:,.2f}</span>
                    </div>
                    <div class="total-row">
                        <span>Grand Total</span>
                        <span>₹ {total_fare:,.2f}</span>
                    </div>
                    <div style="margin-top:15px; display:flex; align-items:center; gap:10px;">
                        <span style="font-size: 14px; font-weight: 600;">Payment Method:</span>
                        <span class="payment-badge">{payment_method}</span>
                    </div>
                </div>

                <div style="text-align: center; margin-top: 30px; padding: 20px; border: 1px dashed #cbd5e1; border-radius: 12px;">
                    <p style="font-style: italic; color: #475569; margin-bottom: 10px;">"We hope you had a seamless logistics experience with us!"</p>
                    <p style="font-weight: 700; color: #0f172a;">Thanks for using our service. We look forward to moving your next load soon!</p>
                </div>

                <p style="text-align: center; margin-top: 30px;">
                    <a href="{url_for('my_bookings', _external=True)}" style="background-color: #dc2626; color: #ffffff !important; padding: 14px 30px; border-radius: 12px; text-decoration: none; font-weight: 700; display: inline-block;">View Trip History</a>
                </p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} VaahanSetu. Reliable Goods Transport.
            </div>
        </div>
    </body>
    </html>
    """
    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = f"Trip Summary: {pnr} | Delivered & Settled"
    em.set_content(html_body, subtype='html') 

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, recipient_email, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending completion email: {e}")
        return False
@app.route('/accept_trip', methods=['POST'])
@driver_required
def accept_trip():
    data = request.json
    driver_email = session.get('driver_email')
    trip_id = data.get('trip_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id, full_name FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()
        
        # Fetch trip details including customer email
        cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
        trip = cursor.fetchone()
        
        if driver and trip:
            date_str = datetime.now().strftime("%Y%m%d")
            random_code = secrets.token_hex(3).upper()
            pnr = f"QL-{date_str}-{random_code}"
            
            # Update database
            sql = "UPDATE trips SET driver_id = %s, status = 'Accepted', pnr_number = %s WHERE id = %s"
            cursor.execute(sql, (driver['id'], pnr, trip_id))
            conn.commit()
            
            # TRIGGER REAL-TIME EMAIL
            send_booking_confirmation_email(
                recipient_email=trip['customer_email'],
                customer_name=trip['customer_name'],
                driver_name=driver['full_name'],
                pnr=pnr,
                pickup=trip['pickup_location'].split(',')[0],
                drop=trip['drop_location'].split(',')[0],
                fare=trip['fare']
            )
            
            return jsonify({'success': True, 'pnr': pnr})
            
        return jsonify({'success': False, 'message': 'Trip acceptance failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


@app.route('/start_trip/<int:trip_id>', methods=['POST'])
@driver_required
def start_trip(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Update trip status to 'Ongoing'
        cursor.execute("UPDATE trips SET status = 'Ongoing' WHERE id = %s", (trip_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


@app.route('/driver/live-trip/<int:trip_id>')
@driver_required
def live_trip(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Fetch trip details and join with drivers to get vehicle info if needed
    cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
    trip = cursor.fetchone()
    conn.close()
    
    if not trip:
        flash("Trip not found", "danger")
        return redirect(url_for('my_trips'))
        
    return render_template('live_trip.html', trip=trip)


@app.route('/driver/navigate-to-pickup/<int:trip_id>')
@driver_required
def navigate_to_pickup(trip_id):
    """Provides a dedicated map for the driver to reach the pickup location."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch trip and customer details for the navigation view
    cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
    trip = cursor.fetchone()
    conn.close()
    
    if not trip:
        flash("Trip details not found", "danger")
        return redirect(url_for('my_trips'))
        
    return render_template('navigate_to_pickup.html', trip=trip)


@app.route('/complete_trip/<int:trip_id>', methods=['POST'])
@driver_required
def complete_trip(trip_id):
    data = request.json
    try:
        toll_tax = float(data.get('toll_tax', 0) if data.get('toll_tax') else 0)
    except ValueError:
        toll_tax = 0.0
    payment_method = data.get('payment_method', 'Cash')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch trip and customer details
        cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
        trip = cursor.fetchone()
        
        if not trip:
            return jsonify({'success': False, 'message': 'Trip not found'})

        # 2. Extract numeric base fare
        import re
        base_fare_clean = re.sub(r'[^\d.]', '', trip['fare'].split('(')[0])
        base_fare_num = float(base_fare_clean) if base_fare_clean else 0.0
        total_sum = base_fare_num + toll_tax

        # 3. Update Trip Status in Database
        sql = """
            UPDATE trips 
            SET status = 'Completed', 
                toll_tax = %s, 
                payment_method = %s,
                total_fare = %s 
            WHERE id = %s
        """
        cursor.execute(sql, (toll_tax, payment_method, total_sum, trip_id))
        conn.commit()

        # 4. Trigger Real-time Completion Email
        send_trip_completion_email(
            recipient_email=trip['customer_email'],
            customer_name=trip['customer_name'],
            pnr=trip['pnr_number'],
            base_fare=base_fare_num,
            toll_tax=toll_tax,
            total_fare=total_sum,
            payment_method=payment_method
        )

        return jsonify({'success': True})
    except Exception as e:
        print(f"Completion Error: {e}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/driver/view-receipt/<int:trip_id>')
@driver_required
def view_receipt(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # This automatically includes customer_email, customer_phone, etc.
    cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
    trip = cursor.fetchone()
    
    if trip:
        import re
        base_fare_clean = re.sub(r'[^\d.]', '', trip['fare'].split('+')[0].split('(')[0])
        trip['base_numeric'] = float(base_fare_clean) if base_fare_clean else 0.0
        trip['toll_numeric'] = float(trip['toll_tax'] or 0.0)
        trip['grand_total'] = float(trip['total_fare']) if trip.get('total_fare') else (trip['base_numeric'] + trip['toll_numeric'])

        # Keep fetching driver info for vehicle registration
        cursor.execute("SELECT full_name, vehicle_reg_no FROM drivers WHERE id = %s", (trip['driver_id'],))
        driver = cursor.fetchone()
    
    conn.close()
    
    if not trip:
        flash("Receipt not found", "danger")
        return redirect(url_for('my_trips'))
        
    return render_template('receipt_print.html', trip=trip, driver=driver)


@app.route('/decline_trip/<int:trip_id>', methods=['POST'])
@driver_required
def decline_trip(trip_id):
    """Records a driver's decision to decline a specific trip request."""
    driver_email = session.get('driver_email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get current driver ID
        cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()
        
        if driver:
            # Save the decline mapping to the database
            cursor.execute(
                "INSERT INTO declined_trips (trip_id, driver_id) VALUES (%s, %s)",
                (trip_id, driver['id'])
            )
            conn.commit()
            return jsonify({'success': True})
            
        return jsonify({'success': False, 'message': 'Driver not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


@app.route('/driver/export_earnings_csv')
@driver_required
def export_earnings_csv():
    driver_email = session.get('driver_email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Get Driver ID
        cursor.execute("SELECT id FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()
        
        # 2. Fetch only 'Completed' trips for this driver
        cursor.execute("""
            SELECT pnr_number, booking_date, pickup_location, drop_location, 
                   fare, toll_tax, total_fare, payment_method 
            FROM trips WHERE driver_id = %s AND status = 'Completed'
            ORDER BY booking_date DESC
        """, (driver['id'],))
        trips = cursor.fetchall()

        # 3. Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Booking ID", "Date", "Pickup", "Drop", "Base Fare", "Toll Tax", "Total Payout", "Payment Method"])

        for trip in trips:
            # Clean fare string to remove "+ Extra Tolls" etc.
            base_fare = trip['fare'].split('+')[0].split('(')[0].replace('₹', '').replace(',', '').strip()
            
            writer.writerow([
                trip['pnr_number'],
                trip['booking_date'].strftime('%Y-%m-%d'),
                trip['pickup_location'].split(',')[0],
                trip['drop_location'].split(',')[0],
                base_fare,
                trip['toll_tax'],
                trip['total_fare'],
                trip['payment_method']
            ])

        response = make_response(output.getvalue())
        filename = f"Earnings_Report_{date.today()}.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-type"] = "text/csv"
        return response

    except Exception as e:
        return f"Error: {e}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/help-support')
def help_support():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('customer_support.html', name=session.get('first_name'))


@app.route('/api/search-tracking/<string:tracking_id>')
def search_tracking(tracking_id):
    if 'logged_in' not in session:
        return jsonify({'success': False, 'message': 'Please login to track your shipment.'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if the PNR exists and is currently active
    cursor.execute("SELECT id, status FROM trips WHERE pnr_number = %s", (tracking_id,))
    trip = cursor.fetchone()
    conn.close()
    
    if trip:
        # Prevent tracking for completed trips
        if trip['status'] == 'Completed':
            return jsonify({
                'success': False, 
                'message': 'This shipment has been delivered. Please check My Bookings for the receipt.'
            })
        return jsonify({'success': True, 'trip_id': trip['id']})
    else:
        return jsonify({'success': False, 'message': 'Booking ID not found. Please verify the PNR.'})
    

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    if 'logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.json
    trip_id = data.get('trip_id')
    rating = data.get('rating')
    comments = data.get('comments')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE trips SET rating = %s, feedback = %s WHERE id = %s", 
                       (rating, comments, trip_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Thank you for your feedback!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

# [In app.py] Replace the manage_drivers function

# [In app.py] Replace the existing manage_drivers function with this comprehensive version

# [In app.py] Replace the manage_drivers function

@app.route('/admin/manage-drivers')
@admin_required
def manage_drivers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch all drivers (Approved & Suspended)
        cursor.execute("""
            SELECT * FROM drivers 
            WHERE application_status IN ('Approved', 'Suspended') 
            ORDER BY full_name ASC
        """)
        drivers_raw = cursor.fetchall()
        
        drivers_data = []
        for d in drivers_raw:
            # 2. Fetch Vehicles
            cursor.execute("SELECT * FROM vehicles WHERE driver_id = %s", (d['id'],))
            vehicles = cursor.fetchall()
            
            # 3. Fetch Trips (Accepted, Ongoing, Completed)
            cursor.execute("""
                SELECT * FROM trips 
                WHERE driver_id = %s 
                ORDER BY 
                    CASE 
                        WHEN status = 'Ongoing' THEN 1
                        WHEN status = 'Accepted' THEN 2
                        ELSE 3 
                    END,
                    booking_date DESC
            """, (d['id'],))
            trips = cursor.fetchall()

            # 4. Format Data (Dates & Images)
            if isinstance(d.get('dob'), date): 
                d['dob'] = d['dob'].strftime('%d %b %Y')
            if isinstance(d.get('license_expiry_date'), date): 
                d['license_expiry_date'] = d['license_expiry_date'].strftime('%Y-%m-%d')
            
            d['profile_photo_url'] = get_public_url(d.get('profile_photo_path'))
            d['dl_url'] = get_public_url(d.get('driving_license_path'))
            d['aadhaar_url'] = get_public_url(d.get('aadhaar_path'))
            d['pan_url'] = get_public_url(d.get('pan_path'))
            d['insurance_url'] = get_public_url(d.get('insurance_path')) 
            d['rc_url'] = get_public_url(d.get('rc_path'))

            # Process Vehicles
            processed_vehicles = []
            for v in vehicles:
                v['photo_url'] = get_public_url(v.get('vehicle_photo_path'))
                v['rc_url'] = get_public_url(v.get('rc_path'))
                v['ins_url'] = get_public_url(v.get('insurance_path'))
                processed_vehicles.append(v)
            d['vehicles'] = processed_vehicles

            # Process Trips
            processed_trips = []
            for t in trips:
                if isinstance(t.get('booking_date'), (date, datetime)):
                    t['booking_date'] = t['booking_date'].strftime('%d %b %Y, %I:%M %p')
                processed_trips.append(t)
            d['trips'] = processed_trips
            
            # Calculate Trip Counts for Table
            d['completed_count'] = sum(1 for t in trips if t['status'] == 'Completed')
            d['active_trip'] = any(t['status'] in ['Accepted', 'Ongoing'] for t in trips)

            drivers_data.append(d)

        summary = {
            'total_active': sum(1 for d in drivers_data if d['application_status'] == 'Approved'),
            'suspended': sum(1 for d in drivers_data if d['application_status'] == 'Suspended'),
            'on_duty': sum(1 for d in drivers_data if d['active_trip'])
        }
        
        return render_template('admin_manage-drivers.html', drivers=drivers_data, summary=summary)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/suspend_driver/<string:app_id>')
@admin_required
def suspend_driver(app_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update status to Suspended
        cursor.execute("UPDATE drivers SET application_status = 'Suspended' WHERE application_id = %s", (app_id,))
        conn.commit()
        flash(f'Driver {app_id} has been suspended.', 'warning')
    except Error as e:
        flash(f'Error suspending driver: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_drivers'))

@app.route('/admin/activate_driver/<string:app_id>')
@admin_required
def activate_driver(app_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update status back to Approved
        cursor.execute("UPDATE drivers SET application_status = 'Approved' WHERE application_id = %s", (app_id,))
        conn.commit()
        flash(f'Driver {app_id} account re-activated.', 'success')
    except Error as e:
        flash(f'Error activating driver: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_drivers'))

@app.route('/admin/suspend_vehicle/<int:vehicle_id>')
@admin_required
def suspend_vehicle(vehicle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Suspend specific vehicle
        cursor.execute("UPDATE vehicles SET status = 'Suspended' WHERE id = %s", (vehicle_id,))
        conn.commit()
        flash('Vehicle suspended successfully.', 'warning')
    except Error as e:
        flash(f'Error suspending vehicle: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_drivers'))

@app.route('/admin/activate_vehicle/<int:vehicle_id>')
@admin_required
def activate_vehicle(vehicle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Re-verify specific vehicle
        cursor.execute("UPDATE vehicles SET status = 'Verified' WHERE id = %s", (vehicle_id,))
        conn.commit()
        flash('Vehicle re-activated successfully.', 'success')
    except Error as e:
        flash(f'Error activating vehicle: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_drivers'))

# --- [ADD THESE ROUTES TO app.py] ---

# [In app.py] Replace the manage_users function

# [In app.py] Replace the manage_users function

@app.route('/admin/manage-users')
@admin_required
def manage_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        # 2. Fetch all users
        cursor.execute("SELECT * FROM users") 
        users_raw = cursor.fetchall()
        
        users_data = []
        for u in users_raw:
            if 'full_name' not in u:
                first = u.get('first_name', '')
                last = u.get('last_name', '')
                u['full_name'] = f"{first} {last}".strip() or u.get('username', 'Valued Customer')

            # 3. Fetch COMPLETE Booking History (Joined with Drivers)
            cursor.execute("""
                SELECT t.*, 
                       d.full_name AS driver_name, 
                       d.contact_number AS driver_phone, 
                       d.vehicle_reg_no AS driver_vehicle
                FROM trips t
                LEFT JOIN drivers d ON t.driver_id = d.id
                WHERE t.booked_by = %s OR t.customer_email = %s 
                ORDER BY t.booking_date DESC
            """, (u.get('email'), u.get('email')))
            bookings = cursor.fetchall()
            
            # Format Dates & Null Checks
            for b in bookings:
                if isinstance(b.get('booking_date'), (date, datetime)):
                    b['booking_date'] = b['booking_date'].strftime('%d %b %Y, %I:%M %p')
                
                # Ensure driver fields are not None for display
                if not b['driver_name']:
                    b['driver_name'] = "Not Assigned"
                    b['driver_phone'] = "N/A"
                    b['driver_vehicle'] = "N/A"

            u['bookings'] = bookings
            u['total_trips'] = len(bookings)
            u['profile_photo_url'] = get_public_url(u.get('profile_photo_path')) if u.get('profile_photo_path') else None
            
            users_data.append(u)

        # Sort by name
        users_data.sort(key=lambda x: x['full_name'].lower())

        summary = {
            'total_users': len(users_data),
            'active': sum(1 for u in users_data if u.get('status', 'Active') == 'Active'),
            'suspended': sum(1 for u in users_data if u.get('status') == 'Suspended')
        }
        
        return render_template('admin_manage-users.html', users=users_data, summary=summary)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/suspend_user/<int:user_id>')
@admin_required
def suspend_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = 'Suspended' WHERE id = %s", (user_id,))
        conn.commit()
        flash('User account suspended.', 'warning')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/admin/activate_user/<int:user_id>')
@admin_required
def activate_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = 'Active' WHERE id = %s", (user_id,))
        conn.commit()
        flash('User account re-activated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        flash('User permanently deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/admin/manage-trips')
@admin_required
def manage_trips():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # [FIX] Removed the join with 'users' table that was overwriting the booking data.
        # We now rely strictly on t.customer_name and t.customer_phone from the 'trips' table
        # which are saved directly from the booking form.
        query = """
            SELECT 
                t.*,
                d.full_name AS driver_name,
                d.contact_number AS driver_phone,
                d.vehicle_reg_no
            FROM trips t
            LEFT JOIN drivers d ON t.driver_id = d.id
            ORDER BY t.booking_date DESC
        """
        cursor.execute(query)
        trips_raw = cursor.fetchall()
        
        trips_data = []
        for t in trips_raw:
            # Format Date
            if isinstance(t.get('booking_date'), (date, datetime)):
                t['formatted_date'] = t['booking_date'].strftime('%d %b %Y, %I:%M %p')
            
            # Handle Empty Driver
            if not t['driver_name']:
                t['driver_name'] = "Not Assigned"
                t['driver_phone'] = "-"
                t['vehicle_reg_no'] = "-"
            
            # Fallback for old records if customer_name is missing
            if not t['customer_name']:
                t['customer_name'] = "Guest User"
                
            trips_data.append(t)

        summary = {
            'total': len(trips_data),
            'ongoing': sum(1 for t in trips_data if t['status'] == 'Ongoing'),
            'completed': sum(1 for t in trips_data if t['status'] == 'Completed'),
            'cancelled': sum(1 for t in trips_data if t['status'] == 'Cancelled')
        }

        return render_template('admin_manage-trips.html', trips=trips_data, summary=summary)
    finally:
        cursor.close()
        conn.close()

# Optional: Route to Cancel a Trip by Admin
@app.route('/admin/cancel_trip/<int:trip_id>')
@admin_required
def cancel_trip_admin(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE trips SET status = 'Cancelled' WHERE id = %s", (trip_id,))
        conn.commit()
        flash(f'Trip #{trip_id} has been cancelled by Admin.', 'warning')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_trips'))

@app.route('/admin/profile')
@admin_required
def admin_profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch current admin details
        cursor.execute("SELECT * FROM admins WHERE username = %s", (session['admin_username'],))
        current_admin = cursor.fetchone()
        
        # --- SAFETY CHECK: If admin was deleted manually, Force Logout ---
        if not current_admin:
            session.clear()
            flash("User not found. Please login again.", "danger")
            return redirect(url_for('admin_login'))
        # -------------------------------------------------------------

        # Fetch all admins list
        cursor.execute("SELECT id, username, email, created_at FROM admins ORDER BY created_at DESC")
        all_admins = cursor.fetchall()
        
        # Format dates
        for a in all_admins:
            if isinstance(a.get('created_at'), (date, datetime)):
                a['created_at'] = a['created_at'].strftime('%d %b %Y')

        return render_template('admin_profile.html', admin=current_admin, all_admins=all_admins)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/add_new_admin', methods=['POST'])
@admin_required
def add_new_admin():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO admins (username, email, password) VALUES (%s, %s, %s)", 
                           (username, email, hashed_password))
            conn.commit()
            flash('New admin added successfully.', 'success')
        except Exception as e:
            flash('Error: Username likely exists already.', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return redirect(url_for('admin_profile'))

@app.route('/admin/change_password', methods=['POST'])
@admin_required
def admin_change_password():
    current_pass = request.form['current_password']
    new_pass = request.form['new_password']
    confirm_pass = request.form['confirm_password']
    
    if new_pass != confirm_pass:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('admin_profile'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM admins WHERE username = %s", (session['admin_username'],))
        admin = cursor.fetchone()
        
        if admin and bcrypt.check_password_hash(admin['password'], current_pass):
            hashed_new = bcrypt.generate_password_hash(new_pass).decode('utf-8')
            cursor.execute("UPDATE admins SET password = %s WHERE id = %s", (hashed_new, admin['id']))
            conn.commit()
            flash('Password updated successfully.', 'success')
        else:
            flash('Incorrect current password.', 'danger')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_profile'))


@app.route('/cancel_trip_customer/<int:trip_id>')
def cancel_trip_customer(trip_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_email = session.get('email')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Securely update status only if:
        # 1. The trip belongs to the logged-in user (booked_by OR customer_email)
        # 2. The status is 'Pending' OR 'Accepted' (Ongoing/Completed cannot be cancelled here)
        query = """
            UPDATE trips
            SET status = 'Cancelled'
            WHERE id = %s
            AND (booked_by = %s OR customer_email = %s)
            AND status IN ('Pending', 'Accepted')
        """
        cursor.execute(query, (trip_id, user_email, user_email))

        if cursor.rowcount > 0:
            conn.commit()
            flash('Trip request cancelled successfully.', 'success')
        else:
            flash('Unable to cancel trip. It may have already started or been completed.', 'danger')

    except Exception as e:
        flash(f'Error cancelling trip: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('my_bookings'))

@app.route('/cancel_trip_driver/<int:trip_id>')
def cancel_trip_driver(trip_id):
    if 'driver_logged_in' not in session:
        return redirect(url_for('driver_login'))

    # This will now work because of Step 1
    driver_id = session.get('driver_id')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch the trip
        cursor.execute("SELECT id, driver_id, status FROM trips WHERE id = %s", (trip_id,))
        trip = cursor.fetchone()

        if not trip:
            flash('Trip not found.', 'danger')
        
        # 2. Verify Ownership
        # We convert both to strings to ensure '5' equals 5
        elif str(trip['driver_id']) != str(driver_id):
            flash('Permission denied: This trip is not assigned to you.', 'danger')

        # 3. Verify Status
        elif trip['status'] != 'Accepted':
            flash(f'Cannot cancel trip. Current status is {trip["status"]}.', 'danger')

        # 4. Success
        else:
            cursor.execute("UPDATE trips SET status = 'Cancelled' WHERE id = %s", (trip_id,))
            conn.commit()
            flash('Trip cancelled successfully.', 'success')

    except Exception as e:
        flash(f'Error cancelling trip: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('my_trips'))

# --- ADD THIS TO app.py ---

@app.route('/driver/change_password', methods=['POST'])
@driver_required
def driver_change_password():
    driver_email = session.get('driver_email')
    data = request.json # We will send data via AJAX (JSON)
    
    current_pass = data.get('currentPassword')
    new_pass = data.get('newPassword')
    confirm_pass = data.get('confirmPassword')
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch current driver
        cursor.execute("SELECT id, password FROM drivers WHERE email = %s", (driver_email,))
        driver = cursor.fetchone()
        
        if not driver:
            return jsonify({'success': False, 'message': 'Driver not found'})
            
        # 2. Verify Old Password
        if not bcrypt.check_password_hash(driver['password'], current_pass):
            return jsonify({'success': False, 'message': 'Incorrect current password'})
            
        # 3. Validate New Password (Backend fallback)
        if new_pass != confirm_pass:
            return jsonify({'success': False, 'message': 'New passwords do not match'})
            
        if len(new_pass) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'})

        # 4. Update Password
        hashed_new_pass = bcrypt.generate_password_hash(new_pass).decode('utf-8')
        
        cursor.execute("UPDATE drivers SET password = %s WHERE id = %s", (hashed_new_pass, driver['id']))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Password updated successfully!'})

    except Exception as e:
        print(f"Error changing password: {e}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})
    finally:
        cursor.close()
        conn.close()

# --- DRIVER PASSWORD RESET ROUTES ---

@app.route('/driver/forgot-password/request-otp', methods=['POST'])
def driver_request_reset_otp():
    data = request.json
    email = data.get('email')
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database error'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Check if driver exists
        cursor.execute("SELECT id, full_name FROM drivers WHERE email = %s", (email,))
        driver = cursor.fetchone()
        
        if not driver:
            return jsonify({'success': False, 'message': 'Email not found in driver records.'})
            
        # 2. Use the NEW Reset OTP function
        # This triggers the "Lock Icon" email template
        success, msg = store_and_send_reset_otp(conn, email, driver['full_name'])
        
        if success:
            return jsonify({'success': True, 'message': msg})
        else:
            return jsonify({'success': False, 'message': msg})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/driver/forgot-password/verify-otp', methods=['POST'])
def driver_verify_reset_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check OTP in otp_codes table
        cursor.execute("""
            SELECT * FROM otp_codes 
            WHERE email = %s AND otp_code = %s AND expires_at > NOW()
        """, (email, otp))
        
        record = cursor.fetchone()
        
        if record:
            # OTP is valid. 
            # IMPORTANT: We verify them here but don't delete the OTP yet, 
            # or we set a session flag to allow the next step.
            session['reset_verified_email'] = email
            return jsonify({'success': True, 'message': 'OTP Verified'})
        else:
            return jsonify({'success': False, 'message': 'Invalid or expired OTP'})
    finally:
        cursor.close()
        conn.close()

@app.route('/driver/forgot-password/reset', methods=['POST'])
def driver_reset_password_final():
    data = request.json
    email = data.get('email')
    new_password = data.get('password')
    
    # Security check: Ensure this email actually passed the verification step in this session
    if session.get('reset_verified_email') != email:
        return jsonify({'success': False, 'message': 'Unauthorized request. Please verify OTP first.'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        cursor.execute("UPDATE drivers SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()
        
        # Clean up
        cursor.execute("DELETE FROM otp_codes WHERE email = %s", (email,))
        conn.commit()
        session.pop('reset_verified_email', None)
        
        return jsonify({'success': True, 'message': 'Password reset successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

# --- ADD THIS TO app.py ---

@app.route('/change-customer-password', methods=['POST'])
def change_customer_password():
    if 'logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.json
    email = session.get('email')
    
    current_pass = data.get('currentPassword')
    new_pass = data.get('newPassword')
    confirm_pass = data.get('confirmPassword')

    # Basic Validation
    if not current_pass or not new_pass:
        return jsonify({'success': False, 'message': 'Please fill in all fields.'})
    
    if new_pass != confirm_pass:
        return jsonify({'success': False, 'message': 'New passwords do not match.'})
        
    if len(new_pass) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'})

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch current user password
        cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'success': False, 'message': 'User not found.'})

        # 2. Verify Old Password
        if not bcrypt.check_password_hash(user['password'], current_pass):
            return jsonify({'success': False, 'message': 'Incorrect current password.'})

        # 3. Hash New Password and Update
        hashed_new_pass = bcrypt.generate_password_hash(new_pass).decode('utf-8')
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_new_pass, email))
        conn.commit()

        return jsonify({'success': True, 'message': 'Password changed successfully.'})

    except Exception as e:
        print(f"Error changing password: {e}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/developers')
@admin_required
def admin_developers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch Developers
        cursor.execute("SELECT * FROM developers ORDER BY is_leader DESC, name ASC")
        developers = cursor.fetchall()
        
        # 2. Fetch Guides
        cursor.execute("SELECT * FROM guides ORDER BY name ASC")
        guides = cursor.fetchall()
        
        # 3. Process Images (Apply Default if Missing)
        # We assume 'get_public_url' returns None if the path is empty/None.
        default_img = url_for('static', filename='images/default_profile.png')

        for p in developers + guides:
            # Try to get uploaded photo URL; fallback to default_img
            p['photo_url'] = get_public_url(p.get('photo_path')) or default_img

        return render_template('admin_developers.html', developers=developers, guides=guides)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/add_developer', methods=['POST'])
@admin_required
def add_developer():
    try:
        data = request.form
        files = request.files
        
        photo_path = None
        if 'photo' in files and files['photo'].filename != '':
            photo_path = save_file(files['photo'], 'dev', data['regNo'])

        is_leader = True if data.get('isLeader') == 'on' else False

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If new dev is leader, remove leader status from others (optional rule)
        # if is_leader:
        #     cursor.execute("UPDATE developers SET is_leader = FALSE")
        
        sql = """
            INSERT INTO developers (name, role, reg_no, year_study, department, college, email, linkedin, github, is_leader, photo_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        vals = (data['name'], data['role'], data['regNo'], data['year'], data['department'], 
                data['college'], data['email'], data['linkedin'], data['github'], is_leader, photo_path)
        
        cursor.execute(sql, vals)
        conn.commit()
        flash('Developer added successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        
    return redirect(url_for('admin_developers'))

@app.route('/admin/delete_developer/<int:dev_id>')
@admin_required
def delete_developer(dev_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM developers WHERE id = %s", (dev_id,))
        conn.commit()
        flash('Developer removed.', 'success')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_developers'))

# 3. Routes for Guides
@app.route('/admin/add_guide', methods=['POST'])
@admin_required
def add_guide():
    try:
        data = request.form
        files = request.files
        
        photo_path = None
        if 'photo' in files and files['photo'].filename != '':
            identifier = secrets.token_hex(4)
            photo_path = save_file(files['photo'], 'guide', identifier)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO guides (name, designation, department, college, email, photo_path)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        vals = (data['name'], data['designation'], data['department'], data['college'], data['email'], photo_path)
        
        cursor.execute(sql, vals)
        conn.commit()
        flash('Guide details added successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        
    return redirect(url_for('admin_developers'))

@app.route('/admin/delete_guide/<int:guide_id>')
@admin_required
def delete_guide(guide_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM guides WHERE id = %s", (guide_id,))
        conn.commit()
        flash('Guide removed.', 'success')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_developers'))

# --- ROUTE TO DELETE TEAM MEMBERS (Developers & Guides) ---
@app.route('/admin/delete_team_member/<type>/<int:id>')
@admin_required
def delete_team_member(type, id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Select table based on type ('dev' or 'guide')
        table = "developers" if type == 'dev' else "guides"
        
        # Delete the record
        cursor.execute(f"DELETE FROM {table} WHERE id = %s", (id,))
        conn.commit()
        
        flash('Team member removed successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting record: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_developers'))
# Change the bottom of your file to:
if __name__ == '__main__':
    #create_database_if_not_exists()
    create_tables()
    socketio.run(app, debug=True)
