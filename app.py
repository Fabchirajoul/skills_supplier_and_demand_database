import numpy as np
from flask import Flask, request, render_template, redirect, session, url_for, jsonify, flash, send_from_directory, make_response,send_file
import matplotlib.pyplot as plt
import matplotlib
import pyodbc
import uuid
import random
from weasyprint import HTML, CSS

from datetime import datetime, timedelta
from collections import defaultdict
import calendar

from werkzeug.utils import secure_filename
from itertools import zip_longest  # Import to handle missing values

import math
import os

from FUNCTION.generalFunctions import fetch_combined_user_details, function_fetch_all_applicant_results, function_fetch_all_applicant_results_for_company
from db_utils import get_db_connection #Database connection string

matplotlib.use('Agg')  # Use a non-GUI backend

app = Flask(__name__)
app.secret_key = 'secret_key'








# Index root

@app.route('/')
def index():
    return render_template('login.html')


# Logout

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.clear()  # ✅ Clears session properly
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))



# Route to fetch SDL number based on company name
@app.route("/get_sdl_number", methods=["POST"])
def get_sdl_number():
    data = request.get_json()
    company_name = data.get("company_name", "").strip().lower()  # Convert input to lowercase

    if not company_name:
        return jsonify({"error": "Company name is required"}), 400

    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Fetch SDL number where company name matches (case-insensitive)
        cursor.execute("""
            SELECT sd_number FROM SSDD_COMPLETE_COMPANY_SDL_NUMBER
            WHERE LOWER(LTRIM(RTRIM(Company_name))) = ?
        """, (company_name,))
        
        result = cursor.fetchone()
        cursor.close()

        if result:
            print(f"✅ [DEBUG] Found SDL Number: {result[0]} for Company: {company_name}")  # ✅ Debugging Output
            return jsonify({"sdl_number": result[0]})  # ✅ Return the SDL number
        else:
            print(f"❌ [DEBUG] No SDL Number found for Company: {company_name}")  # ✅ Debugging Output
            return jsonify({"sdl_number": None})  # ✅ No match found

    except Exception as e:
        print(f"❌ [ERROR] Database Error: {e}")
        return jsonify({"error": "Database error"}), 500

    finally:
        if conn:
            conn.close()


