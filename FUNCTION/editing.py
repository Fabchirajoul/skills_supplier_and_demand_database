def function_fetch_all_applicant_results_for_company():
    """
    Fetch distinct applicants by email, selecting only one entry per email.
    Orders by the most recent entries first.
    """
    conn = None
    fetch_all_applicant_results_company = []
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
                p.region,
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
                "region": row[3],
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

    return fetch_all_applicant_results_company