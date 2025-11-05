from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from .models import Base  # Import Base from models.py

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Test connections before use
    pool_recycle=300     # Recycle connections every 5 mins
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to create tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency for our API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()