# Register route

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        account_type = request.form.get('AccountType')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('userpassword')
        confirm_password = request.form.get('confirmUserPassword')

        company_name = request.form.get('company_name') if account_type == 'Company' else None
        sdl_number = request.form.get('sdl_number') if account_type == 'Company' else None

        if not all([username, email, password, confirm_password, account_type]):
            flash('All fields are required. Please fill out the form completely.', 'danger')
            return redirect(request.url)

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(request.url)

        conn = None
        try:
            conn = get_db_connection('WorkflowDB')
            cursor = conn.cursor()

            # Check if email already exists
            cursor.execute("SELECT email FROM SSDD__COMPLETE_REGISTER WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('This email is already registered. Please use another email.', 'warning')
                return redirect(request.url)

            # Insert user data into SSDD__COMPLETE_REGISTER
            cursor.execute("""
                INSERT INTO SSDD__COMPLETE_REGISTER (username, email, password, account_type, account_status, date_joined, otp_verified, company_name, sd_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, email, password, account_type, 0, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), 0, company_name, sdl_number))

            # Insert user data into SSDD_COMPLETE_LOGIN
            cursor.execute("""
                INSERT INTO SSDD_COMPLETE_LOGIN (Surname, Email, Password, AccountType, AccountStatus)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, password, account_type, 0))

            # Store user email in session
            session['email'] = email

            # Generate OTP and save it
            generate_otp(conn, cursor, email)

            conn.commit()  # Ensure all changes are saved before closing

            flash("Registration successful! An OTP has been sent to your email. Please verify your account.", "success")
            return redirect(url_for('login_otp'))

        except Exception as e:
            print(f"Database error: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(request.url)

        finally:
            if conn:
                conn.close()

    return render_template('register.html')







  
#OTP REDIRECT
@app.route('/loginOTP')
def login_otp():
    return render_template('loginOTP.html')  # Make sure this file is in the "templates/" folder


def generate_otp(conn, cursor, email):
    otp_code = random.randint(100000, 999999)  # Generate a 6-digit OTP
    otp_created_at = datetime.utcnow()  # Timestamp for OTP generation

    try:
        # Store OTP in SSDD_COMPLETE_OTP_RECORD table
        cursor.execute("""
            INSERT INTO SSDD_COMPLETE_OTP_RECORD (Email, OTP_Code_generated, otp_created_at)
            VALUES (?, ?, ?)
        """, (email, otp_code, otp_created_at))

        # Also update the SSDD__COMPLETE_REGISTER table to store the OTP
        cursor.execute("""
            UPDATE SSDD__COMPLETE_REGISTER 
            SET otp_code = ?, otp_created_at = ?, otp_verified = 0 
            WHERE email = ?
        """, (otp_code, otp_created_at, email))

        print(f"Generated OTP for {email}: {otp_code}")  # Debugging output
        flash("OTP has been sent to your email.", "info")
    except Exception as e:
        print(f"Error generating OTP: {e}")
        flash("An error occurred while generating OTP. Please try again.", "danger")




# Route to verify OTP
@app.route('/verify_otp', methods=['POST'])
def verify_otp_code_generated():
    if 'email' not in session:
        flash("No email found in session. Please register or log in again.", "danger")
        return redirect(url_for('register'))

    email = session['email']
    entered_otp = request.form.get("otp_code")  # Get user-inputted OTP

    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Fetch stored OTP details
        cursor.execute("""
            SELECT OTP_Code_generated, otp_created_at 
            FROM SSDD_COMPLETE_OTP_RECORD 
            WHERE Email = ?
        """, (email,))
        otp_data = cursor.fetchone()

        if not otp_data:
            flash("No OTP found. Please request a new OTP.", "danger")
            return redirect(url_for('login_otp'))

        stored_otp, otp_created_at = otp_data

        # Ensure OTP values are not None
        if stored_otp is None or otp_created_at is None:
            flash("Invalid OTP record. Please request a new OTP.", "danger")
            return redirect(url_for('login_otp'))

        # Convert stored OTP and entered OTP to strings for comparison
        stored_otp = str(stored_otp)
        entered_otp = str(entered_otp)

        # Debugging outputs to verify values
        current_time = datetime.utcnow()  # Get current UTC time

        print(f"Stored OTP: {stored_otp}, Entered OTP: {entered_otp}")
        print(f"OTP Created At (Stored in DB): {otp_created_at}, Current Time (UTC): {current_time}")

        # Calculate time difference
        time_difference = (current_time - otp_created_at).total_seconds()
        print(f"Time Difference: {time_difference} seconds")

        # Check if OTP matches and is within 10-minute validity period
        if entered_otp == stored_otp and 0 <= time_difference <= 600:  # 10 minutes = 600 seconds
            cursor.execute("""
                UPDATE SSDD__COMPLETE_REGISTER 
                SET otp_verified = 1 
                WHERE email = ?
            """, (email,))

            # ✅ NEW: Update AccountStatus in SSDD_COMPLETE_LOGIN
            cursor.execute("""
                UPDATE SSDD_COMPLETE_LOGIN 
                SET AccountStatus = 1 
                WHERE Email = ?
            """, (email,))

            conn.commit()
            flash("Your account is now active. Please log in.", "success")
            return redirect(url_for('index'))  # Redirect to login page

        else:
            flash("Invalid or expired OTP. Please try again.", "danger")
            return redirect(url_for('login_otp'))

    except Exception as e:
        print(f"Error verifying OTP: {e}")
        flash("An error occurred while verifying OTP. Please try again.", "danger")
        return redirect(url_for('login_otp'))

    finally:
        if conn:
            conn.close()
            
# Resend OTP function
def resend_otp(email):
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Generate a new OTP
        new_otp = random.randint(100000, 999999)  # New 6-digit OTP
        new_otp_created_at = datetime.utcnow()  # Timestamp for OTP creation

        # Update the OTP for the user in SSDD_COMPLETE_OTP_RECORD
        cursor.execute("""
            UPDATE SSDD_COMPLETE_OTP_RECORD 
            SET OTP_Code_generated = ?, otp_created_at = ? 
            WHERE Email = ?
        """, (new_otp, new_otp_created_at, email))

        conn.commit()
        print(f"Resent OTP for {email}: {new_otp}")  # Debugging Output

    except Exception as e:
        print(f"Error resending OTP: {e}")

    finally:
        if conn:
            conn.close()



            
#Resend OTP
@app.route('/resend_otp')
def resend_otp_route():
    if 'email' not in session:
        flash("No email found in session. Please register or log in again.", "danger")
        return redirect(url_for('register'))

    email = session['email']
    resend_otp(email)  # Call function to generate a new OTP

    flash("A new OTP has been sent to your email. Please enter it to verify your account.", "info")
    return redirect(url_for('login_otp'))






# Login Route
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Fetch user account details including PersonalInforEntered
        cursor.execute("""
            SELECT AccountType, AccountStatus, PersonalInforEntered
            FROM SSDD_COMPLETE_LOGIN 
            WHERE Email = ? AND Password = ?
        """, (email, password))
        user = cursor.fetchone()

        if user:
            account_type, account_status, personal_info_entered = user

            if account_status == 1:  # ✅ Account is verified
                session['email'] = email  # ✅ Store email in session
                session.permanent = True  # ✅ Keep session active
                if account_type == 'Learner':
                    if personal_info_entered == 1:
                        # ✅ If Personal Info is entered, go to the Student Dashboard
                        return redirect(url_for('Studentdashboardinformation'))
                    else:
                        # ✅ If Personal Info is NOT entered, redirect to personal information form
                        flash("Make sure you have completed all 5 steps", "warning")
                        return redirect(url_for('Enterstudentpersonalinformation'))
                elif account_type == 'Company':
                    return redirect(url_for('DashboardCompany'))
                elif account_type == 'Administrator':
                    return redirect(url_for('DashboardAdministrator'))
            
            else:
                # ✅ If AccountStatus is 0, resend OTP and redirect to OTP verification page
                resend_otp(email)  # Generate a new OTP
                flash("Your account is not verified. Click to resend a new OTP to verify your account.", "warning")
                return redirect(url_for('login_otp'))

        else:
            flash("Invalid email or password.", "danger")

    except Exception as e:
        print(f"Login error: {e}")
        flash("An error occurred during login. Please try again.", "danger")

    finally:
        if conn:
            conn.close()

    return redirect(url_for('index'))





# Getting unique element for company 
def get_distinct_elements():
    # Use your existing database connection method
    conn = get_db_connection('WorkflowDB')
    cursor = conn.cursor()

    # Queries to fetch distinct elements
    queries = {
        "fields_of_study": "SELECT DISTINCT Field_of_Study FROM SSDD_FIELD_OF_STUDY",
        "institutions": "SELECT DISTINCT Institute_of_Study FROM SSDD_INSTITUTION",
        "provinces_cities": "SELECT DISTINCT Province, City FROM SSDD_PROVINCE_CITY",
        "qualification_types": "SELECT DISTINCT Qualification_Type FROM SSDD_QUALIFICATION_TYPE",
        "race_types": "SELECT DISTINCT Race_type FROM SSDD_RACE_TYPE",
        "disability_types" : "SELECT DISTINCT Type_of_Disability FROM SSDD_DISABILITY",
        "placement_types" : "SELECT Placement_type FROM SSDD_PLACEMENT_TYPE"
    }

    # Dictionary to store the results
    data = {
        "fields_of_study": [],
        "institutions": [],
        "provinces_cities": [],
        "qualification_types": [],
        "race_types" : [],
        "disability_types": [],
        "placement_types" : []
    }

    try:
        # Loop through each query and fetch results
        for key, query in queries.items():
            cursor.execute(query)
            rows = cursor.fetchall()

            # Process and store the results based on the query type
            if key == "provinces_cities":
                # Combine Province and City into a list of dictionaries
                data[key] = [{"province": row[0], "city": row[1]} for row in rows]
            else:
                # Store as a list of distinct values
                data[key] = [row[0] for row in rows]
    except Exception as e:
        print(f"An error occurred while fetching data: {e}")
    finally:
        # Ensure the cursor and connection are properly closed
        cursor.close()
        conn.close()

    return data            
            
#Dashboard student enter personal info    
@app.route('/studentpersonalinformation')
def Enterstudentpersonalinformation():
    distinct_data = get_distinct_elements()



    return render_template('studentpersonalinformation.html', distinct_data=distinct_data)    


#Dashboard student 
@app.route('/MainDashboardForStudent')
def PersonalInfoAlreadyEntered():
    distinct_data = get_distinct_elements()
    
    # fetch_all_applicant_results = function_fetch_all_applicant_results()



    return render_template('WelcomeStudent.html', distinct_data=distinct_data)   


# Dashbaord company
@app.route('/MainDashboardForCompany')
def DashboardCompany():
    distinct_data = get_distinct_elements()
    company_fetch_looping_results = function_fetch_all_applicant_results_for_company()



    return render_template('WelcomeCompany.html', distinct_data=distinct_data, company_fetch_looping_results =company_fetch_looping_results )   


# Help and support company
@app.route('/MainDashboardForCompany/and/support')
def DashboardCompanyhelpandsupport():
    distinct_data = get_distinct_elements()
    company_fetch_looping_results = function_fetch_all_applicant_results_for_company()



    return render_template('CompanyHelpandSupport.html', distinct_data=distinct_data, company_fetch_looping_results =company_fetch_looping_results )   


@app.route('/MainDashboardForCompany/and/notifications')
def DashboardCompanyhelpandnotifications():
    distinct_data = get_distinct_elements()
    company_fetch_looping_results = function_fetch_all_applicant_results_for_company()



    return render_template('CompanyHelpandNotifications.html', distinct_data=distinct_data, company_fetch_looping_results =company_fetch_looping_results )   






def function_fetch_all_applicant_results_for_company():
    """
    Fetch applicants who are active (Is_Active = 1) by selecting only one entry per email.
    Orders by the most recent entries first.
    """
    conn = None
    fetch_all_applicant_results_company = []
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Updated Query: Only fetch applicants where Is_Active = 1
        query = """
            SELECT 
                p.firstname + ' ' + p.lastname AS name,
                COALESCE(MAX(e.Field_of_study), 'Not Provided') AS field_of_study,
                p.email,
                p.contact_number,
                p.Province,
                COALESCE(p.Seeking_Placement, 'Not Specified') AS seeking_placement,
                COALESCE(l.Is_Active, 0) AS Is_Active,  -- Defaults to 0 if NULL
                COALESCE(l.Is_Placed, 0) AS Is_Placed   -- Defaults to 0 if NULL
            FROM SSDD_COMPLETE_PERSONALINFO p
            LEFT JOIN SSDD_COMPLETE_EDUCATION_DETAILS e ON p.email = e.email
            LEFT JOIN SSDD_COMPLETE_LOGIN l ON p.email = l.Email  -- ✅ Join with SSDD_COMPLETE_LOGIN
            WHERE l.Is_Active = 1  -- ✅ Only fetch ACTIVE applicants
            GROUP BY p.id, p.firstname, p.lastname, p.email, p.contact_number, p.province,
                     p.Seeking_Placement, l.Is_Active, l.Is_Placed
            ORDER BY p.id DESC  -- ✅ Orders most recent entries at the top
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Convert fetched data into a list of dictionaries
        fetch_all_applicant_results_company = [
            {
                "name": row[0],
                "field_of_study": row[1],
                "email": row[2],
                "contact_number": row[3],
                "region": row[4],
                "seeking_placement": row[5],
                "is_active": "Active" if row[6] == 1 else "Inactive",  # ✅ Convert 1 -> "Active", 0 -> "Inactive"
                "is_placed": "Yes" if row[7] == 1 else "No"   # ✅ Convert 1 -> "Yes", 0 -> "No"
            }
            for row in rows
        ]

        # 🔍 Debugging: Print fetched data
        print("🔍 Debugging - Fetched Active Applicants:", fetch_all_applicant_results_company)

    except Exception as e:
        print(f"Database error while fetching active applicant details: {e}")
    finally:
        if conn:
            conn.close()

    return fetch_all_applicant_results_company



#  Company filter table
@app.route('/filter_applicants_company', methods=['GET', 'POST'])
def filter_applicants_company():
    """
    Filters applicants based on user-selected criteria and ensures only active accounts are retrieved.
    """
    # ✅ Fetch distinct data (for dropdown lists)
    distinct_data = get_distinct_elements()

    # ✅ Get filter values from request.args (GET)
    Qualification = request.args.get('Qualification', '').strip()
    City = request.args.get('City_and_town_of_residence', '').strip()
    Disability = request.args.get('Disability', '').strip()
    Province = request.args.get('Province', '').strip()
    Academic_Institution = request.args.get('Academic_Institution', '').strip()
    Race = request.args.get('Race', '').strip()
    Gender = request.args.get('Gender', '').strip()
    Seeking_Placement = request.args.get('Seeking_Placement', '').strip()
    Preferred_Opportunity = request.args.get('Preferred_Opportunity', '').strip()

    # ✅ Dictionary to store only active filters
    active_filters = {
        "Qualification": Qualification,
        "City": City,
        "Disability": Disability,
        "Province": Province,
        "Academic_Institution": Academic_Institution,
        "Race": Race,
        "Gender": Gender,
        "Seeking_Placement": Seeking_Placement,
        "Preferred_Opportunity": Preferred_Opportunity
    }
    active_filters = {k: v for k, v in active_filters.items() if v}  # ✅ Remove empty values

    # ✅ If no filters are selected, return an empty result set
    if not active_filters:
        print("❌ No filters provided. Returning default dashboard.")
        return render_template(
            'WelcomeCompany.html',
            distinct_data=distinct_data,
            results_filter_applicants_company=[],
        )

    # ✅ Build SQL Query for filtering applicants
    conn = None
    results = []
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT 
                p.firstname + ' ' + p.lastname AS name,
                COALESCE(e.Field_of_study, 'Not Provided') AS field_of_study,
                p.email,
                p.contact_number,
                p.Race,
                p.Gender,
                COALESCE(p.Seeking_Placement, 'Not Specified') AS seeking_placement,
                p.Province,
                p.City,
                e.Qualification,
                e.Academic_Institution,
                COALESCE(l.Is_Active, 0) AS Is_Active,  
                COALESCE(l.Is_Placed, 0) AS Is_Placed   
            FROM SSDD_COMPLETE_PERSONALINFO p
            LEFT JOIN SSDD_COMPLETE_EDUCATION_DETAILS e ON p.email = e.email
            LEFT JOIN SSDD_COMPLETE_LOGIN l ON p.email = l.Email  
            WHERE l.Is_Active = 1  -- ✅ Filter active accounts
        """

        params = []
        if "Qualification" in active_filters:
            query += " AND COALESCE(e.Qualification, '') LIKE ?"
            params.append(f"%{active_filters['Qualification']}%")
        if "City" in active_filters:
            query += " AND COALESCE(p.City, '') LIKE ?"
            params.append(f"%{active_filters['City']}%")
        if "Disability" in active_filters:
            query += " AND COALESCE(p.Disability, '') = ?"
            params.append(active_filters["Disability"])
        if "Province" in active_filters:
            query += " AND COALESCE(p.Province, '') = ?"
            params.append(active_filters["Province"])
        if "Academic_Institution" in active_filters:
            query += " AND COALESCE(e.Academic_Institution, '') LIKE ?"
            params.append(f"%{active_filters['Academic_Institution']}%")
        if "Race" in active_filters:
            query += " AND COALESCE(p.Race, '') = ?"
            params.append(active_filters["Race"])
        if "Gender" in active_filters:
            query += " AND COALESCE(p.Gender, '') = ?"
            params.append(active_filters["Gender"])
        if "Seeking_Placement" in active_filters:
            query += " AND COALESCE(p.Seeking_Placement, '') = ?"
            params.append(active_filters["Seeking_Placement"])
        if "Preferred_Opportunity" in active_filters:
            query += " AND COALESCE(p.Preferred_Opportunity, '') = ?"
            params.append(active_filters["Preferred_Opportunity"])

        # ✅ Sort results by most recent entries using `p.id DESC`
        query += """
            GROUP BY p.id, p.firstname, p.lastname, p.email, p.contact_number, p.Race, p.Gender, 
                     p.Seeking_Placement, p.Province, p.City, e.Qualification, e.Academic_Institution, 
                     e.Field_of_study, l.Is_Active, l.Is_Placed
            ORDER BY p.id DESC
        """

        # ✅ Debugging - Print SQL Query & Params
        print("🔍 SQL Query:", query)
        print("🔍 Query Params:", params)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # ✅ Convert results into a list of dictionaries
        results = [
            {
                "name": row[0],
                "field_of_study": row[1],
                "email": row[2],
                "contact_number": row[3],
                "race": row[4],
                "gender": row[5],
                "seeking_placement": row[6],
                "province": row[7],
                "city": row[8],
                "qualification": row[9],
                "academic_institution": row[10],
                "is_active": "Active" if row[11] == 1 else "Inactive",  
                "is_placed": "Yes" if row[12] == 1 else "No"
            }
            for row in rows
        ]

    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if conn:
            conn.close()

    return render_template(
        'WelcomeCompany.html',
        distinct_data=distinct_data,
        results_filter_applicants_company=results,
    )


# Company view cv
#View cv admin
@app.route('/Company_view_all_cv')
def CompanyViewCV():
    # ✅ Get email from query parameters
    email = request.args.get('email', '').strip()

    # ✅ Debugging: Print email received
    print(f"🔍 Fetching CV details for email: {email}")

    # ✅ Store email in session
    if email:
        session['current_student_email'] = email  # Store for later use
        print(f"📌 Email stored in session: {session['current_student_email']}")

    # ✅ Fetch distinct data
    distinct_data = get_distinct_elements()
    recent_registrations = count_recent_registrations()
    total_incomplete_profiles = count_incomplete_profiles()

    # ✅ Fetch CV data
    cv_data = fetch_combined_user_details(email)

    return render_template(
        'CompanyViewCVForStudent.html',
        distinct_data=distinct_data,
        recent_registrations=recent_registrations,
        incomplete_profiles=total_incomplete_profiles,
        cv_data_admin_view_all_cv=cv_data
    )


# Admin redirecting to decision page
@app.route('/Company_Placement_Decision_page_making')
def CompanyDecisionMaking():
    # ✅ Retrieve email from session
    email = session.get('current_student_email', '')

    # ✅ Debugging: Print email from session
    print(f"📌 Email retrieved from session for decision-making: {email}")

    distinct_data = get_distinct_elements()
   
    cv_data = fetch_combined_user_details(email)

    return render_template(
        'CompanyDecision.html',
        distinct_data=distinct_data,
       
        cv_data_admin_view_all_cv=cv_data
    )



#Company making placement or refusal decision
@app.route('/Company_Making_approval_or_refual_decision_on_learner', methods=['POST'])
def Company_Making_approval_or_refual_decision_on_learner():
    try:
        # ✅ Get email from session (instead of form)
        email = session.get('current_student_email', '')

        # ✅ Debugging: Print email retrieved from session
        print(f"📌 Email retrieved from session for decision submission: {email}")

        # ✅ Get form data
        decision_outcome = request.form.get('company_decision_on_learner')
        reason_for_rejection = request.form.get('reason_for_rejection', '')



        # ✅ Ensure the administrator is logged in
        company_email = session.get('email')  
        print("👤 Administrator email from session:", company_email)

        if not company_email:
            flash("Unauthorized access. Please log in first.", "danger")
            return redirect(url_for('login'))  

        # ✅ Ensure email is valid before inserting into database
        if not email:
            print("❌ ERROR: Email is missing!")
            flash("Error: No email provided for decision.", "danger")
            return redirect(url_for('DashboardAdministrator'))

        # ✅ Get current timestamp
        decision_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ✅ Connect to the database
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Insert into the Decision Outcome table
        cursor.execute("""
            INSERT INTO SSDD_COMPLETE_COMPANY_DECISION_OUTCOME (email, Decision_outcome, Company_name, Decision_date, Decision_verdict)
            VALUES (?, ?, ?, ?, ?)
        """, (email, decision_outcome, company_email, decision_date, reason_for_rejection))
        print("✅ Inserted decision into the database successfully!")

        # ✅ Check if the email exists in SSDD_COMPLETE_LOGIN
        cursor.execute("SELECT Is_Active FROM SSDD_COMPLETE_LOGIN WHERE email = ?", (email,))
        result = cursor.fetchone()

        if result:
            current_status = result[0]
            print(f"🔎 Current Is_Active status for {email}: {current_status}")

            # ✅ If decision is "Approve", set Is_Active = 1
            if decision_outcome == "Approve":
                print(f"🔄 Updating Is_Active to 1 for {email}")
                cursor.execute("""
                    UPDATE SSDD_COMPLETE_LOGIN
                    SET Is_Placed = 1
                    WHERE email = ?
                """, (email,))

            # ✅ If decision is "Reject" and Is_Active is 1, set Is_Active = 0
            elif decision_outcome == "Reject" and current_status == 1:
                print(f"🔄 Updating Is_Placed to 0 for {email} (Rejection rollback)")
                cursor.execute("""
                    UPDATE SSDD_COMPLETE_LOGIN
                    SET Is_Placed = 0
                    WHERE email = ?
                """, (email,))

        else:
            print(f"❌ Email {email} not found in SSDD_COMPLETE_LOGIN. No update performed.")

        # ✅ Commit changes and close connection
        conn.commit()
        print("✅ Database changes committed!")
        cursor.close()
        conn.close()

        flash("Decision submitted successfully.", "success")
        return redirect(url_for('DashboardCompany'))  

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        print("❌ Database error:", str(e))
        return redirect(url_for('DashboardCompany'))  



















































































# Incomplete profile
def count_incomplete_profiles():
    """
    Count the total number of users in SSDD_COMPLETE_LOGIN where PersonalInforEntered = 0.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT COUNT(*) 
            FROM SSDD_COMPLETE_LOGIN 
            WHERE PersonalInforEntered = 0
        """
        cursor.execute(query)
        count = cursor.fetchone()[0]  # Fetch the count value

        print(f"Total users with incomplete personal info: {count}")
        return count

    except Exception as e:
        print(f"Database error while counting incomplete profiles: {e}")
        return None

    finally:
        if conn:
            conn.close()
            
            
# Placement function count
def count_recent_placement_students():
    """
    Count the number of accounts where:
      - Is_Placed = 1 (placed) and Is_Placed = 0 (not placed).
      - Is_Active = 1 (activated accounts).
    
    Returns:
        dict: A dictionary with counts for placed, not placed, and activated accounts.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Count Placed and Not Placed
        query_placement = """
            SELECT Is_Placed, COUNT(*)
            FROM SSDD_COMPLETE_LOGIN
            GROUP BY Is_Placed
        """
        cursor.execute(query_placement)
        results = cursor.fetchall()

        # Initialize counts
        placement_counts = {"Placed": 0, "Not_Placed": 0, "Activated_Accounts": 0}

        # Process the query results
        for is_placed, count in results:
            if is_placed == 1:
                placement_counts["Placed"] = count
            elif is_placed == 0:
                placement_counts["Not_Placed"] = count

        # Count Activated Accounts separately
        query_active = """
            SELECT COUNT(*) 
            FROM SSDD_COMPLETE_LOGIN
            WHERE Is_Active = 1
        """
        cursor.execute(query_active)
        activated_count = cursor.fetchone()[0]  # Get the single count result
        placement_counts["Activated_Accounts"] = activated_count

        return placement_counts

    except Exception as e:
        print(f"Database error while counting placements: {e}")
        return {"Placed": 0, "Not_Placed": 0, "Activated_Accounts": 0}

    finally:
        if conn:
            conn.close()



            
            
            
            


# Count of registered accounts within 7 days
def count_recent_registrations():
    """
    Count the number of 'Learner' and 'Company' accounts registered in the last 7 days.
    Returns a dictionary with the counts.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Define the date range (last 7 days)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')

        query = """
            SELECT account_type, COUNT(*) 
            FROM SSDD__COMPLETE_REGISTER
            WHERE date_joined >= ?
            GROUP BY account_type
        """
        cursor.execute(query, (seven_days_ago,))
        results = cursor.fetchall()

        # ✅ Initialize counts
        account_counts = {
            "Learner": 0,
            "Company": 0
        }

        # ✅ Process the query results
        for account_type, count in results:
            if account_type in account_counts:
                account_counts[account_type] = count

        print(f"Recent Registrations: {account_counts}")  # Debugging Output
        return account_counts

    except Exception as e:
        print(f"Database error while counting recent registrations: {e}")
        return {"Learner": 0, "Company": 0}

    finally:
        if conn:
            conn.close()





#Dashboard administrator
@app.route('/MainDashboardForAdministrator')
def DashboardAdministrator():
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    distinct_data = get_distinct_elements()
    email = request.args.get('email', '').strip()
    
    
    
    fetch_all_applicant_results = function_fetch_all_applicant_results()
    



    return render_template('WelcomeAdministrator.html', distinct_data=distinct_data,recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, fetch_all_applicant_results=fetch_all_applicant_results 
                       
                            )   
    
 # Administrator inactive accounts and monthly sign up functions   
def fetch_incomplete_profiles_sign_up():
    """
    Fetch users who have not completed their personal information.
    
    Returns:
        list[dict]: A list of dictionaries containing incomplete profiles.
    """
    conn = None
    incomplete_profiles_sign_up = []
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT 
                l.Surname, 
                l.Email, 
                l.AccountType, 
                CONVERT(VARCHAR, r.date_joined, 120) AS date_joined
            FROM SSDD_COMPLETE_LOGIN l
            JOIN SSDD__COMPLETE_REGISTER r ON l.Email = r.email
            WHERE l.PersonalInforEntered = 0
            AND (l.AccountType != 'Administrator' OR l.AccountType != 'Company' OR l.AccountType IS NULL)
            ORDER BY r.date_joined DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # Convert results into a list of dictionaries
        incomplete_profiles_sign_up = [
            {
                "Surname": row[0],
                "Email": row[1],
                "AccountType": row[2],
                "Date_Created": row[3]  # Now stored as string instead of datetime2
            }
            for row in rows
        ]

        print(f"✅ [DEBUG] Fetched {len(incomplete_profiles_sign_up)} incomplete profiles")  # Debugging

    except Exception as e:
        print(f"❌ [DEBUG] Database error while fetching incomplete profiles: {e}")

    finally:
        if conn:
            conn.close()

    return incomplete_profiles_sign_up



 
 
 
    
# Administrator inactive profiles
@app.route('/MainDashboardForAdministratorInactiveProfiles')
def DashboardAdministratorInactiveProfiles():
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    distinct_data = get_distinct_elements()
    email = request.args.get('email', '').strip()
    fetch_all_applicant_results = function_fetch_all_applicant_results()
    incomplete_profiles_sign_up = fetch_incomplete_profiles_sign_up()
    
    
    
    



    return render_template('AdministratorInactiveProfiles.html', distinct_data=distinct_data,
                           recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, 
                           fetch_all_applicant_results=fetch_all_applicant_results,
                           incomplete_profiles_sign_up=incomplete_profiles_sign_up,
                           
                       
                            )   




# Monthly sign up functions
def count_monthly_registrations():
    """
    Retrieves the account type and date joined, extracts the Year and Month,
    and counts the number of 'Learner' and 'Company' accounts registered per month.

    Returns:
        list[dict]: A list of dictionaries containing:
                    - Year
                    - Month
                    - Learner Count
                    - Company Count
    """
    conn = None
    monthly_counts = defaultdict(lambda: {"Learner": 0, "Company": 0})  # Store counts by (year, month)

    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Convert `date_joined` to `DATE` format to avoid ODBC SQL type error
        query = """
            SELECT account_type, YEAR(date_joined) AS year, MONTH(date_joined) AS month
            FROM SSDD__COMPLETE_REGISTER
            WHERE date_joined IS NOT NULL
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Process each row and group by Year-Month
        for row in rows:
            account_type, year, month = row
            month_name = calendar.month_name[month]  # Convert month number to name

            if account_type in ["Learner", "Company"]:
                monthly_counts[(year, month)][account_type] += 1  # Increment count

        # ✅ Ensure all 12 months are included for the current year
        current_year = datetime.utcnow().year  # ✅ Get current year

        formatted_data = []
        for month in range(1, 13):  # ✅ Loop through January (1) to December (12)
            month_name = calendar.month_name[month]  # ✅ Convert to full month name
            
            formatted_data.append({
                "Year": current_year,
                "Month": month_name,
                "Learner_Count": monthly_counts.get((current_year, month), {}).get("Learner", 0),
                "Company_Count": monthly_counts.get((current_year, month), {}).get("Company", 0)
            })

        print(f"✅ [DEBUG] Processed Monthly Registration Data: {formatted_data}")  # Debugging Output
        return formatted_data

    except Exception as e:
        print(f"❌ Database error while fetching monthly registrations: {e}")
        return []

    finally:
        if conn:
            conn.close()

# filter option for monthly sign up accounts funtion
def count_monthly_registrations_filtered(start_date, end_date):
    """
    Retrieves the account type and date joined within a specific date range, extracts the Year and Month,
    and counts the number of 'Learner' and 'Company' accounts registered per month.

    Args:
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        list[dict]: A list of dictionaries containing:
                    - Year
                    - Month
                    - Learner Count
                    - Company Count
    """
    conn = None
    monthly_counts = defaultdict(lambda: {"Learner": 0, "Company": 0})  # Store counts by (year, month)

    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Convert `date_joined` to `DATE` format and apply the date range filter
        query = """
            SELECT account_type, YEAR(date_joined) AS year, MONTH(date_joined) AS month
            FROM SSDD__COMPLETE_REGISTER
            WHERE date_joined IS NOT NULL
            AND date_joined BETWEEN ? AND ?
        """
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()

        # ✅ Process each row and group by Year-Month
        for row in rows:
            account_type, year, month = row
            month_name = calendar.month_name[month]  # Convert month number to name

            if account_type in ["Learner", "Company"]:
                monthly_counts[(year, month)][account_type] += 1  # Increment count

        # ✅ Ensure all 12 months are included for the selected year range
        start_year = datetime.strptime(start_date, '%Y-%m-%d').year
        end_year = datetime.strptime(end_date, '%Y-%m-%d').year

        formatted_data = []
        for year in range(start_year, end_year + 1):  # Loop through each year in range
            for month in range(1, 13):  # ✅ Loop through January (1) to December (12)
                month_name = calendar.month_name[month]  # ✅ Convert to full month name
                
                formatted_data.append({
                    "Year": year,
                    "Month": month_name,
                    "Learner_Count": monthly_counts.get((year, month), {}).get("Learner", 0),
                    "Company_Count": monthly_counts.get((year, month), {}).get("Company", 0)
                })

        print(f"✅ [DEBUG] Filtered Monthly Registration Data: {formatted_data}")  # Debugging Output
        return formatted_data

    except Exception as e:
        print(f"❌ Database error while fetching filtered monthly registrations: {e}")
        return []

    finally:
        if conn:
            conn.close()


# The filtered monthly sign up app route
@app.route('/filter_monthly_signups', methods=['GET', 'POST'])
def filter_monthly_signups():
    """
    Handles filtering of monthly sign-ups based on a user-selected date range.
    """
    distinct_data = get_distinct_elements()
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    fetch_all_applicant_results = function_fetch_all_applicant_results()

    # ✅ Get start and end dates from the form submission
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    # ✅ If no filter is applied, default to showing the full year
    if not start_date or not end_date:
        current_year = datetime.utcnow().year
        start_date = f"{current_year}-01-01"
        end_date = f"{current_year}-12-31"

    print(f"🔍 Filtering from {start_date} to {end_date}")  # Debugging

    # ✅ Call the function with the selected date range
    monthly_signups = count_monthly_registrations_filtered(start_date, end_date)

    return render_template('AdministratorMonthlySignUps.html', distinct_data=distinct_data,
                           recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles,
                           recent_registrations=recent_registrations,
                           fetch_all_applicant_results=fetch_all_applicant_results,
                           monthly_signups=monthly_signups)





            
            
            

# Administrator monthly sign u
@app.route('/MainDashboardForAdministratorMonthlySignUps')
def DashboardAdministratorMonthlySignUps():
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    distinct_data = get_distinct_elements()
    email = request.args.get('email', '').strip()
    fetch_all_applicant_results = function_fetch_all_applicant_results()
    monthly_signups = count_monthly_registrations()
    



    return render_template('AdministratorMonthlySignUps.html', distinct_data=distinct_data,
                           recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, 
                           fetch_all_applicant_results=fetch_all_applicant_results,
                           monthly_signups=monthly_signups
                       
                            )   


# Function for approved and rejection learners
def fetch_company_decisions_by_outcome():
    """
    Fetch all decision outcome details from SSDD_COMPLETE_COMPANY_DECISION_OUTCOME
    and separate them into Approved and Rejected lists.

    Returns:
        dict: A dictionary with two lists:
              - "approve": List of approved decisions
              - "reject": List of rejected decisions
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # SQL Query to fetch all decision and personal info details
        query = """
            SELECT 
                d.email, 
                d.Decision_outcome, 
                d.Company_name, 
                d.Decision_date, 
                d.Decision_verdict, 
                p.lastname, 
                p.Gender, 
                p.Province, 
                p.Race, 
                p.Preferred_Opportunity
            FROM SSDD_COMPLETE_COMPANY_DECISION_OUTCOME d
            LEFT JOIN SSDD_COMPLETE_PERSONALINFO p ON d.email = p.email
            ORDER BY d.Decision_date DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        print(f" These are the total check [DEBUG] Total Rows Fetched: {len(rows)}")  # Debugging

        # Initialize separate lists for Approved and Rejected decisions
        approved_decisions = []
        rejected_decisions = []

        # Process query results
        for row in rows:
            decision_data = {
                "email": row[0],
                "Decision_outcome": row[1],
                "Company_name": row[2],
                "Decision_date": row[3],
                "Decision_verdict": row[4],
                "lastname": row[5],
                "Gender": row[6],
                "Province": row[7],
                "Race": row[8],
                "Preferred_Opportunity": row[9]
            }

            print(f"🔍 [DEBUG] Processing row: {decision_data}")  # Debugging

            if row[1] and row[1].strip() == "Approve":  # ✅ Ensure consistent lowercase comparison
                approved_decisions.append(decision_data)
            elif row[1] and row[1].strip() == "Reject":
                rejected_decisions.append(decision_data)

        print(f"✅ [DEBUG] Approved Count: {len(approved_decisions)}")  # Debugging
        print(f"✅ [DEBUG] Rejected Count: {len(rejected_decisions)}")  # Debugging

        return {
            "approve": approved_decisions,  # ✅ Use lowercase keys
            "reject": rejected_decisions
        }

    except Exception as e:
        print(f"❌ [DEBUG] Database error while fetching company decision data: {e}")
        return {"approve": [], "reject": []}

    finally:
        if conn:
            conn.close()







# Administrator non placement reports

@app.route('/MainDashboardForAdministratorNonPlacementReport')
def DashboardAdministratorNonPlacementReport():
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    distinct_data = get_distinct_elements()
    email = request.args.get('email', '').strip()
    fetch_all_applicant_results = function_fetch_all_applicant_results()
    decision_data = fetch_company_decisions_by_outcome()
    
    
    
    
    print(f"✅ [DEBUG] Non-Placement Learners (Rejected): {decision_data['reject']}")
    
    
    
    
    
    
    
    
    
    
    



    return render_template('AdministratorNonPlacementReport.html', distinct_data=distinct_data,
                           recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, 
                           fetch_all_applicant_results=fetch_all_applicant_results,
                           non_placement_learners=decision_data["reject"]
                       
                            )   






# Administrator placement reports

@app.route('/MainDashboardForAdministratorPlacementReport')
def DashboardAdministratorPlacementReport():
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    distinct_data = get_distinct_elements()
    email = request.args.get('email', '').strip()
    fetch_all_applicant_results = function_fetch_all_applicant_results()
    decision_data = fetch_company_decisions_by_outcome()
    
    
    
    
    print(f"Approved [DEBUG] Placement Learners (Approved): {decision_data['approve']}") 
    
    
    
   
    



    return render_template('AdministratorPlacementReport.html', distinct_data=distinct_data,
                           recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, 
                           fetch_all_applicant_results=fetch_all_applicant_results,
                           placement_learners=decision_data["approve"]
                       
                            )   






# Administrator cv download reports

@app.route('/MainDashboardForAdministratorCVDonwloadReport')
def DashboardAdministratorCVDonwloadReport():
    total_incomplete_profiles = count_incomplete_profiles()
    recent_registrations = count_recent_registrations()
    recent_placements = count_recent_placement_students()
    distinct_data = get_distinct_elements()
    email = request.args.get('email', '').strip()
    
    
    
    fetch_all_applicant_results = function_fetch_all_applicant_results()
    



    return render_template('AdministratorReportCVDownloads.html', distinct_data=distinct_data,recent_placements=recent_placements,
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, fetch_all_applicant_results=fetch_all_applicant_results 
                       
                            )   








# Filter applicant data
@app.route('/filter_applicants_admin', methods=['GET', 'POST'])
def filter_applicants():
    # ✅ Fetch distinct data (for dropdown lists)
    distinct_data = get_distinct_elements()
    recent_registrations = count_recent_registrations()
    total_incomplete_profiles = count_incomplete_profiles()
    recent_placements = count_recent_placement_students()

    # ✅ Get email from request (POST or GET)
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
    else:
        email = request.args.get('email', '').strip()

    # ✅ Debugging: Print email value
    print(f"🔍 Filtering applicants for email: {email}")

    # ✅ Get filter values from request.args (GET)
    Qualification = request.args.get('Qualification', '').strip()
    City = request.args.get('City_and_town_of_residence', '').strip()
    Disability = request.args.get('Disability', '').strip()
    Province = request.args.get('Province', '').strip()
    Academic_Institution = request.args.get('Academic_Institution', '').strip()
    Race = request.args.get('Race', '').strip()
    Gender = request.args.get('Gender', '').strip()
    Seeking_Placement = request.args.get('Seeking_Placement', '').strip()
    Preferred_Opportunity = request.args.get('Preferred_Opportunity', '').strip()

    # ✅ Dictionary to store only active filters
    active_filters = {
        "Qualification": Qualification,
        "City": City,
        "Disability": Disability,
        "Province": Province,
        "Academic_Institution": Academic_Institution,
        "Race": Race,
        "Gender": Gender,
        "Seeking_Placement": Seeking_Placement,
        "Preferred_Opportunity": Preferred_Opportunity
    }
    active_filters = {k: v for k, v in active_filters.items() if v}  # ✅ Remove empty values

    # ✅ If no filters are selected, return an empty result set
    if not active_filters and not email:
        print("❌ No filters or email provided. Returning default dashboard.")
        return render_template(
            'WelcomeAdministrator.html',
            distinct_data=distinct_data,
            recent_registrations=recent_registrations,
            incomplete_profiles=total_incomplete_profiles,
            results_filter_applicants_admin=[],
            recent_placements=recent_placements
        )

    # ✅ Build SQL Query for filtering applicants
    conn = None
    results = []
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT 
                p.firstname + ' ' + p.lastname AS name,
                COALESCE(e.Field_of_study, 'Not Provided') AS field_of_study,
                p.email,
                p.contact_number,
                p.Race,
                p.Gender,
                COALESCE(p.Seeking_Placement, 'Not Specified') AS seeking_placement,
                p.Province,
                p.City,
                e.Qualification,
                e.Academic_Institution,
                COALESCE(l.Is_Active, 0) AS Is_Active,  -- ✅ Defaults to 0 if NULL
                COALESCE(l.Is_Placed, 0) AS Is_Placed   -- ✅ Defaults to 0 if NULL
            FROM SSDD_COMPLETE_PERSONALINFO p
            LEFT JOIN SSDD_COMPLETE_EDUCATION_DETAILS e ON p.email = e.email
            LEFT JOIN SSDD_LOGIN l ON p.email = l.Email  -- ✅ Join with SSDD_LOGIN table
            WHERE 1=1
        """

        params = []
        if "Qualification" in active_filters:
            query += " AND COALESCE(e.Qualification, '') LIKE ?"
            params.append(f"%{active_filters['Qualification']}%")
        if "City" in active_filters:
            query += " AND COALESCE(p.City, '') LIKE ?"
            params.append(f"%{active_filters['City']}%")
        if "Disability" in active_filters:
            query += " AND COALESCE(p.Disability, '') = ?"
            params.append(active_filters["Disability"])
        if "Province" in active_filters:
            query += " AND COALESCE(p.Province, '') = ?"
            params.append(active_filters["Province"])
        if "Academic_Institution" in active_filters:
            query += " AND COALESCE(e.Academic_Institution, '') LIKE ?"
            params.append(f"%{active_filters['Academic_Institution']}%")
        if "Race" in active_filters:
            query += " AND COALESCE(p.Race, '') = ?"
            params.append(active_filters["Race"])
        if "Gender" in active_filters:
            query += " AND COALESCE(p.Gender, '') = ?"
            params.append(active_filters["Gender"])
        if "Seeking_Placement" in active_filters:
            query += " AND COALESCE(p.Seeking_Placement, '') = ?"
            params.append(active_filters["Seeking_Placement"])
        if "Preferred_Opportunity" in active_filters:
            query += " AND COALESCE(p.Preferred_Opportunity, '') = ?"
            params.append(active_filters["Preferred_Opportunity"])

        # ✅ Sort results by most recent entries using `p.id DESC`
        query += """
            GROUP BY p.id, p.firstname, p.lastname, p.email, p.contact_number, p.Race, p.Gender, 
                     p.Seeking_Placement, p.Province, p.City, e.Qualification, e.Academic_Institution, 
                     e.Field_of_study, l.Is_Active, l.Is_Placed
            ORDER BY p.id DESC
        """

        # ✅ Debugging - Print SQL Query & Params
        print("🔍 SQL Query:", query)
        print("🔍 Query Params:", params)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # ✅ Convert results into a list of dictionaries
        results = [
            {
                "name": row[0],
                "field_of_study": row[1],
                "email": row[2],
                "contact_number": row[3],
                "race": row[4],
                "gender": row[5],
                "seeking_placement": row[6],
                "province": row[7],
                "city": row[8],
                "qualification": row[9],
                "academic_institution": row[10],
                "is_active": "Active" if row[11] == 1 else "Inactive",  # ✅ Convert 1 -> "Yes", 0 -> "No"
                "is_placed": "Yes" if row[12] == 1 else "No"   # ✅ Convert 1 -> "Yes", 0 -> "No"
            }
            for row in rows
        ]

    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if conn:
            conn.close()

    return render_template(
        'WelcomeAdministrator.html',
        distinct_data=distinct_data,
        results_filter_applicants_admin=results,
        recent_registrations=recent_registrations,
        incomplete_profiles=total_incomplete_profiles,
        recent_placements=recent_placements,
       
    )


#View cv admin
@app.route('/Admin_view_all_cv')
def administratorViewCV():
    # ✅ Get email from query parameters
    email = request.args.get('email', '').strip()

    # ✅ Debugging: Print email received
    print(f"🔍 Fetching CV details for email: {email}")

    # ✅ Store email in session
    if email:
        session['current_student_email'] = email  # Store for later use
        print(f"📌 Email stored in session: {session['current_student_email']}")

    # ✅ Fetch distinct data
    distinct_data = get_distinct_elements()
    recent_registrations = count_recent_registrations()
    total_incomplete_profiles = count_incomplete_profiles()
    recent_placements = count_recent_placement_students()

    # ✅ Fetch CV data
    cv_data = fetch_combined_user_details(email)

    return render_template(
        'AdministratorViewCVForStudent.html',
        distinct_data=distinct_data,
        recent_registrations=recent_registrations,
        incomplete_profiles=total_incomplete_profiles,
        cv_data_admin_view_all_cv=cv_data,
        recent_placements=recent_placements
    )




# Admin redirecting to decision page
@app.route('/Admin_Decision_page_making')
def AdminDecisionMaking():
    # ✅ Retrieve email from session
    email = session.get('current_student_email', '')

    # ✅ Debugging: Print email from session
    print(f"📌 Email retrieved from session for decision-making: {email}")

    distinct_data = get_distinct_elements()
    recent_registrations = count_recent_registrations()
    total_incomplete_profiles = count_incomplete_profiles()
    cv_data = fetch_combined_user_details(email)
    recent_placements = count_recent_placement_students()

    return render_template(
        'AdministratorDecision.html',
        distinct_data=distinct_data,
        recent_registrations=recent_registrations,
        incomplete_profiles=total_incomplete_profiles,
        cv_data_admin_view_all_cv=cv_data,
        recent_placements=recent_placements
    )


    
    
@app.route('/Making_approval_or_refual_decision_on_learner', methods=['POST'])
def Making_approval_or_refual_decision_on_learner():
    try:
        # ✅ Get email from session (instead of form)
        email = session.get('current_student_email', '')

        # ✅ Debugging: Print email retrieved from session
        print(f"📌 Email retrieved from session for decision submission: {email}")

        # ✅ Get form data
        decision_outcome = request.form.get('admin_decision_on_learner')
        reason_for_rejection = request.form.get('reason_for_rejection', '')

        print("📌 Decision outcome selected:", decision_outcome)
        print("✏️ Reason for rejection:", reason_for_rejection)

        # ✅ Ensure the administrator is logged in
        administrator_email = session.get('email')  
        print("👤 Administrator email from session:", administrator_email)

        if not administrator_email:
            flash("Unauthorized access. Please log in first.", "danger")
            return redirect(url_for('login'))  

        # ✅ Ensure email is valid before inserting into database
        if not email:
            print("❌ ERROR: Email is missing!")
            flash("Error: No email provided for decision.", "danger")
            return redirect(url_for('DashboardAdministrator'))

        # ✅ Get current timestamp
        decision_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ✅ Connect to the database
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Insert into the Decision Outcome table
        cursor.execute("""
            INSERT INTO SSDD_COMPLETE_STUDENT_DECISION_OUTCOME (email, Decision_outcome, Administrator_name, Decision_date, Decision_verdict)
            VALUES (?, ?, ?, ?, ?)
        """, (email, decision_outcome, administrator_email, decision_date, reason_for_rejection))
        print("✅ Inserted decision into the database successfully!")

        # ✅ Check if the email exists in SSDD_COMPLETE_LOGIN
        cursor.execute("SELECT Is_Active FROM SSDD_COMPLETE_LOGIN WHERE email = ?", (email,))
        result = cursor.fetchone()

        if result:
            current_status = result[0]
            print(f"🔎 Current Is_Active status for {email}: {current_status}")

            # ✅ If decision is "Approve", set Is_Active = 1
            if decision_outcome == "Approve":
                print(f"🔄 Updating Is_Active to 1 for {email}")
                cursor.execute("""
                    UPDATE SSDD_COMPLETE_LOGIN
                    SET Is_Active = 1
                    WHERE email = ?
                """, (email,))

            # ✅ If decision is "Reject" and Is_Active is 1, set Is_Active = 0
            elif decision_outcome == "Reject" and current_status == 1:
                print(f"🔄 Updating Is_Active to 0 for {email} (Rejection rollback)")
                cursor.execute("""
                    UPDATE SSDD_COMPLETE_LOGIN
                    SET Is_Active = 0
                    WHERE email = ?
                """, (email,))

        else:
            print(f"❌ Email {email} not found in SSDD_COMPLETE_LOGIN. No update performed.")

        # ✅ Commit changes and close connection
        conn.commit()
        print("✅ Database changes committed!")
        cursor.close()
        conn.close()

        flash("Decision submitted successfully.", "success")
        return redirect(url_for('DashboardAdministrator'))  

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        print("❌ Database error:", str(e))
        return redirect(url_for('DashboardAdministrator'))  











































# personal information 
@app.route('/personalInfo', methods=['GET', 'POST'])
def dashboardPersonalInformation():
    distinct_data = get_distinct_elements()

    if request.method == 'POST':
        email = session.get('email')

        # ✅ Retrieve all form fields correctly
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        date_of_birth = request.form.get('date_of_birth')
        id_number = request.form.get('id_number')
        address = request.form.get('address')
        City = request.form.get('City')
        Postal_code = request.form.get('Postal_code')
        Province = request.form.get('Province')
        Contact_number = request.form.get('Contact_number')
        Race = request.form.get('Race')
        Gender = request.form.get('Gender')
        Seeking_Placement = request.form.get('Seeking_Placement')
        Preferred_Opportunity = request.form.get('Preferred_Opportunity')
        Citizenship = request.form.get('Citizenship')
        Willing_to_Relocate = request.form.get('Willing_to_Relocate')
        Disability = request.form.get('Disability')

        # ✅ Retrieve multiple selected languages correctly
        selected_languages = request.form.getlist('Language')
        Language = ', '.join(selected_languages) if selected_languages else ""

        About_yourself = request.form.get('About_yourself')
        Self_Picture = request.files.get('Self_Picture')

        # ✅ Debugging: Check retrieved values
        print(f"Debug: email={email}, firstname={firstname}, lastname={lastname}, Language={Language}")

        # ✅ Prevent empty 'firstname' from breaking the database
        if not firstname:
            flash("First Name is missing. Please complete the form.", "danger")
            return redirect('/personalInfo')

        if not email:
            flash("Session expired. Please log in again.", "danger")
            return redirect('/login')

        # ✅ Read and process the uploaded file (if any)
        if Self_Picture and Self_Picture.filename:
            Self_Picture = Self_Picture.read()
        else:
            Self_Picture = None  # Keep it None if no file is uploaded

        # ✅ Connect to database and insert data safely
        conn = None
        try:
            conn = get_db_connection('WorkflowDB')
            cursor = conn.cursor()
            #Insert into the personal information table
            query = """
            INSERT INTO SSDD_COMPLETE_PERSONALINFO 
            (email, firstname, lastname, date_of_birth, id_number, address, City, Postal_code, Province, 
             contact_number, Race, Gender, Seeking_Placement, Preferred_Opportunity, Citizenship, 
             Willing_to_Relocate, Disability, Language, About_yourself, Self_Picture)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            #Insert into the combined table
            
        

            cursor.execute(query, (
                email, firstname or "", lastname or "", date_of_birth or "", 
                id_number or "", address or "", City or "", Postal_code or "", 
                Province or "", Contact_number or "", Race or "", Gender or "", 
                Seeking_Placement or "", Preferred_Opportunity or "", Citizenship or "", 
                Willing_to_Relocate or "", Disability or "", Language, 
                About_yourself or "", pyodbc.Binary(Self_Picture) if Self_Picture else None
            ))

            conn.commit()
            flash('Personal information entered successfully!', 'success')
            return redirect('/education')

        except Exception as e:
            print(f"Database error: {e}")
            flash(f"Database error: {e}", 'danger')
            return redirect('/personalInfo')

        finally:
            if conn:
                conn.close()

    return render_template('studentpersonalinformation.html', distinct_data=distinct_data)






# Education
@app.route('/education', methods=['GET', 'POST'])
def dashboardEducation():
    distinct_data = get_distinct_elements()

    if request.method == 'POST':
        email = session.get('email')

        if not email:
            flash("Session expired. Please log in again.", "danger")
            return redirect('/login')

        # ✅ Retrieve all form inputs as lists
        academic_institutions = request.form.getlist('Academic_Institution[]')
        qualifications = request.form.getlist('Qualification[]')
        fields_of_study = request.form.getlist('Field_of_study[]')
        completion_statuses = request.form.getlist('Completion_status[]')
        countries = request.form.getlist('Country[]')
        cities = request.form.getlist('City[]')

        # ✅ Debugging - print to verify form data
        print(f"Debug: email={email}, Institutions={academic_institutions}, Qualifications={qualifications}")

        # ✅ Ensure at least one entry exists
        if not academic_institutions or not qualifications:
            flash("Please enter at least one education record.", "danger")
            return redirect('/education')

        conn = None
        try:
            conn = get_db_connection('WorkflowDB')
            cursor = conn.cursor()

            # ✅ Loop through all education entries and insert into the database
            for i in range(len(academic_institutions)):
                institution = academic_institutions[i] if i < len(academic_institutions) else None
                qualification = qualifications[i] if i < len(qualifications) else None
                field = fields_of_study[i] if i < len(fields_of_study) else None
                status = completion_statuses[i] if i < len(completion_statuses) else None
                country = countries[i] if i < len(countries) else None
                city = cities[i] if i < len(cities) else None

                if not institution or not qualification:
                    continue  # Skip invalid entries

                # ✅ Insert each entry into the database
                query = """
                INSERT INTO SSDD_COMPLETE_EDUCATION_DETAILS
                (email, Academic_Institution, Qualification, Field_of_study, Completion_status, Country, City)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (email, institution, qualification, field, status, country, city))

            conn.commit()
            flash('Education details submitted successfully!', 'success')
            return redirect('/workHistory')

        except Exception as e:
            print(f"Database error: {e}")
            flash('An error occurred while submitting your education details. Please try again.', 'danger')
            return redirect('/education')

        finally:
            if conn:
                conn.close()

    return render_template('studenteducation.html', distinct_data=distinct_data)




