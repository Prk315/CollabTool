# backend/db.py
import psycopg2, os, time
from dotenv import load_dotenv; load_dotenv()
from flask import current_app, g

def get_db_connection():
    """Get a database connection with error handling"""
    try:
        return psycopg2.connect(
            dbname="collabtool", 
            user=os.getenv("DB_USER"), 
            password=os.getenv("DB_PASSWORD"), 
            host=os.getenv("DB_HOST", "localhost")
        )
    except psycopg2.OperationalError as e:
        # Log the error if in a Flask context
        if current_app:
            current_app.logger.error(f"Database connection failed: {e}")
        return None

def get_db_connection_with_retry(max_retries=3, retry_delay=1):
    """Try to connect to the database with retries"""
    attempts = 0
    last_error = None
    
    while attempts < max_retries:
        conn = get_db_connection()
        if conn:
            return conn
        attempts += 1
        if attempts < max_retries:
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        else:
            last_error = f"Failed to connect to database after {max_retries} attempts"
            if current_app:
                current_app.logger.error(last_error)
    
    # Return a placeholder connection object that raises a friendly error when used
    class DBConnectionPlaceholder:
        def __getattr__(self, name):
            raise RuntimeError(f"Database connection unavailable: {last_error}")
        
        def cursor(self):
            raise RuntimeError(f"Database connection unavailable: {last_error}")
    
    return DBConnectionPlaceholder()
