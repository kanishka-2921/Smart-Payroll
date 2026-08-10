from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base

class User(Base):
    __tablename__ = "payroll_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False)  # Administrator, HR, Accountant
    is_active = Column(Boolean, default=True)

class Department(Base):
    __tablename__ = "payroll_departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    employees = relationship("Employee", back_populates="department")

class Designation(Base):
    __tablename__ = "payroll_designations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    employees = relationship("Employee", back_populates="designation")

class Employee(Base):
    __tablename__ = "payroll_employees"
    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), index=True, nullable=False)
    father_name = Column(String(100))
    gender = Column(String(10))
    dob = Column(Date)
    joining_date = Column(Date)
    department_id = Column(Integer, ForeignKey("payroll_departments.id"), index=True)
    designation_id = Column(Integer, ForeignKey("payroll_designations.id"), index=True)
    employment_type = Column(String(20))  # Permanent, Contract, Intern, Consultant
    
    # Base Salary structure
    monthly_salary = Column(Float, default=0.0)
    half_day_salary = Column(Float, default=0.0)
    weekly_off_day = Column(String(10), default="SUN")
    basic_salary = Column(Float, default=0.0)
    hra = Column(Float, default=0.0)
    special_allowance = Column(Float, default=0.0)
    other_allowance = Column(Float, default=0.0)
    
    # Financial details
    bank_name = Column(String(100))
    account_number = Column(String(50), index=True)
    ifsc = Column(String(20))
    pan_number = Column(String(20), index=True)
    aadhaar_number = Column(String(20), index=True)
    pf_number = Column(String(50))
    esic_number = Column(String(50))
    uan = Column(String(50))
    
    # Contact
    email = Column(String(100), index=True)
    mobile = Column(String(20))
    address = Column(String(255))
    emergency_contact = Column(String(100))
    photo_path = Column(String(255))
    
    # Mockup attributes
    title = Column(String(10))
    marital_status = Column(String(20))
    nationality = Column(String(50))
    religion = Column(String(50))
    blood_group = Column(String(10))
    probation_end_date = Column(Date)
    confirmation_date = Column(Date)
    location = Column(String(100))
    reporting_to = Column(String(100))
    
    # Status
    status = Column(String(20), default="Active", index=True)  # Active, Inactive, Resigned
 
    department = relationship("Department", back_populates="employees")
    designation = relationship("Designation", back_populates="employees")
    attendance_records = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    daily_attendance_records = relationship("DailyAttendance", back_populates="employee", cascade="all, delete-orphan")
    payroll_records = relationship("Payroll", back_populates="employee", cascade="all, delete-orphan")
    leave_masters = relationship("LeaveMaster", back_populates="employee", cascade="all, delete-orphan")
    leave_transactions = relationship("LeaveTransaction", back_populates="employee", cascade="all, delete-orphan")
    bonuses = relationship("Bonus", back_populates="employee", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="employee", cascade="all, delete-orphan")
    advances = relationship("Advance", back_populates="employee", cascade="all, delete-orphan")

class Attendance(Base):
    __tablename__ = "payroll_attendance"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    month = Column(Integer, index=True, nullable=False)
    year = Column(Integer, index=True, nullable=False)
    
    working_days = Column(Integer, default=0)
    full_days = Column(Integer, default=0)
    half_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    paid_leave = Column(Integer, default=0)
    unpaid_leave = Column(Integer, default=0)
    weekly_off = Column(Integer, default=0)
    holidays = Column(Integer, default=0)
    
    worked_on_weekly_off = Column(Integer, default=0)
    overtime_hours = Column(Float, default=0.0)
    late_coming_days = Column(Integer, default=0)
    early_leaving_days = Column(Integer, default=0)
    remarks = Column(String(255))
 
    employee = relationship("Employee", back_populates="attendance_records")

class DailyAttendance(Base):
    __tablename__ = "payroll_daily_attendance"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    
    status = Column(String(30), nullable=False)  # Present, Half Day, Paid Leave, Unpaid Leave, Absent, Worked Off
    late_coming = Column(Boolean, default=False)
    early_leaving = Column(Boolean, default=False)
    remarks = Column(String(255))

    employee = relationship("Employee", back_populates="daily_attendance_records")