# Work History


@app.route('/workHistory', methods=['GET', 'POST'])
def workHistory():
    distinct_data = get_distinct_elements()

    if 'email' not in session:
        flash('Please log in to submit your work history.', 'error')
        return redirect('/')

    email = session['email']
    today_date = datetime.today().strftime('%Y-%m-%d')  # Get current date

    if request.method == 'POST':
        employer_names = request.form.getlist('employer_names[]')
        job_titles = request.form.getlist('job-title[]')
        current_place_of_employment = request.form.getlist('current_place_of_employment[]')
        start_dates = request.form.getlist('start-date[]')
        end_dates = request.form.getlist('end-date[]')  # May be shorter
        job_descriptions = request.form.getlist('job-description[]')

        # 🔍 Debugging
        print("Captured Work History Form Data:")
        print("Employer Names:", employer_names)
        print("Job Titles:", job_titles)
        print("Current Place of Employment:", current_place_of_employment)
        print("Start Dates:", start_dates)
        print("End Dates Before Fix:", end_dates)  # Log end_dates before fixing
        print("Job Descriptions:", job_descriptions)

        # 🔹 Ensure end_dates has the same length as other fields
        adjusted_end_dates = []
        end_date_index = 0  # To track positions in the end_dates list

        for i in range(len(employer_names)):
            if current_place_of_employment[i] == "Yes":
                adjusted_end_dates.append(None)  # Set NULL for currently employed
            else:
                if end_date_index < len(end_dates):  # If there's a corresponding end_date
                    adjusted_end_dates.append(end_dates[end_date_index])
                    end_date_index += 1
                else:
                    adjusted_end_dates.append(None)  # Fallback in case of missing data

        # 🔍 Debugging - check after correction
        print("End Dates After Fix:", adjusted_end_dates)

        # Ensure equal-length lists using zip()
        conn = None
        try:
            conn = get_db_connection('WorkflowDB')
            cursor = conn.cursor()

            for i, (employer_name, job_title, current_employment, start_date, end_date, job_description) in enumerate(
                zip(employer_names, job_titles, current_place_of_employment, start_dates, adjusted_end_dates, job_descriptions)
            ):
                # ✅ Validate start vs end date only when "No" is selected
                if current_employment == "No":
                    if not end_date:
                        flash(f"End date missing for job entry {i+1}. Please provide an end date.", "danger")
                        return redirect('/workHistory')

                    try:
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

                        if start_dt > end_dt:
                            flash(f"Start date cannot be greater than end date for job {i+1}.", "danger")
                            return redirect('/workHistory')

                    except ValueError:
                        flash(f"Invalid date format for job {i+1}. Please enter a valid date.", "danger")
                        return redirect('/workHistory')

                # ✅ Debugging output before inserting
                print(f"✅ Inserting Entry {i+1} into Database:")
                print(f"  Email: {email}")
                print(f"  Employer: {employer_name}")
                print(f"  Job Title: {job_title}")
                print(f"  Current Employment: {current_employment}")
                print(f"  Start Date: {start_date}")
                print(f"  End Date: {end_date if end_date else 'NULL'}")
                print(f"  Job Description: {job_description}")

                # ✅ Insert into the database
                query = """
                    INSERT INTO SSDD_COMPLETE_WORK_HISTORY
                    (email, employer_names, job_titles, current_place_of_employment, start_date, end_date, job_description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (email, employer_name, job_title, current_employment, start_date, end_date, job_description))

            conn.commit()
            flash('Work history details submitted successfully!', 'success')

            return redirect('/skills')

        except Exception as e:
            print(f"Database error: {e}")
            flash(f'Database error: {e}', 'error')
            return redirect('/workHistory')

        finally:
            if conn:
                conn.close()

    return render_template('studentworkhistory.html', distinct_data=distinct_data)





# Skills
@app.route('/skills', methods=['GET', 'POST'])
def dashboardskills():
    distinct_data = get_distinct_elements()
    if request.method == 'POST':
        # Check if the user is logged in
        if 'email' not in session:
            flash('Please log in to submit your work history.', 'error')
            return redirect('/')

        email = session['email']  # Email from the logged-in user

        # Retrieve form data
        skills = request.form.getlist('skills[]')
        proficiency = request.form.getlist('proficiency[]')
       

        conn = None
        try:
            # Connect to the database
            conn = get_db_connection('WorkflowDB')
            cursor = conn.cursor()

            # Insert work history details into the database
            for skills , proficiency in zip(skills , proficiency):
                query = """
                    INSERT INTO SSDD_COMPLETE_SKILLS
                    (email, skills, proficiency)
                    VALUES (?, ?, ?)
                """
                cursor.execute(query, (email, skills, proficiency))

            conn.commit()
            flash('Skills details submitted successfully!', 'success')
            return redirect('/Attachment')

        except Exception as e:
            print(f"Database error: {e}")
            flash('An error occurred while submitting your Skills details. Please try again.', 'error')
            return redirect('/skills')

        finally:
            if conn:
                conn.close()

    # Render the form for GET requests
    return render_template('studentskills.html', distinct_data=distinct_data)





# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
UPLOAD_FOLDER = 'uploads'  # Folder to store uploaded files

# Configure Flask to use the upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    """
    Check if the file has an allowed extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS






