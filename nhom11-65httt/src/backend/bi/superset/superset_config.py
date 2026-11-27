import os
from urllib.parse import quote_plus

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

DB_PASSWORD = quote_plus(
    os.environ["SUPERSET_DB_PASSWORD"]
)

SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://"
    f"superset:{DB_PASSWORD}"
    "@superset_meta:5432/superset"
)

ROW_LIMIT = 10000

SQLLAB_TIMEOUT = 120

SUPERSET_WEBSERVER_TIMEOUT = 120

WTF_CSRF_ENABLED = True

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
}

LANGUAGES = {
    "en": {
        "flag": "us",
        "name": "English",
    },
}

BABEL_DEFAULT_LOCALE = "en"