from database.models import Employee, Attendance, Payroll, Setting, Advance, Loan, LeaveMaster, Bonus, HolidayCalendar
from sqlalchemy.orm import Session
from datetime import datetime

class PayrollEngine:
    @staticmethod
    def get_settings(db: Session) -> dict:
        """Fetch all setting key-value pairs from database."""
        settings = db.query(Setting).all()
        return {s.setting_key: float(s.setting_value) for s in settings}

    @classmethod
    def calculate_realtime(cls, db: Session, employee: Employee, att: Attendance,
                           extra_bonuses: float = 0.0, extra_incentives: float = 0.0,
                           food_deduction: float = 0.0, penalty: float = 0.0) -> dict:
        """
        Calculate employee payroll details dynamically.
        Returns a dictionary of all earnings, deductions, and net salary.
        """
        cfg = cls.get_settings(db)
        
        # 1. Base details
        working_days = att.working_days if att.working_days > 0 else int(cfg.get("working_days", 26))
        monthly_salary = employee.monthly_salary or 0.0
        
        # Per Day Salary
        per_day_salary = monthly_salary / working_days if working_days > 0 else 0.0
        
        # 2. Equivalent Paid Days
        full_days = att.full_days or 0
        half_days = att.half_days or 0
        
        # Half Day Salary calculation
        half_day_salary = half_days * (per_day_salary / 2.0) if half_days > 0 else 0.0
        
        # Worked on Weekly Off calculation
        worked_weekly_off = att.worked_on_weekly_off or 0
        worked_weekly_off_amount = worked_weekly_off * per_day_salary if worked_weekly_off > 0 else 0.0
        
        # Leave Deduction calculation (Total leave days = paid_leave + unpaid_leave)
        leave_days = (att.paid_leave or 0) + (att.unpaid_leave or 0)
        leave_deduction = leave_days * per_day_salary if leave_days > 0 else 0.0
        
        # Net Payable Salary = (Present Days * Per Day Salary) + Half Day Salary + Weekly Off Amount
        net_salary = (full_days * per_day_salary) + half_day_salary + worked_weekly_off_amount
        if net_salary < 0:
            net_salary = 0.0
            
        # Deductions (set to 0.0 as requested)
        pf_deduction = 0.0
        esi_deduction = 0.0
        prof_tax = 0.0
        tds_deduction = 0.0
        late_deduction = 0.0
        advance_recovery = 0.0
        loan_emi = 0.0
        
        total_deductions = leave_deduction
        
        return {
            "per_day_salary": round(per_day_salary, 2),
            "monthly_salary": round(monthly_salary, 2),
            "half_day_salary": round(half_day_salary, 2),
            "worked_weekly_off_days": worked_weekly_off,
            "worked_weekly_off_amount": round(worked_weekly_off_amount, 2),
            "leave_days": leave_days,
            "leave_deduction": round(leave_deduction, 2),
            "paid_days": round(full_days + (half_days * 0.5), 1),
            "gross_salary": round(net_salary, 2),
            "hra_amount": 0.0,
            "special_allowance": 0.0,
            "other_allowance": 0.0,
            "overtime_amount": 0.0,
            "off_day_compensation": round(worked_weekly_off_amount, 2),
            "pf_deduction": 0.0,
            "esi_deduction": 0.0,
            "prof_tax_deduction": 0.0,
            "tds_deduction": 0.0,
            "late_deduction": 0.0,
            "advance_recovery": 0.0,
            "loan_emi": 0.0,
            "food_deduction": 0.0,
            "penalty": 0.0,
            "total_allowances": round(worked_weekly_off_amount, 2),
            "total_deductions": round(total_deductions, 2),
            "net_salary": round(net_salary, 2)
        }

    @classmethod
    def process_payroll(cls, db: Session, employee_id: int, month: int, year: int, 
                        extra_bonuses: float = 0.0, extra_incentives: float = 0.0, 
                        food_deduction: float = 0.0, penalty: float = 0.0,
                        username: str = "System") -> Payroll:
        """
        Calculates and commits the payroll for an employee.
        Adjusts loan and advance balances upon commitment.
        """
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        att = db.query(Attendance).filter(
            Attendance.employee_id == employee_id, 
            Attendance.month == month, 
            Attendance.year == year
        ).first()
        
        if not employee or not att:
            raise ValueError("Employee or attendance record not found.")

        # Calculate values
        res = cls.calculate_realtime(db, employee, att, extra_bonuses, extra_incentives, food_deduction, penalty)

        # Check if payroll record already exists
        payroll = db.query(Payroll).filter(
            Payroll.employee_id == employee_id, 
            Payroll.month == month, 
            Payroll.year == year
        ).first()

        if not payroll:
            payroll = Payroll(employee_id=employee_id, month=month, year=year)
            db.add(payroll)

        # Populate calculations
        payroll.per_day_salary = res["per_day_salary"]
        payroll.paid_days = res["paid_days"]
        payroll.gross_salary = res["gross_salary"]
        payroll.hra_amount = res["hra_amount"]
        payroll.special_allowance = res["special_allowance"]
        payroll.other_allowance = res["other_allowance"]
        payroll.bonus_amount = extra_bonuses
        payroll.incentive_amount = extra_incentives
        payroll.overtime_amount = res["overtime_amount"]
        payroll.off_day_compensation = res["off_day_compensation"]
        payroll.pf_deduction = res["pf_deduction"]
        payroll.esi_deduction = res["esi_deduction"]
        payroll.prof_tax_deduction = res["prof_tax_deduction"]
        payroll.tds_deduction = res["tds_deduction"]
        payroll.advance_recovery = res["advance_recovery"]
        payroll.loan_emi = res["loan_emi"]
        payroll.food_deduction = res["food_deduction"]
        payroll.penalty = res["penalty"]
        payroll.late_deduction = res["late_deduction"]
        payroll.total_allowances = res["total_allowances"]
        payroll.total_deductions = res["total_deductions"]
        payroll.net_salary = res["net_salary"]
        payroll.status = "Processed"
        payroll.processed_at = datetime.utcnow()

        # Update loan and advance balances
        if res["advance_recovery"] > 0:
            active_advance = db.query(Advance).filter(
                Advance.employee_id == employee_id, 
                Advance.status == "Active",
                Advance.balance_amount > 0
            ).first()
            if active_advance:
                active_advance.balance_amount -= res["advance_recovery"]
                if active_advance.balance_amount <= 0:
                    active_advance.status = "Closed"

        if res["loan_emi"] > 0:
            active_loan = db.query(Loan).filter(
                Loan.employee_id == employee_id, 
                Loan.status == "Active",
                Loan.balance_amount > 0
            ).first()
            if active_loan:
                active_loan.balance_amount -= res["loan_emi"]
                if active_loan.balance_amount <= 0:
                    active_loan.status = "Closed"
                    
        # Update any pending bonus status to Paid
        bonuses = db.query(Bonus).filter(
            Bonus.employee_id == employee_id,
            Bonus.month == month,
            Bonus.year == year,
            Bonus.status == "Pending"
        ).all()
        for bonus in bonuses:
            bonus.status = "Paid"

        db.commit()
        return payroll
