import os
from dotenv import load_dotenv

# Cargar .env si estás en entorno local
env = os.getenv("ENV", "local")
if env == "local":
    load_dotenv(".env.local")


class Config:
    # Seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'd16f2bfa7491b82b8f9e30cf60eac02c82c648b1a93f7d9c671a3973d7eb69e5'

    # Configuración MySQL
    MYSQL_HOST = os.environ.get("MYSQLHOST") or os.environ.get("DB_HOST")
    MYSQL_USER = os.environ.get("MYSQLUSER") or os.environ.get("DB_USER")
    MYSQL_PASSWORD = os.environ.get("MYSQLPASSWORD") or os.environ.get("DB_PASS")
    MYSQL_DB = os.environ.get("MYSQLDATABASE") or os.environ.get("DB_NAME")
    MYSQL_PORT = int(os.environ.get("MYSQLPORT") or os.environ.get("DB_PORT", 3306))

    # Gemini API Key
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AIzaSyDGCXwlcMTPtdBOKHwszEuuV4cFh-mfc18"
