from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

# Auto-create MySQL database if it doesn't exist
if settings.DATABASE_URL.startswith("mysql"):
    try:
        from urllib.parse import urlparse
        import pymysql
        # standard urlparse requires a standard scheme like http
        cleaned_url = settings.DATABASE_URL.replace("mysql+pymysql://", "http://").replace("mysql://", "http://")
        url = urlparse(cleaned_url)
        db_name = url.path.lstrip('/')
        host = url.hostname
        port = url.port or 3306
        user = url.username
        password = url.password
        
        # Connect to MySQL server (without selecting DB)
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to auto-create MySQL database: {e}")

# If SQLite, add check_same_thread argument
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
