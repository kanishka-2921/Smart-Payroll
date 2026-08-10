from database.connection import SessionLocal, init_db
from database.models import User, Setting, Department, Designation, HolidayCalendar
from services.auth_service import AuthService
from datetime import date

def seed_db():
    db = SessionLocal()
    try:
        # Check if users already seeded
        if db.query(User).first() is not None:
            return  # DB already seeded

        print("Seeding database...")
        
        # 1. Seed Users
        users = [
            User(username="admin", password_hash=AuthService.hash_password("admin123"), role="Administrator"),
            User(username="hr", password_hash=AuthService.hash_password("hr123"), role="HR"),
            User(username="accountant", password_hash=AuthService.hash_password("accountant123"), role="Accountant"),
        ]
        db.add_all(users)

        # 2. Seed Settings
        settings_dict = {
            "pf_rate": "12.0",            # employee PF %
            "esi_rate": "0.75",           # employee ESI %
            "prof_tax": "200.0",          # Professional Tax flat deduction
            "overtime_rate_mult": "1.5",  # Overtime multiplier
            "off_day_rule_mult": "2.0",   # Comp off / Worked on weekly off rate multiplier (e.g. 2.0x daily pay)
            "half_day_rule": "0.5",       # Deducts 0.5 pay days
            "late_coming_deduction": "50.0",  # Deduction per late day (e.g., after 3 warnings)
            "late_coming_threshold": "3", # Allowed late days per month before deductions
            "working_days": "26",         # standard working days per month
            "cl_balance": "12",           # Casual Leaves per year
            "sl_balance": "10",           # Sick Leaves per year
            "el_balance": "15"            # Earned Leaves per year
        }
        
        for k, v in settings_dict.items():
            db.add(Setting(setting_key=k, setting_value=v))

        # 3. Seed Departments
        depts = [
            Department(name="Human Resources"),
            Department(name="Finance & Accounting"),
            Department(name="Engineering"),
            Department(name="Sales & Marketing"),
            Department(name="Operations")
        ]
        db.add_all(depts)

        # 4. Seed Designations
        desigs = [
            Designation(name="Manager"),
            Designation(name="Senior Specialist"),
            Designation(name="HR Generalist"),
            Designation(name="Accountant"),
            Designation(name="Software Engineer"),
            Designation(name="Sales Executive"),
            Designation(name="Associate")
        ]
        db.add_all(desigs)

        # 5. Seed Holiday Calendar
        holidays = [
            HolidayCalendar(holiday_date=date(2026, 1, 1), name="New Year's Day", is_paid=True),
            HolidayCalendar(holiday_date=date(2026, 1, 26), name="Republic Day", is_paid=True),
            HolidayCalendar(holiday_date=date(2026, 5, 1), name="Labor Day", is_paid=True),
            HolidayCalendar(holiday_date=date(2026, 8, 15), name="Independence Day", is_paid=True),
            HolidayCalendar(holiday_date=date(2026, 10, 2), name="Gandhi Jayanti", is_paid=True),
            HolidayCalendar(holiday_date=date(2026, 12, 25), name="Christmas", is_paid=True),
        ]
        db.add_all(holidays)

        db.commit()
        print("Seeding complete.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    seed_db()
