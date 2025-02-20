# db_utils.py
import pyodbc
import pyodbc
import pypyodbc as odbc

# def get_db_connection(database_name):
#     s = 'APB-JBS02-02L'
#     u = 'GENERALADMINISTRATOR'
#     p = 'GENERALADMIN@12345'
#     cstr = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s};DATABASE={database_name};UID={u};PWD={p}'
#     conn = pyodbc.connect(cstr)
#     return conn




# online
DRIVER_NAME='ODBC Driver 17 for SQL Server'
SERVER_NAME='102.23.201.12\IMS'
DATABASE_NAME='chieta_ofo'
PASSWORD='0foAdmin123$'
USERNAME='ofo_service'

def get_db_connection(database_name):
    connection_string = "DRIVER={SQL Server};SERVER=102.23.201.12\IMS;DATABASE=chieta_ofo;UID=ofo_service;PWD=0foAdmin123$"

    return odbc.connect(connection_string)

conn=get_db_connection('database_name')
