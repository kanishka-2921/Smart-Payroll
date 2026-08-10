from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URI, BASE_DIR
import os

Base = declarative_base()

# Attempt to connect to the configured URI, fallback to SQLite if it fails
try:
    if DATABASE_URI.startswith("sqlite"):
        engine = create_engine(DATABASE_URI, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URI, pool_pre_ping=True, pool_recycle=300)
    # Test connection
    with engine.connect() as conn:
        pass
except Exception as e:
    print(f"Database connection to database failed: {e}")
    print("Falling back to local SQLite database.")
    sqlite_file = os.path.join(BASE_DIR, "payroll.db")
    DATABASE_URI = f"sqlite:///{sqlite_file}"
    engine = create_engine(DATABASE_URI, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    db = SessionLocal()
    
    # Migrate half_day_salary
    try:
        db.execute(text("ALTER TABLE payroll_employees ADD COLUMN half_day_salary FLOAT DEFAULT 0.0;"))
        db.commit()
    except Exception:
        db.rollback()
        
    # Migrate weekly_off_day
    try:
        db.execute(text("ALTER TABLE payroll_employees ADD COLUMN weekly_off_day VARCHAR(10) DEFAULT 'SUN';"))
        db.commit()
    except Exception:
        db.rollback()

    # Migrate mockup fields
    for col, col_type in [
        ("title", "VARCHAR(10)"),
        ("marital_status", "VARCHAR(20)"),
        ("nationality", "VARCHAR(50)"),
        ("religion", "VARCHAR(50)"),
        ("blood_group", "VARCHAR(10)"),
        ("probation_end_date", "DATE"),
        ("confirmation_date", "DATE"),
        ("location", "VARCHAR(100)"),
        ("reporting_to", "VARCHAR(100)")
    ]:
        try:
            db.execute(text(f"ALTER TABLE payroll_employees ADD COLUMN {col} {col_type};"))
            db.commit()
        except Exception:
            db.rollback()
        
    db.close()
