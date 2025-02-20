import numpy as np
from flask import Flask, request, render_template, redirect, session, url_for, jsonify, flash, send_from_directory, make_response,send_file
import matplotlib.pyplot as plt
import matplotlib
import pyodbc
import uuid
import random
from weasyprint import HTML, CSS

from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from itertools import zip_longest  # Import to handle missing values

import math
import os

matplotlib.use('Agg')  # Use a non-GUI backend

app = Flask(__name__)
app.secret_key = 'secret_key'


def get_db_connection(database_name):
    s = 'APB-JBS02-02L'
    u = 'GENERALADMINISTRATOR'
    p = 'GENERALADMIN@12345'
    cstr = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s};DATABASE={database_name};UID={u};PWD={p}'
    conn = pyodbc.connect(cstr)
    return conn





# Generate cv function 
# 1. Personal information function 

            
            
# 2. Educational information 


# 3. Work history 

            
            
# 4. Upload document

            
            
# Getting unique element for company 



 



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
            """, (username, email, password, account_type, 0, datetime.utcnow(), 0, company_name, sdl_number))

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



    return render_template('studentDashboardInfo.html', distinct_data=distinct_data)   


# Dashbaord company
@app.route('/MainDashboardForCompany')
def DashboardCompany():
    distinct_data = get_distinct_elements()



    return render_template('WelcomeCompany.html', distinct_data=distinct_data)   


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
    distinct_data = get_distinct_elements()
    # email = request.args.get('email', '').strip()
    
    
    
    all_applicant_results = fetch_applicant_details()
    # personal_info = fetch_personal_info(email)
    # education_details = fetch_education_details(email)
    # work_history = fetch_work_history_details(email)
    # skills_details = fetch_skills_details(email)
    # uploaded_documents = fetch_uploaded_documents(email)



    return render_template('WelcomeAdministrator.html', distinct_data=distinct_data, 
                           incomplete_profiles=total_incomplete_profiles, 
                           recent_registrations=recent_registrations, all_applicant_results =all_applicant_results, 
                        #    personal_info=personal_info, education_details=education_details,
                        #     work_history=work_history,skills_details=skills_details,
                        #     uploaded_documents=uploaded_documents
                            )   

# Fetch all applicant results
def fetch_applicant_details():
    """
    Fetch distinct applicants by email, selecting only one entry per email.
    Orders by the most recent entries first.
    """
    conn = None
    results = []
    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # ✅ Updated query: Get DISTINCT email, most recent records first
        query = """
            SELECT 
                p.firstname + ' ' + p.lastname AS name,
                COALESCE(MAX(e.Field_of_study), 'Not Provided') AS field_of_study,
                p.email,
                p.contact_number,
                COALESCE(p.Seeking_Placement, 'Not Specified') AS seeking_placement
            FROM SSDD_COMPLETE_PERSONALINFO p
            LEFT JOIN SSDD_COMPLETE_EDUCATION_DETAILS e ON p.email = e.email
            GROUP BY p.id, p.firstname, p.lastname, p.email, p.contact_number, p.Seeking_Placement
            ORDER BY p.id DESC  -- ✅ Orders most recent entries at the top
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Convert fetched data into a list of dictionaries
        results = [
            {
                "name": row[0],
                "field_of_study": row[1],
                "email": row[2],
                "contact_number": row[3],
                "seeking_placement": row[4]
            }
            for row in rows
        ]

        # 🔍 Debugging: Print fetched data
        print("🔍 Debugging - Fetched Applicants (Ordered & Unique):", results)

    except Exception as e:
        print(f"Database error while fetching applicant details: {e}")
    finally:
        if conn:
            conn.close()

    return results





# Filter applicant data
@app.route('/filter_applicants_admin', methods=['GET', 'POST'])
def filter_applicants():
    # ✅ Fetch distinct data (for dropdown lists)
    distinct_data = get_distinct_elements()
    recent_registrations = count_recent_registrations()
    total_incomplete_profiles = count_incomplete_profiles()

    # ✅ Get email from request (POST or GET)
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
    else:
        email = request.args.get('email', '').strip()

    # ✅ Debugging: Print email value
    print(f"🔍 Filtering applicants for email: {email}")

    # ✅ Fetch applicant details only if email exists
    # personal_info = education_details = work_history = skills_details = uploaded_documents = None
    # if email:
    #     personal_info = fetch_personal_info(email)
    #     education_details = fetch_education_details(email)
    #     work_history = fetch_work_history_details(email)
    #     skills_details = fetch_skills_details(email)
    #     uploaded_documents = fetch_uploaded_documents(email)

        # ✅ Debugging: Print fetched records
        # print("🔍 Personal Info:", personal_info)
        # print("🔍 Education Details:", education_details)
        # print("🔍 Work History:", work_history)
        # print("🔍 Skills Details:", skills_details)
        # print("🔍 Uploaded Documents:", uploaded_documents)

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
            # personal_info=personal_info,
            # education_details=education_details,
            # work_history=work_history,
            # skills_details=skills_details,
            # uploaded_documents=uploaded_documents,
            results=[]
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
                e.Academic_Institution
            FROM SSDD_COMPLETE_PERSONALINFO p
            LEFT JOIN SSDD_COMPLETE_EDUCATION_DETAILS e ON p.email = e.email
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
                     p.Seeking_Placement, p.Province, p.City, e.Qualification, e.Academic_Institution, e.Field_of_study
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
        results=results,
        recent_registrations=recent_registrations,
        incomplete_profiles=total_incomplete_profiles,
        # personal_info=personal_info,
        # education_details=education_details,
        # work_history=work_history,
        # skills_details=skills_details,
        # uploaded_documents=uploaded_documents
    )

