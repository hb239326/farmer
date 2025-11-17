from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from urllib.parse import quote_plus

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database configuration via environment variables
# Set DB_ENGINE=mysql to use MySQL, otherwise defaults to SQLite
DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite').lower().strip()

if DB_ENGINE == 'mysql':
    # Expect: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = int(os.getenv('DB_PORT', '3306'))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'cropai')
    # Optional UNIX socket (if using local MySQL/MariaDB socket). On Windows XAMPP this is typically not used.
    DB_SOCKET = os.getenv('DB_SOCKET', '').strip()

    # URL-encode credentials for safety (handles special characters)
    q_user = quote_plus(DB_USER)
    q_pass = quote_plus(DB_PASSWORD)

    # Build server-level URL (no database) to create DB if missing
    if DB_SOCKET:
        server_url = f"mysql+pymysql://{q_user}:{q_pass}@%lo/?unix_socket={DB_SOCKET}&charset=utf8mb4"
        db_url = f"mysql+pymysql://{q_user}:{q_pass}@localhost/{DB_NAME}?unix_socket={DB_SOCKET}&charset=utf8mb4"
    else:
        server_url = f"mysql+pymysql://{q_user}:{q_pass}@{DB_HOST}:{DB_PORT}/?charset=utf8mb4"
        db_url = f"mysql+pymysql://{q_user}:{q_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

    # Create database if it doesn't exist (works with root or a user with CREATE privilege)
    try:
        bootstrap_engine = create_engine(server_url, pool_pre_ping=True)
        with bootstrap_engine.connect() as conn:
            conn.exec_driver_sql(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
    except Exception:
        # If we cannot create DB (insufficient privileges), continue; app may fail later with clearer error
        pass

    # Final engine bound to target database
    SQLALCHEMY_DATABASE_URL = db_url
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '10')),
        echo=os.getenv('SQL_ECHO', '0') == '1',
    )
else:
    # Default to SQLite local file for dev
    DB_PATH = os.path.join(BASE_DIR, 'app.db')
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=os.getenv('SQL_ECHO', '0') == '1',
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
