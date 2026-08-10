from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QFormLayout, QTableWidget, QTableWidgetItem, QDateEdit,
                             QHeaderView, QAbstractItemView, QScrollArea)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Employee, LeaveMaster, LeaveTransaction
from services.leave_service import LeaveService
from utilities.audit_logger import AuditLogger
from datetime import datetime

class LeaveView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.load_employees()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Title & Refresh H-Layout
        header_row = QHBoxLayout()
        title_lbl = QLabel("Leave Management")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setFixedWidth(100)
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_row.addWidget(self.btn_refresh)

        layout.addLayout(header_row)

        # Employee Selector Bar
        selection_frame = QFrame()
        selection_frame.setProperty("class", "DashboardCard")
        selection_layout = QHBoxLayout(selection_frame)
        selection_layout.setContentsMargins(15, 15, 15, 15)
        
        selection_layout.addWidget(QLabel("Select Employee:"))
        self.cmb_employee = QComboBox()
        self.cmb_employee.currentIndexChanged.connect(self.employee_changed)
        selection_layout.addWidget(self.cmb_employee, 2)
        selection_layout.addStretch(3)

        layout.addWidget(selection_frame)

        # Split: Top part has Balances (left) and Apply Form (right), Bottom part has Transactions History
        top_split = QHBoxLayout()
        top_split.setSpacing(15)

        # Balances Card
        self.balances_card = QFrame()
        self.balances_card.setProperty("class", "DashboardCard")
        bal_layout = QVBoxLayout(self.balances_card)
        bal_layout.addWidget(QLabel("<b>Leave Balances</b>"))
        
        self.tbl_balances = QTableWidget()
        self.tbl_balances.setColumnCount(4)
        self.tbl_balances.setHorizontalHeaderLabels(["Leave Type", "Opening", "Used", "Remaining"])
        self.tbl_balances.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_balances.verticalHeader().setDefaultSectionSize(36)
        self.tbl_balances.verticalHeader().setVisible(False)
        self.tbl_balances.setEditTriggers(QAbstractItemView.NoEditTriggers)
        bal_layout.addWidget(self.tbl_balances)
        top_split.addWidget(self.balances_card, 3)

        # Apply Form Card
        self.apply_card = QFrame()
        self.apply_card.setProperty("class", "DashboardCard")
        form_layout = QFormLayout(self.apply_card)
        form_layout.setSpacing(10)
        
        form_layout.addRow(QLabel("<b>Apply / Book Leave</b>"))
        
        self.cmb_leave_type = QComboBox()
        self.cmb_leave_type.addItems([
            "Casual Leave", "Sick Leave", "Earned Leave", 
            "Maternity Leave", "Paternity Leave", "Leave Without Pay"
        ])
        
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate())

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())

        self.txt_reason = QLineEdit()
        
        self.btn_apply = QPushButton("Apply Leave")
        self.btn_apply.setProperty("class", "PrimaryBtn")
        self.btn_apply.clicked.connect(self.apply_leave)

        form_layout.addRow("Leave Type:", self.cmb_leave_type)
        form_layout.addRow("Start Date:", self.date_start)
        form_layout.addRow("End Date:", self.date_end)
        form_layout.addRow("Reason:", self.txt_reason)
        form_layout.addRow("", self.btn_apply)

        top_split.addWidget(self.apply_card, 2)
        layout.addLayout(top_split)

        # Bottom Transactions List
        self.history_card = QFrame()
        self.history_card.setProperty("class", "DashboardCard")
        hist_layout = QVBoxLayout(self.history_card)
        hist_layout.addWidget(QLabel("<b>Leave Transactions History</b>"))

        self.tbl_history = QTableWidget()
        self.tbl_history.setColumnCount(8)
        self.tbl_history.setHorizontalHeaderLabels([
            "ID", "Type", "Start Date", "End Date", "Days", "Reason", "Status", "Actions"
        ])
        self.tbl_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_history.verticalHeader().setDefaultSectionSize(36)
        self.tbl_history.verticalHeader().setVisible(False)
        self.tbl_history.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_history.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hist_layout.addWidget(self.tbl_history)

        layout.addWidget(self.history_card)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def refresh_data(self):
        self.load_employees()
        self.employee_changed()

    def load_employees(self):
        current_id = self.cmb_employee.currentData()
        db = SessionLocal()
        try:
            self.cmb_employee.blockSignals(True)
            self.cmb_employee.clear()
            self.cmb_employee.addItem("-- Select Employee --", None)
            employees = db.query(Employee).filter(Employee.status == "Active").order_by(Employee.name).all()
            for emp in employees:
                self.cmb_employee.addItem(f"{emp.name} ({emp.employee_code})", emp.id)
                
            if current_id is not None:
                idx = self.cmb_employee.findData(current_id)
                if idx >= 0:
                    self.cmb_employee.setCurrentIndex(idx)
            self.cmb_employee.blockSignals(False)
        finally:
            db.close()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_employees()

    def employee_changed(self):
        self.refresh_balances()
        self.refresh_transactions()

    def refresh_balances(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.tbl_balances.setRowCount(0)
            return

        db = SessionLocal()
        try:
            balances = db.query(LeaveMaster).filter(LeaveMaster.employee_id == emp_id).all()
            self.tbl_balances.setRowCount(len(balances))
            for i, bal in enumerate(balances):
                self.tbl_balances.setItem(i, 0, QTableWidgetItem(bal.leave_type))
                self.tbl_balances.setItem(i, 1, QTableWidgetItem(str(bal.opening_balance)))
                self.tbl_balances.setItem(i, 2, QTableWidgetItem(str(bal.used)))
                self.tbl_balances.setItem(i, 3, QTableWidgetItem(str(bal.remaining)))
        finally:
            db.close()

    def refresh_transactions(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.tbl_history.setRowCount(0)
            return

        db = SessionLocal()
        try:
            txns = db.query(LeaveTransaction).filter(
                LeaveTransaction.employee_id == emp_id
            ).order_by(LeaveTransaction.start_date.desc()).all()

            self.tbl_history.setRowCount(len(txns))
            
            # Setup row contents
            for i, txn in enumerate(txns):
                self.tbl_history.setItem(i, 0, QTableWidgetItem(str(txn.id)))
                self.tbl_history.setItem(i, 1, QTableWidgetItem(txn.leave_type))
                self.tbl_history.setItem(i, 2, QTableWidgetItem(str(txn.start_date)))
                self.tbl_history.setItem(i, 3, QTableWidgetItem(str(txn.end_date)))
                self.tbl_history.setItem(i, 4, QTableWidgetItem(str(txn.total_days)))
                self.tbl_history.setItem(i, 5, QTableWidgetItem(txn.reason or ""))
                self.tbl_history.setItem(i, 6, QTableWidgetItem(txn.status))
                
                # Approve/Reject Actions Buttons if Pending
                if txn.status == "Pending":
                    btn_widget = QWidget()
                    btn_layout = QHBoxLayout(btn_widget)
                    btn_layout.setContentsMargins(0, 0, 0, 0)
                    btn_layout.setSpacing(4)
                    
                    btn_app = QPushButton("✓")
                    btn_app.setToolTip("Approve Leave")
                    btn_app.setProperty("class", "PrimaryBtn")
                    btn_app.clicked.connect(lambda checked=False, tid=txn.id: self.approve_leave(tid))
                    
                    btn_rej = QPushButton("✗")
                    btn_rej.setToolTip("Reject Leave")
                    btn_rej.setProperty("class", "DangerBtn")
                    btn_rej.clicked.connect(lambda checked=False, tid=txn.id: self.reject_leave(tid))
                    
                    btn_layout.addWidget(btn_app)
                    btn_layout.addWidget(btn_rej)
                    
                    self.tbl_history.setCellWidget(i, 7, btn_widget)
                else:
                    self.tbl_history.setItem(i, 7, QTableWidgetItem(f"Done by {txn.approved_by or 'System'}"))
        finally:
            db.close()

    def apply_leave(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            QMessageBox.warning(self, "Selection Required", "Please select an employee first.")
            return

        l_type = self.cmb_leave_type.currentText()
        start = self.date_start.date().toPython()
        end = self.date_end.date().toPython()
        reason = self.txt_reason.text().strip()

        if end < start:
            QMessageBox.critical(self, "Validation Error", "End Date cannot be before Start Date.")
            return

        db = SessionLocal()
        try:
            success = LeaveService.apply_leave(db, emp_id, l_type, start, end, reason)
            if success:
                QMessageBox.information(self, "Success", "Leave request logged successfully.")
                self.txt_reason.clear()
                self.refresh_transactions()
            else:
                QMessageBox.critical(
                    self, "Insufficient Balance", 
                    "Unable to apply leave. Insufficient remaining balance for this leave type."
                )
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to submit leave: {str(e)}")
        finally:
            db.close()

    def approve_leave(self, txn_id):
        db = SessionLocal()
        try:
            success = LeaveService.approve_leave(db, txn_id, "HR Manager")
            if success:
                QMessageBox.information(self, "Approved", "Leave request approved and balance updated.")
                self.refresh_balances()
                self.refresh_transactions()
            else:
                QMessageBox.critical(self, "Action Failed", "Failed to approve leave (possibly insufficient balance).")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to approve: {e}")
        finally:
            db.close()

    def reject_leave(self, txn_id):
        db = SessionLocal()
        try:
            success = LeaveService.reject_leave(db, txn_id, "HR Manager")
            if success:
                QMessageBox.information(self, "Rejected", "Leave request marked as Rejected.")
                self.refresh_transactions()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to reject: {e}")
        finally:
            db.close()
