from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QDateEdit)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Employee, Loan
from utilities.audit_logger import AuditLogger
from datetime import datetime

class LoanView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.load_employees()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        title_lbl = QLabel("Loan Management")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_lbl)

        # Split Layout
        split_layout = QHBoxLayout()
        split_layout.setSpacing(15)

        # Grant Form
        form_card = QFrame()
        form_card.setProperty("class", "DashboardCard")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 15, 15, 15)
        
        form_layout.addRow(QLabel("<b>Disburse Employee Loan</b>"))
        
        self.cmb_employee = QComboBox()
        self.cmb_employee.currentIndexChanged.connect(self.employee_changed)
        form_layout.addRow("Employee:", self.cmb_employee)

        self.txt_amount = QLineEdit()
        form_layout.addRow("Loan Amount (Principal):", self.txt_amount)

        self.txt_interest = QLineEdit("0.0")
        form_layout.addRow("Interest Rate (%):", self.txt_interest)

        self.txt_emi = QLineEdit()
        form_layout.addRow("Monthly EMI Amount:", self.txt_emi)

        self.date_issued = QDateEdit()
        self.date_issued.setCalendarPopup(True)
        self.date_issued.setDate(QDate.currentDate())
        form_layout.addRow("Disbursement Date:", self.date_issued)

        self.btn_save = QPushButton("Disburse Loan")
        self.btn_save.setProperty("class", "PrimaryBtn")
        self.btn_save.clicked.connect(self.save_loan)
        form_layout.addRow("", self.btn_save)

        split_layout.addWidget(form_card, 2)

        # List Card
        table_card = QFrame()
        table_card.setProperty("class", "DashboardCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)
        table_layout.addWidget(QLabel("<b>Loan Portfolios & Balances</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Principal", "Interest %", "EMI", "Issued Date", "Balance", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_layout.addWidget(self.table)

        split_layout.addWidget(table_card, 3)
        layout.addLayout(split_layout)

    def load_employees(self):
        db = SessionLocal()
        try:
            self.cmb_employee.clear()
            self.cmb_employee.addItem("-- Select Employee --", None)
            employees = db.query(Employee).filter(Employee.status == "Active").order_by(Employee.name).all()
            for emp in employees:
                self.cmb_employee.addItem(f"{emp.name} ({emp.employee_code})", emp.id)
        finally:
            db.close()

    def employee_changed(self):
        self.refresh_table()

    def refresh_table(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.table.setRowCount(0)
            return

        db = SessionLocal()
        try:
            loans = db.query(Loan).filter(Loan.employee_id == emp_id).order_by(Loan.date_issued.desc()).all()
            self.table.setRowCount(len(loans))
            for i, ln in enumerate(loans):
                self.table.setItem(i, 0, QTableWidgetItem(str(ln.id)))
                self.table.setItem(i, 1, QTableWidgetItem(f"₹{ln.loan_amount:,.2f}"))
                self.table.setItem(i, 2, QTableWidgetItem(f"{ln.interest_rate}%"))
                self.table.setItem(i, 3, QTableWidgetItem(f"₹{ln.emi_amount:,.2f}"))
                self.table.setItem(i, 4, QTableWidgetItem(str(ln.date_issued)))
                self.table.setItem(i, 5, QTableWidgetItem(f"₹{ln.balance_amount:,.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(ln.status))
        finally:
            db.close()

    def save_loan(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            QMessageBox.warning(self, "Selection Required", "Please select an employee.")
            return

        try:
            amount = float(self.txt_amount.text())
            interest = float(self.txt_interest.text())
            emi = float(self.txt_emi.text())
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid numeric amounts for Principal, Interest, and EMI.")
            return

        if emi <= 0 or amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount and EMI must be greater than zero.")
            return

        issue_dt = self.date_issued.date().toPython()
        
        # Simple interest calculation for total balance: Principal + (Principal * Interest / 100)
        total_repayable = amount + (amount * (interest / 100.0))

        db = SessionLocal()
        try:
            # Check for existing active loan
            active = db.query(Loan).filter(
                Loan.employee_id == emp_id,
                Loan.status == "Active"
            ).first()

            if active:
                QMessageBox.critical(self, "Disbursal Failed", "Employee has an active running loan. Refinance or close it before issuing a new one.")
                return

            ln = Loan(
                employee_id=emp_id,
                loan_amount=amount,
                interest_rate=interest,
                emi_amount=emi,
                balance_amount=total_repayable,
                date_issued=issue_dt,
                status="Active"
            )
            db.add(ln)
            db.commit()
            
            emp_name = self.cmb_employee.currentText()
            AuditLogger.log("Loan Issued", f"Disbursed loan of ₹{amount:,.2f} at {interest}% interest to {emp_name}. Repayable: ₹{total_repayable:,.2f}")
            QMessageBox.information(self, "Success", "Loan disbursed successfully.")
            self.txt_amount.clear()
            self.txt_interest.setText("0.0")
            self.txt_emi.clear()
            self.refresh_table()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save loan: {e}")
        finally:
            db.close()
