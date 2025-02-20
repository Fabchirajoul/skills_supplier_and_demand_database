
from db_utils import get_db_connection
import random
from datetime import datetime
import pyodbc




def get_db_connection(database_name):
    s = 'APB-JBS02-02L'
    u = 'GENERALADMINISTRATOR'
    p = 'GENERALADMIN@12345'
    cstr = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s};DATABASE={database_name};UID={u};PWD={p}'
    conn = pyodbc.connect(cstr)
    return conn







# Fetch all applicant results
def function_fetch_all_applicant_results():
    """
    Fetch distinct applicants by email, selecting only one entry per email.
    Orders by the most recent entries first.
    """
    conn = None
    fetch_all_applicant_results = []
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
                COALESCE(p.Seeking_Placement, 'Not Specified') AS seeking_placement,
                COALESCE(l.Is_Active, 0) AS Is_Active,  -- Defaults to 0 if NULL
                COALESCE(l.Is_Placed, 0) AS Is_Placed   -- Defaults to 0 if NULL
            FROM SSDD_COMPLETE_PERSONALINFO p
            LEFT JOIN SSDD_COMPLETE_EDUCATION_DETAILS e ON p.email = e.email
            LEFT JOIN SSDD_COMPLETE_LOGIN l ON p.email = l.Email  -- ✅ Join with SSDD_COMPLETE_LOGIN
            GROUP BY p.id, p.firstname, p.lastname, p.email, p.contact_number, 
                     p.Seeking_Placement, l.Is_Active, l.Is_Placed
            ORDER BY p.id DESC  -- ✅ Orders most recent entries at the top
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Convert fetched data into a list of dictionaries
        fetch_all_applicant_results = [
            {
                "name": row[0],
                "field_of_study": row[1],
                "email": row[2],
                "contact_number": row[3],
                "seeking_placement": row[4],
                "is_active": "Active" if row[5] == 1 else "Inactive",  # ✅ Convert 1 -> "Yes", 0 -> "No"
                "is_placed": "Yes" if row[6] == 1 else "No"   # ✅ Convert 1 -> "Yes", 0 -> "No"
            }
            for row in rows
        ]

        # 🔍 Debugging: Print fetched data
        print("🔍 Debugging - Fetched Applicants (Ordered & Unique):", fetch_all_applicant_results)

    except Exception as e:
        print(f"Database error while fetching applicant details: {e}")
    finally:
        if conn:
            conn.close()

    return fetch_all_applicant_results



def fetch_combined_user_details(email):
    """
    Fetch all user details (personal info, education, work history, skills, and uploaded documents)
    for the given email and return them as a combined list of dictionaries.
    
    :param email: The user's email address.
    :return: A list of dictionaries containing all user details.
    """
    conn = None
    combined_results = []

    try:
        conn = get_db_connection('WorkflowDB')
        cursor = conn.cursor()

        # Query for personal information
        personal_info_query = """
            SELECT email, firstname, lastname, date_of_birth, id_number, address, City, Postal_code, Province, contact_number,
                   Race, Gender, Seeking_Placement, Preferred_Opportunity, Citizenship, Willing_to_Relocate, Disability,
                   Language, About_yourself, Self_Picture
            FROM SSDD_COMPLETE_PERSONALINFO
            WHERE email = ?
        """
        cursor.execute(personal_info_query, (email,))
        personal_info = cursor.fetchone()

        if personal_info:
            combined_results.append({
                "email": personal_info[0],
                "firstname": personal_info[1],
                "lastname": personal_info[2],
                "date_of_birth": personal_info[3],
                "id_number": personal_info[4],
                "address": personal_info[5],
                "City": personal_info[6],
                "Postal_code": personal_info[7],
                "Province": personal_info[8],
                "contact_number": personal_info[9],
                "Race": personal_info[10],
                "Gender": personal_info[11],
                "Seeking_Placement": personal_info[12],
                "Preferred_Opportunity": personal_info[13],
                "Citizenship": personal_info[14],
                "Willing_to_Relocate": personal_info[15],
                "Disability": personal_info[16],
                "Language": personal_info[17],
                "About_yourself": personal_info[18],
                "Self_Picture": personal_info[19]
            })

        # Query for education details
        education_query = """
            SELECT Academic_Institution, Qualification, Field_of_study, Completion_status, Country, City
            FROM SSDD_COMPLETE_EDUCATION_DETAILS
            WHERE email = ?
        """
        cursor.execute(education_query, (email,))
        education_rows = cursor.fetchall()

        for row in education_rows:
            combined_results.append({
                "Academic_Institution": row[0],
                "Qualification": row[1],
                "Field_of_study": row[2],
                "Completion_status": row[3],
                "Country": row[4],
                "City": row[5]
            })

        # Query for work history details
        work_history_query = """
            SELECT employer_names, job_titles, current_place_of_employment, start_date, end_date, job_description
            FROM SSDD_COMPLETE_WORK_HISTORY
            WHERE email = ?
        """
        cursor.execute(work_history_query, (email,))
        work_history_rows = cursor.fetchall()

        for row in work_history_rows:
            combined_results.append({
                "employer_names": row[0],
                "job_titles": row[1],
                "current_place_of_employment": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "job_description": row[5]
            })

        # Query for skills details
        skills_query = """
            SELECT skills, proficiency
            FROM SSDD_COMPLETE_SKILLS
            WHERE email = ?
        """
        cursor.execute(skills_query, (email,))
        skills_rows = cursor.fetchall()

        for row in skills_rows:
            combined_results.append({
                "skills": row[0],
                "proficiency": row[1]
            })

        # Query for uploaded documents
        documents_query = """
            SELECT document_type, file_name, file_format, uploaded_at
            FROM SSDD_COMPLETE_UPLOADED_DOCUMENTS
            WHERE email = ?
        """
        cursor.execute(documents_query, (email,))
        documents_rows = cursor.fetchall()

        for row in documents_rows:
            combined_results.append({
                "document_type": row[0],
                "file_name": row[1],
                "file_format": row[2],
                "uploaded_at": row[3]
            })

        return combined_results

    except Exception as e:
        print(f"Database error while fetching combined user details: {e}")
        return []
    finally:
        if conn:
            conn.close()
