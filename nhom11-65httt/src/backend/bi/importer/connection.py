import psycopg

from .config import DB_CONFIG


def get_connection():
    return psycopg.connect(**DB_CONFIG)


def test_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_database(), current_user
            """)

            database, username = cur.fetchone()

            print("DATABASE CONNECTION SUCCESS")
            print(f"Database: {database}")
            print(f"User: {username}")


if __name__ == "__main__":
    test_connection()