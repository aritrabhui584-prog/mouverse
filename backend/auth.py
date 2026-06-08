import os
import sqlite3
import random
import bcrypt
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_login import UserMixin, login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer
from twilio.rest import Client

auth_bp = Blueprint("auth", __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mouverse.db")

def is_debug_mode():
    try:
        return current_app.debug
    except RuntimeError:
        return os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1") or \
               os.getenv("FLASK_ENV", "").lower() == "development" or \
               os.getenv("DEBUG", "false").lower() in ("true", "1")

# User representation for Flask-Login
class User(UserMixin):
    def __init__(self, id, name, email, phone, region, email_verified, phone_verified):
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.region = region
        self.email_verified = email_verified
        self.phone_verified = phone_verified

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_email(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row['id'], row['name'], row['email'], row['phone'], row['region'], row['email_verified'], row['phone_verified'])
    return None

def get_user_by_id(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row['id'], row['name'], row['email'], row['phone'], row['region'], row['email_verified'], row['phone_verified'])
    return None

def send_sms_otp(phone, otp_code):
    """Send OTP via Twilio or fallback to printing to console"""
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    if dev_mode and is_debug_mode():
        print(f"\n[DEV MODE] OTP code for {phone} is: {otp_code} (SMS not sent)\n")
        return False

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
    
    if account_sid and auth_token and twilio_phone:
        try:
            client = Client(account_sid, auth_token)
            client.messages.create(
                body=f"Your Mouverse AI verification code is: {otp_code}. It will expire in 5 minutes.",
                from_=twilio_phone,
                to=phone
            )
            return True
        except Exception as e:
            print(f"Twilio Send Error: {e}")
            return False
    else:
        if is_debug_mode():
            print(f"\n[SANDBOX SMS] OTP code for {phone} is: {otp_code}\n")
        else:
            print("[WARNING] Twilio credentials are not configured; OTP delivery is disabled in production.")
        return False

def send_verification_email(email, user_id):
    """Send verification email link via Flask-Mail or fallback to printing to console"""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = serializer.dumps(user_id, salt="email-confirm")
    confirm_url = url_for("auth.confirm_email", token=token, _external=True)
    
    mail_username = os.getenv("MAIL_USERNAME")
    
    if mail_username:
        try:
            from flask_mail import Message
            # Retrieve mail client dynamically to avoid circular imports
            mail = current_app.extensions.get('mail')
            if mail:
                msg = Message(
                    "Verify Your Mouverse AI Account",
                    recipients=[email],
                    body=f"Welcome to Mouverse AI! To complete registration, please confirm your email address by clicking here: {confirm_url}"
                )
                mail.send(msg)
                return True, confirm_url
        except Exception as e:
            print(f"Flask-Mail Send Error: {e}")
            return False, confirm_url
    else:
        if is_debug_mode():
            print(f"\n[SANDBOX EMAIL] Verification URL for {email} is: {confirm_url}\n")
        else:
            print("[WARNING] Flask-Mail is not configured; verification email delivery is disabled in production.")
        return False, confirm_url

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
        
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        conn.close()
        
        if row and bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
            user = User(row['id'], row['name'], row['email'], row['phone'], row['region'], row['email_verified'], row['phone_verified'])
            
            # Check if user needs OTP verification
            if not user.phone_verified:
                # Store user email in session and generate new OTP
                session["pending_verification_email"] = user.email
                
                # Generate new OTP
                otp_code = f"{random.randint(100000, 999999)}"
                print(f"OTP generated: {otp_code}")
                expires_at = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
                
                # Save OTP in DB
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(
                    "INSERT INTO otp_verification (email, phone, otp_code, expires_at) VALUES (?, ?, ?, ?)",
                    (user.email, user.phone, otp_code, expires_at)
                )
                conn.commit()
                print(f"[OTP_LOG] OTP stored in database: {otp_code} for {user.email}")
                conn.close()
                
                # Send OTP
                twilio_sent = send_sms_otp(user.phone, otp_code)
                
                # Development: print OTP to terminal
                dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
                if dev_mode:
                    print(f"Development OTP: {otp_code}")
                elif not twilio_sent and is_debug_mode():
                    print(f"[DEV] OTP: {otp_code}")
                
                # User feedback
                flash("OTP sent successfully", "info")
                    
                return redirect(url_for("auth.verify_otp"))
                
            login_user(user)
            flash("Welcome back to Mouverse AI!", "success")
            
            # If user has not selected region, redirect to region select
            if not user.region:
                return redirect(url_for("region.select_region"))
                
            session["region"] = user.region
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
        
    if request.method == "POST":
        name = request.form.get("name").strip()
        email = request.form.get("email").strip()
        phone = request.form.get("phone").strip()
        password = request.form.get("password")
        
        if not name or not email or not phone or not password:
            flash("Please fill in all registration fields.", "danger")
            return redirect(url_for("auth.login"))
            
        # Check if email exists
        if get_user_by_email(email):
            flash("Email address is already registered.", "danger")
            return redirect(url_for("auth.login"))
            
        # Hash password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Save user to DB
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (name, email, phone, password, email_verified, phone_verified) VALUES (?, ?, ?, ?, 0, 0)",
                (name, email, phone, hashed_password)
            )
            user_id = c.lastrowid
            conn.commit()
        except Exception as e:
            conn.close()
            print(f"[ERROR] Registration database error: {e}")
            flash("A database error occurred during registration. Please try again.", "danger")
            return redirect(url_for("auth.login"))
        conn.close()
        
        # Setup session variable for verification flow
        session["pending_verification_email"] = email
        
        # Generate 6-digit OTP code (valid for 5 minutes)
        otp_code = f"{random.randint(100000, 999999)}"
        print(f"OTP generated: {otp_code}")
        expires_at = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Store OTP code
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO otp_verification (email, phone, otp_code, expires_at) VALUES (?, ?, ?, ?)",
            (email, phone, otp_code, expires_at)
        )
        conn.commit()
        print(f"[OTP_LOG] OTP stored in database: {otp_code} for {email}")
        conn.close()
        
        # Send SMS OTP
        twilio_sent = send_sms_otp(phone, otp_code)
        
        # Send Email Verification
        email_sent, confirm_url = send_verification_email(email, user_id)
        
        # Development: print OTP and link to terminal
        dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
        if dev_mode:
            print(f"Development OTP: {otp_code}")
        elif not twilio_sent and is_debug_mode():
            print(f"[DEV] OTP: {otp_code}")
        if not email_sent and is_debug_mode():
            print(f"[DEV] Email link: {confirm_url}")
        
        # User feedback
        flash("OTP sent successfully", "success")
            
        return redirect(url_for("auth.verify_otp"))
        
    return render_template("login.html")

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("pending_verification_email")
    if not email:
        flash("No pending verification session found.", "danger")
        return redirect(url_for("auth.login"))
        
    if request.method == "POST":
        entered_otp = (request.form.get("otp_code") or "").strip()
        
        # Retrieve latest OTP code for this email
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM otp_verification WHERE email = ? ORDER BY id DESC LIMIT 1",
            (email,)
        )
        row = c.fetchone()
        conn.close()
        
        if row:
            otp_db = row['otp_code']
            expires_at = datetime.strptime(row['expires_at'], "%Y-%m-%d %H:%M:%S")
            
            # Check code matching and expiration (5 minutes duration)
            if entered_otp == otp_db:
                if datetime.now() <= expires_at:
                    # Update phone_verified status
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE users SET phone_verified = 1 WHERE email = ?", (email,))
                    c.execute("DELETE FROM otp_verification WHERE email = ?", (email,))
                    conn.commit()
                    
                    # Reload user to log them in
                    c.execute("SELECT * FROM users WHERE email = ?", (email,))
                    user_row = c.fetchone()
                    conn.close()
                    
                    user = User(
                        user_row['id'], user_row['name'], user_row['email'], 
                        user_row['phone'], user_row['region'], user_row['email_verified'], user_row['phone_verified']
                    )
                    
                    # Log user in
                    login_user(user)
                    session.pop("pending_verification_email", None)
                    
                    flash("Phone OTP verified successfully!", "success")
                    return redirect(url_for("region.select_region"))
                else:
                    flash("OTP has expired (expires in 5 minutes).", "danger")
            else:
                flash("Invalid OTP code.", "danger")
        else:
            flash("No verification record found.", "danger")
            
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    active_otp = None
    if dev_mode:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT otp_code FROM otp_verification WHERE email = ? ORDER BY id DESC LIMIT 1",
            (email,)
        )
        row = c.fetchone()
        conn.close()
        if row:
            active_otp = row["otp_code"]
    return render_template("verify_otp.html", email=email, dev_mode=dev_mode, active_otp=active_otp)