@app.route('/Attachment', methods=['GET', 'POST'])
def dashboardAttachment():
    distinct_data = get_distinct_elements()

    if 'email' not in session:
        flash('Please log in to upload documents.', 'error')
        return redirect('/')

    email = session['email']  # Get the logged-in user's email

    if request.method == 'POST':
        # ✅ Retrieve document types and uploaded files
        document_types = request.form.getlist('document-type[]')
        files = request.files.getlist('document-upload[]')

        print("✅ Received Form Data")  # Debugging output
        print(f"Document Types: {document_types}")
        print(f"Uploaded Files: {[file.filename for file in files]}")

        if not document_types or not files:
            flash('No files or document types provided.', 'error')
            return redirect('/Attachment')

        conn = None
        try:
            # ✅ Connect to the database
            conn = get_db_connection('WorkflowDB')
            cursor = conn.cursor()

            file_uploaded = False  # Track if at least one file is successfully uploaded

            for doc_type, file in zip(document_types, files):
                if file and allowed_file(file.filename):
                    # ✅ Debugging: Print file details
                    print(f"Uploading File: {file.filename} of type {doc_type}")

                    # ✅ Save file
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)  # ✅ Save file to the uploads folder

                    print(f"✅ File saved to: {file_path}")  # Debugging Output

                    # ✅ Get file format
                    file_format = filename.rsplit('.', 1)[1].lower()

                    # ✅ Insert file metadata into the database
                    query = """
                        INSERT INTO SSDD_COMPLETE_UPLOADED_DOCUMENTS 
                        (email, document_type, file_name, file_format, uploaded_at)
                        VALUES (?, ?, ?, ?, GETDATE())
                    """
                    cursor.execute(query, (email, doc_type, filename, file_format))

                    file_uploaded = True  # ✅ Mark as successful upload

                  
                else:
                    
                    flash(f"Invalid file format for {file.filename}", 'error')

            if file_uploaded:
                # ✅ Update `PersonalInforEntered` column in `SSDD_COMPLETE_LOGIN` table
                update_query = """
                    UPDATE SSDD_COMPLETE_LOGIN
                    SET PersonalInforEntered = 1
                    WHERE Email = ?
                """
                cursor.execute(update_query, (email,))
                print(f"✅ Updated PersonalInforEntered for {email}")  # Debugging output

            conn.commit()  # ✅ Ensure changes are committed
            print("✅ File successfully inserted into the database and login info updated!")  # Debugging Output

            flash('Documents uploaded successfully! Your profile has been updated.', 'success')
            return redirect('/MainDashboardStudent')

        except Exception as e:
            print(f"❌ Error: {e}")
            flash('An error occurred while uploading documents.', 'error')
            return redirect('/Attachment')

        finally:
            if conn:
                conn.close()

    return render_template('studentdocuments.html', distinct_data=distinct_data)