class Payroll(Base):
    __tablename__ = "payroll_payroll"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    month = Column(Integer, index=True, nullable=False)
    year = Column(Integer, index=True, nullable=False)
    
    per_day_salary = Column(Float, default=0.0)
    paid_days = Column(Float, default=0.0)
    gross_salary = Column(Float, default=0.0)
    
    # Allowances
    hra_amount = Column(Float, default=0.0)
    travel_allowance = Column(Float, default=0.0)
    medical_allowance = Column(Float, default=0.0)
    special_allowance = Column(Float, default=0.0)
    bonus_amount = Column(Float, default=0.0)
    incentive_amount = Column(Float, default=0.0)
    overtime_amount = Column(Float, default=0.0)
    off_day_compensation = Column(Float, default=0.0)
    
    # Deductions
    pf_deduction = Column(Float, default=0.0)
    esi_deduction = Column(Float, default=0.0)
    prof_tax_deduction = Column(Float, default=0.0)
    tds_deduction = Column(Float, default=0.0)
    advance_recovery = Column(Float, default=0.0)
    loan_emi = Column(Float, default=0.0)
    food_deduction = Column(Float, default=0.0)
    penalty = Column(Float, default=0.0)
    late_deduction = Column(Float, default=0.0)
    
    total_allowances = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    net_salary = Column(Float, default=0.0)
    
    status = Column(String(20), default="Pending", index=True)  # Pending, Processed
    processed_at = Column(DateTime, default=datetime.utcnow)
 
    employee = relationship("Employee", back_populates="payroll_records")

class LeaveMaster(Base):
    __tablename__ = "payroll_leave_master"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    leave_type = Column(String(50), nullable=False)  # Casual Leave, Sick Leave, Earned Leave, Maternity, Paternity
    opening_balance = Column(Integer, default=0)
    used = Column(Integer, default=0)
    remaining = Column(Integer, default=0)
 
    employee = relationship("Employee", back_populates="leave_masters")

class LeaveTransaction(Base):
    __tablename__ = "payroll_leave_transactions"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Integer, nullable=False)
    reason = Column(String(255))
    status = Column(String(20), default="Pending", index=True)  # Pending, Approved, Rejected
    approved_by = Column(String(50))
 
    employee = relationship("Employee", back_populates="leave_transactions")

class Bonus(Base):
    __tablename__ = "payroll_bonus"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    type = Column(String(50), nullable=False)  # Festival, Performance, Referral, Custom
    amount = Column(Float, default=0.0)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(String(20), default="Pending")  # Pending, Paid
 
    employee = relationship("Employee", back_populates="bonuses")

class Loan(Base):
    __tablename__ = "payroll_loan"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    loan_amount = Column(Float, default=0.0)
    interest_rate = Column(Float, default=0.0)
    emi_amount = Column(Float, default=0.0)
    balance_amount = Column(Float, default=0.0)
    date_issued = Column(Date)
    status = Column(String(20), default="Active")  # Active, Closed
 
    employee = relationship("Employee", back_populates="loans")

class Advance(Base):
    __tablename__ = "payroll_advance"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("payroll_employees.id"), index=True, nullable=False)
    advance_amount = Column(Float, default=0.0)
    reason = Column(String(255))
    emi_amount = Column(Float, default=0.0)
    balance_amount = Column(Float, default=0.0)
    date_issued = Column(Date)
    status = Column(String(20), default="Active")  # Active, Closed
 
    employee = relationship("Employee", back_populates="advances")

class Setting(Base):
    __tablename__ = "payroll_settings"
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, index=True, nullable=False)
    setting_value = Column(String(255))

class HolidayCalendar(Base):
    __tablename__ = "payroll_holiday_calendar"
    id = Column(Integer, primary_key=True, index=True)
    holiday_date = Column(Date, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_paid = Column(Boolean, default=True)

class AuditLog(Base):
    __tablename__ = "payroll_audit_log"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), index=True)
    action_name = Column(String(100), index=True)
    details = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

# Composite indexes for faster reports and calculation queries
Index("idx_payroll_attendance_emp_date", Attendance.employee_id, Attendance.month, Attendance.year, unique=True)
Index("idx_payroll_payroll_emp_date", Payroll.employee_id, Payroll.month, Payroll.year, unique=True)
Index("idx_payroll_bonus_emp_date", Bonus.employee_id, Bonus.month, Bonus.year)
Index("idx_daily_attendance_emp_date", DailyAttendance.employee_id, DailyAttendance.date, unique=True)
