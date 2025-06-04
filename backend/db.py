# backend/db.py
import psycopg2, os
from dotenv import load_dotenv; load_dotenv()

def get_db_connection():
    return psycopg2.connect(dbname="collabtool", user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), host="localhost")
