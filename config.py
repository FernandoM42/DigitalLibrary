# config.py
# config.py
import os
from dotenv import load_dotenv


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "going-to-be-a-secret"
    MYSQL_HOST = os.environ.get("MYSQL_HOST") or "127.0.0.1"
    MYSQL_USER = os.environ.get("MYSQL_USER") or "adminlibros"
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD") or "constantreader"
    MYSQL_DB = os.environ.get("MYSQL_DB") or "sk_libros"
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT") or 3306)

    # --- Configuración para subida de archivos ---
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Límite de 16MB para archivos
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    # Asegurarse de que la carpeta de subidas exista
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # ---------------------------------------------