# Upload file
@app.route('/uploads/<filename>')
def download_file(filename):
    """
    Serve the uploaded file for download.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)




@app.route('/MainDashboardStudent')
def Studentdashboardinformation():
    distinct_data = get_distinct_elements()



    return render_template('WelcomeStudent.html', distinct_data=distinct_data)






# Generate cv function 
# 1. Personal information function 
def fetch_personal_info(email):
    """
    Fetch personal information for a given email from the SSDD_PERSONALINFO table.

    :param email: Email of the user (retrieved from session during login)
    :return: A dictionary containing the personal information, or None if not found
    """
    conn = None
    try:
        # Connect to the database
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Updated query without 'age'
        query = """
            SELECT email, firstname, lastname, date_of_birth, id_number,address, City, Postal_code, Province, contact_number
                   Race, Gender, Seeking_Placement, Preferred_Opportunity, Citizenship, Willing_to_Relocate, Disability,
                   Language, About_yourself, Self_Picture
            FROM SSDD_COMPLETE_PERSONALINFO
            WHERE email = ?
        """
        cursor.execute(query, (email,))
        result = cursor.fetchone()

        if result:
            # Updated keys to match the new query
            keys = [
                    "email", "firstname", "lastname", "date_of_birth", "id_number","address", "City", "Postal_code", "Province", "contact_number"
                   "Race", "Gender", "Seeking_Placement", "Preferred_Opportunity", "Citizenship", "Willing_to_Relocate", "Disability",
                   "Language", "About_yourself", "Self_Picture"
            
            
            ]
            personal_info = dict(zip(keys, result))
            return personal_info
        else:
            # Return None if no record is found
            return None

    except Exception as e:
        print(f"Database error: {e}")
        return None

    finally:
        if conn:
            conn.close()
            
            
# 2. Educational information 
def fetch_education_details(email):
    """
    Fetch education details for the given email from the database.

    Args:
        email (str): User's email address.

    Returns:
        list[dict]: A list of dictionaries containing education details.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT Academic_Institution, Qualification, 
                   Field_of_study, Completion_status, Country, City
            FROM SSDD_COMPLETE_EDUCATION_DETAILS
            WHERE email = ?
            AND (Academic_Institution IS NOT NULL OR Qualification IS NOT NULL 
                 OR Field_of_study IS NOT NULL OR Completion_status IS NOT NULL 
                 OR Country IS NOT NULL OR City IS NOT NULL)
        """
        cursor.execute(query, (email,))
        rows = cursor.fetchall()

        # Convert the results into a list of dictionaries
        education_details = [
            {
                "Academic_Institution": row[0],
                "Qualification": row[1],
                "Field_of_study": row[2],
                "Completion_status": row[3],
                "Country": row[4],
                "City": row[5]
            }
            for row in rows
        ]

        return education_details

    except Exception as e:
        print(f"Database error while fetching education details: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
# 3. Work history 
def fetch_work_history_details(email):
    """
    Fetch education details for the given email from the database.

    Args:
        email (str): User's email address.

    Returns:
        list[dict]: A list of dictionaries containing education details.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT employer_names, job_titles, current_place_of_employment, start_date, end_date, job_description
            FROM SSDD_COMPLETE_WORK_HISTORY
            WHERE email = ?
            AND (employer_names IS NOT NULL OR job_titles IS NOT NULL 
                 OR current_place_of_employment IS NOT NULL OR start_date IS NOT NULL 
                 OR end_date IS NOT NULL OR job_description IS NOT NULL)
        """
        cursor.execute(query, (email,))
        rows = cursor.fetchall()

        # Convert the results into a list of dictionaries
        work_history_details = [
            {
                "employer_names": row[0],
                "job_titles": row[1],
                "current_place_of_employment": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "job_description": row[5]
            }
            for row in rows
        ]

        return work_history_details

    except Exception as e:
        print(f"Database error while fetching education details: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
            
#4. Skills
def fetch_skills_details(email):
    """
    Fetch education details for the given email from the database.

    Args:
        email (str): User's email address.

    Returns:
        list[dict]: A list of dictionaries containing education details.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT skills, proficiency
            FROM SSDD_COMPLETE_SKILLS
            WHERE email = ?
            AND (skills IS NOT NULL OR proficiency IS NOT NULL)
        """
        cursor.execute(query, (email,))
        rows = cursor.fetchall()

        # Convert the results into a list of dictionaries
        skills_details = [
            {
                "skills": row[0],
                "proficiency": row[1]
            }
            for row in rows
        ]

        return skills_details

    except Exception as e:
        print(f"Database error while fetching education details: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
            
# 5. Uploaded document function
def fetch_uploaded_documents(email):
    """
    Fetch uploaded documents for the given email from the SSDD_COMPLETE_UPLOADED_DOCUMENTS table.
    """
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT document_type, file_name, file_format, uploaded_at
            FROM SSDD_COMPLETE_UPLOADED_DOCUMENTS
            WHERE email = ?
        """
        cursor.execute(query, (email,))
        rows = cursor.fetchall()

        if rows:
            # ✅ Convert results to a list of dictionaries
            uploaded_documents = [
                {
                    "document_type": row[0],
                    "file_name": row[1],
                    "file_format": row[2],
                    "uploaded_at": row[3]
                }
                for row in rows
            ]
            return uploaded_documents
        else:
            return []  # ✅ Return empty list if no files are found

    except Exception as e:
        print(f"Database error while fetching uploaded documents: {e}")
        return []
    finally:
        if conn:
            conn.close()
 
            



