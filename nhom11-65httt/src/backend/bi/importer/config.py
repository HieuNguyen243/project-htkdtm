import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "dbname": os.getenv("DB_NAME", "phongtro_bi_demo"),
    "user": os.getenv("DB_USER", "bi_importer"),
    "password": os.getenv("DB_PASSWORD"),
    "connect_timeout": 10,
}

SCHEMA_VERSION = "1.0.0-draft.1"

if not DB_CONFIG["password"]:
    raise RuntimeError("Missing DB_PASSWORD in .env")