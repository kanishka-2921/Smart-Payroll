from database.models import Employee, LeaveMaster, LeaveTransaction, Setting
from sqlalchemy.orm import Session
from datetime import date

class LeaveService:
    @staticmethod
    def initialize_employee_leaves(db: Session, employee_id: int):
        """Seed opening leave balances for a newly created employee based on settings."""
        settings = db.query(Setting).all()
        cfg = {s.setting_key: int(s.setting_value) for s in settings if s.setting_key.endswith("_balance")}
        
        leave_types = {
            "Casual Leave": cfg.get("cl_balance", 12),
            "Sick Leave": cfg.get("sl_balance", 10),
            "Earned Leave": cfg.get("el_balance", 15),
            "Maternity Leave": 90,  # default standard paid leaves for maternity
            "Paternity Leave": 15,  # default standard paid leaves for paternity
            "Leave Without Pay": 999  # unlimited LWP
        }

        # Check if already initialized
        exists = db.query(LeaveMaster).filter(LeaveMaster.employee_id == employee_id).first()
        if exists:
            return

        for l_type, bal in leave_types.items():
            lm = LeaveMaster(
                employee_id=employee_id,
                leave_type=l_type,
                opening_balance=bal,
                used=0,
                remaining=bal
            )
            db.add(lm)
        db.commit()

    @staticmethod
    def apply_leave(db: Session, employee_id: int, leave_type: str, 
                    start_date: date, end_date: date, reason: str) -> bool:
        """Apply for a leave and check balance availability."""
        total_days = (end_date - start_date).days + 1
        
        # Check balance
        lm = db.query(LeaveMaster).filter(
            LeaveMaster.employee_id == employee_id,
            LeaveMaster.leave_type == leave_type
        ).first()

        if not lm:
            return False

        # If not Leave Without Pay, check remaining balance
        if leave_type != "Leave Without Pay" and lm.remaining < total_days:
            return False  # Insufficient leaves

        # Create leave transaction
        txn = LeaveTransaction(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status="Pending"
        )
        db.add(txn)
        db.commit()
        return True

    @staticmethod
    def approve_leave(db: Session, transaction_id: int, approved_by_user: str) -> bool:
        """Approve leave transaction and deduct from remaining balance."""
        txn = db.query(LeaveTransaction).filter(LeaveTransaction.id == transaction_id).first()
        if not txn or txn.status != "Pending":
            return False

        lm = db.query(LeaveMaster).filter(
            LeaveMaster.employee_id == txn.employee_id,
            LeaveMaster.leave_type == txn.leave_type
        ).first()

        if lm and txn.leave_type != "Leave Without Pay":
            if lm.remaining < txn.total_days:
                txn.status = "Rejected"
                txn.reason += " (Auto-Rejected: Insufficient Balance)"
                db.commit()
                return False
            
            lm.used += txn.total_days
            lm.remaining = lm.opening_balance - lm.used

        txn.status = "Approved"
        txn.approved_by = approved_by_user
        db.commit()
        return True

    @staticmethod
    def reject_leave(db: Session, transaction_id: int, rejected_by_user: str) -> bool:
        """Reject leave transaction."""
        txn = db.query(LeaveTransaction).filter(LeaveTransaction.id == transaction_id).first()
        if not txn or txn.status != "Pending":
            return False
        txn.status = "Rejected"
        txn.approved_by = rejected_by_user
        db.commit()
        return True