# Generate CV
@app.route('/generateCV')
def dashboardGenerateCV():
    distinct_data = get_distinct_elements()
    email = session.get('email')
    
    if not email:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('index'))  

    personal_info = fetch_personal_info(email)  
    education_details = fetch_education_details(email)  
    work_history = fetch_work_history_details(email)  
    skills_details = fetch_skills_details(email)
    uploaded_documents = fetch_uploaded_documents(email)  # ✅ Make sure it's fetched

    return render_template(
        'GeneratedCVStudent.html',
        personal_info=personal_info,
        education_details=education_details,
        work_history=work_history,
        distinct_data=distinct_data, 
        skills_details=skills_details,
        uploaded_documents=uploaded_documents  # ✅ Ensure this is passed
    )

    
    


  
# Download CV

# Define the folder to store PDFs
PDF_FOLDER = "/Generated_CV_FORMAT/Your Name.pdf"
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

@app.route('/download_cv_pdf')
def download_cv_pdf():
    distinct_data = get_distinct_elements()
    email = session.get('email')

    if not email:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('index'))

    personal_info = fetch_personal_info(email)
    education_details = fetch_education_details(email)
    work_history = fetch_work_history_details(email)
    skills_details = fetch_skills_details(email)
    uploaded_documents = fetch_uploaded_documents(email)

    html_content = render_template(
        'GeneratedCVStudent.html',
        personal_info=personal_info,
        education_details=education_details,
        work_history=work_history,
        skills_details=skills_details,
        uploaded_documents=uploaded_documents,
        distinct_data=distinct_data
    )

    # ✅ Add explicit font face to fix missing fonts issue
    css = CSS(string='''
        @font-face {
            font-family: "Arial";
            src: url("C:/Windows/Fonts/ariblk.ttf");
        }
        body { font-family: "Arial", sans-serif; font-size: 12px; color: #333; }
    ''')

    # Define file path
    pdf_filename = f"{personal_info['firstname']}_{personal_info['lastname']}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)

    try:
        # ✅ Generate and save PDF with correct fonts
        HTML(string=html_content).write_pdf(pdf_path, stylesheets=[css])
    except Exception as e:
        print(f"❌ PDF Generation Error: {e}")
        flash("An error occurred while generating the PDF.", "danger")
        return redirect(url_for('dashboardGenerateCV'))

    return send_file(pdf_path, as_attachment=True, download_name="Generated_CV.pdf")