# Generate cv admin function 
def admin_get_cv_data(email):
    """
    Fetch all CV-related data for a given email and return it as a dictionary.
    This function consolidates:
    - Personal Information
    - Education Details
    - Work History
    - Skills Details
    - Uploaded Documents

    Args:
        email (str): The email of the applicant whose CV data is being fetched.

    Returns:
        dict: A dictionary containing all fetched data, structured for easy rendering.
    """

    # ✅ Initialize dictionary with default empty values
    cv_data = {
        "personal_info": None,
        "education_details": [],
        "work_history": [],
        "skills_details": [],
        "uploaded_documents": []
    }

    if email:
        print(f"🔍 Fetching CV details for email: {email}")

        # ✅ Fetch each data component
        cv_data["personal_info"] = fetch_personal_info(email) or None
        cv_data["education_details"] = fetch_education_details(email) or []
        cv_data["work_history"] = fetch_work_history_details(email) or []
        cv_data["skills_details"] = fetch_skills_details(email) or []
        cv_data["uploaded_documents"] = fetch_uploaded_documents(email) or []

        # ✅ Debugging: Print results
        print("✅ Fetched CV Data:")
        print(f"   - Personal Info: {cv_data['personal_info']}")
        print(f"   - Education Details: {cv_data['education_details']}")
        print(f"   - Work History: {cv_data['work_history']}")
        print(f"   - Skills Details: {cv_data['skills_details']}")
        print(f"   - Uploaded Documents: {cv_data['uploaded_documents']}")
    
    return cv_data




#View cv admin
@app.route('/Admin_view_all_cv')
def administratorViewCV():
    # ✅ Get email from query parameters
    email = request.args.get('email', '').strip()

    # ✅ Debugging: Print email received
    print(f"🔍 Fetching CV details for email: {email}")

    # ✅ Fetch distinct data (for dropdowns)
    distinct_data = get_distinct_elements()
    recent_registrations = count_recent_registrations()
    total_incomplete_profiles = count_incomplete_profiles()
    
    
    cv_data = admin_get_cv_data(email)

    # ✅ If no email is provided, return with an error message
    if not email:
        print("❌ No email provided. Returning default administrator dashboard.")
        return render_template(
            'WelcomeAdministrator.html',
            distinct_data=distinct_data,
            recent_registrations=recent_registrations,
            incomplete_profiles=total_incomplete_profiles,
            # personal_info=personal_info,
            # education_details=education_details,
            # work_history=work_history,skills_details=skills_details,
            # uploaded_documents=uploaded_documents
        )

    # ✅ Fetch records for the provided email
    # personal_info = fetch_personal_info(email)
    # education_details = fetch_education_details(email)
    # work_history = fetch_work_history_details(email)
    # skills_details = fetch_skills_details(email)
    # uploaded_documents = fetch_uploaded_documents(email)

    # ✅ Debugging: Print fetched records
    # print("🔍 Personal Info:", personal_info)
    # print("🔍 Education Details:", education_details)
    # print("🔍 Work History:", work_history)
    # print("🔍 Skills Details:", skills_details)
    # print("🔍 Uploaded Documents:", uploaded_documents)

    # ✅ For now, return to the admin dashboard without rendering these details
    return render_template(
        'WelcomeAdministrator.html',
        distinct_data=distinct_data,
        recent_registrations=recent_registrations,
        incomplete_profiles=total_incomplete_profiles,
        cv_data=cv_data
        # personal_info=personal_info,
        # education_details=education_details,
        # work_history=work_history,skills_details=skills_details,
        # uploaded_documents=uploaded_documents
        
    )
 # Make sure this file is in the "templates/" folder









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

            query = """
            INSERT INTO SSDD_COMPLETE_PERSONALINFO 
            (email, firstname, lastname, date_of_birth, id_number, address, City, Postal_code, Province, 
             contact_number, Race, Gender, Seeking_Placement, Preferred_Opportunity, Citizenship, 
             Willing_to_Relocate, Disability, Language, About_yourself, Self_Picture)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

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










if __name__ == '__main__':
    app.run(port=8060,debug=True)