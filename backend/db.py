import psycopg2
import os

def get_db_connection():
    return psycopg2.connect(
        dbname="collabtool",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host="localhost"
    )
