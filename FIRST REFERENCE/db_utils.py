# db_utils.py
import pyodbc
import pyodbc

def get_db_connection(database_name):
    s = 'APB-JBS02-02L'
    u = 'GENERALADMINISTRATOR'
    p = 'GENERALADMIN@12345'
    cstr = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s};DATABASE={database_name};UID={u};PWD={p}'
    conn = pyodbc.connect(cstr)
    return conn