@auth_bp.route("/resend-otp")
def resend_otp():
    email = session.get("pending_verification_email")
    if not email:
        flash("No pending verification session found.", "danger")
        return redirect(url_for("auth.login"))
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT phone FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    
    if row:
        phone = row['phone']
        otp_code = f"{random.randint(100000, 999999)}"
        print(f"OTP generated: {otp_code}")
        expires_at = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO otp_verification (email, phone, otp_code, expires_at) VALUES (?, ?, ?, ?)",
            (email, phone, otp_code, expires_at)
        )
        conn.commit()
        print(f"[OTP_LOG] OTP stored in database: {otp_code} for {email}")
        conn.close()
        
        twilio_sent = send_sms_otp(phone, otp_code)
        
        # Development: print OTP to terminal
        dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
        if dev_mode:
            print(f"Development OTP: {otp_code}")
        elif not twilio_sent and is_debug_mode():
            print(f"[DEV] OTP: {otp_code}")
        
        # User feedback
        flash("OTP sent successfully", "success")
    else:
        flash("User record not found for resending.", "danger")
        
    return redirect(url_for("auth.verify_otp"))

@auth_bp.route("/verify-email/<token>")
def confirm_email(token):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        user_id = serializer.loads(token, salt="email-confirm", max_age=86400) # Token valid for 24 hours
    except Exception:
        flash("The verification link is invalid or has expired.", "danger")
        return redirect(url_for("auth.login"))
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("Your email address has been verified successfully! Thank you.", "success")
    return redirect(url_for("auth.login"))

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))
