import psycopg2

DB_CONF = {
    "host": "localhost",
    "database": "shopdb",
    "user": "postgres",
    "password": "2004"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONF)