# Function to fetch admin feedback
def fetch_admin_feedback_for_student_account(email):
    conn = None
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        query = """
            SELECT TOP 1 Decision_outcome, Decision_verdict
            FROM SSDD_COMPLETE_STUDENT_DECISION_OUTCOME
            WHERE email = ?
            ORDER BY Decision_date DESC
        """
        cursor.execute(query, (email,))
        row = cursor.fetchone()  # Fetch only the latest record

        if row:
            admin_decision_feedback_on_student = {
                "status_outcome": row[0],
                "Status_reason": row[1]
            }
            print("DEBUG: Retrieved Most Recent Data ->", admin_decision_feedback_on_student)  # ✅ Debugging
            return admin_decision_feedback_on_student  # ✅ Returning a single dictionary
        else:
            print("DEBUG: No records found for", email)  # ✅ Debug Empty Result
            return None

    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()




# Student Admin Feedback

@app.route('/StudentAdminintratorFeedback')
def GetAfminFeedbackAccountStatusReport():
    distinct_data = get_distinct_elements()
    email = session.get('email')

    if not email:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('index'))

    personal_info = fetch_personal_info(email)
    education_details = fetch_education_details(email)
    work_history = fetch_work_history_details(email)
    skills_details = fetch_skills_details(email)
    uploaded_documents = fetch_uploaded_documents(email)
    admin_feedback_on_account = fetch_admin_feedback_for_student_account(email)
    
    
    
    
    
    
    
    
    
    return render_template('StudentAdminFeedbackStatus.html', personal_info=personal_info,
        education_details=education_details,
        work_history=work_history,
        skills_details=skills_details,
        uploaded_documents=uploaded_documents,
        distinct_data=distinct_data,
        admin_feedback_on_account=admin_feedback_on_account)







if __name__ == '__main__':
    app.run(port=8060,debug=True)