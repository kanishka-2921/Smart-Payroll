from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QDateEdit)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Employee, Advance
from utilities.audit_logger import AuditLogger
from datetime import datetime

class AdvanceView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.load_employees()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Title & Refresh H-Layout
        header_row = QHBoxLayout()
        title_lbl = QLabel("Salary Advance Management")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_row.addWidget(self.btn_refresh)

        layout.addLayout(header_row)

        # Split Layout
        split_layout = QHBoxLayout()
        split_layout.setSpacing(15)

        # Grant Form
        form_card = QFrame()
        form_card.setProperty("class", "DashboardCard")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 15, 15, 15)
        
        form_layout.addRow(QLabel("<b>Grant Salary Advance</b>"))
        
        self.cmb_employee = QComboBox()
        self.cmb_employee.currentIndexChanged.connect(self.employee_changed)
        form_layout.addRow("Employee:", self.cmb_employee)

        self.txt_amount = QLineEdit()
        form_layout.addRow("Advance Amount (INR):", self.txt_amount)

        self.txt_emi = QLineEdit()
        form_layout.addRow("Monthly Recovery EMI:", self.txt_emi)

        self.date_issued = QDateEdit()
        self.date_issued.setCalendarPopup(True)
        self.date_issued.setDate(QDate.currentDate())
        form_layout.addRow("Issue Date:", self.date_issued)

        self.txt_reason = QLineEdit()
        form_layout.addRow("Reason / Remarks:", self.txt_reason)

        self.btn_save = QPushButton("Grant Advance")
        self.btn_save.setProperty("class", "PrimaryBtn")
        self.btn_save.clicked.connect(self.save_advance)
        form_layout.addRow("", self.btn_save)

        split_layout.addWidget(form_card, 2)

        # List Card
        table_card = QFrame()
        table_card.setProperty("class", "DashboardCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)
        table_layout.addWidget(QLabel("<b>Active & Closed Advances</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Amount", "Issued Date", "Reason", "EMI", "Balance", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_layout.addWidget(self.table)

        split_layout.addWidget(table_card, 3)
        layout.addLayout(split_layout)

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
        self.refresh_table()

    def refresh_table(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.table.setRowCount(0)
            return

        db = SessionLocal()
        try:
            advances = db.query(Advance).filter(Advance.employee_id == emp_id).order_by(Advance.date_issued.desc()).all()
            self.table.setRowCount(len(advances))
            for i, adv in enumerate(advances):
                self.table.setItem(i, 0, QTableWidgetItem(str(adv.id)))
                self.table.setItem(i, 1, QTableWidgetItem(f"₹{adv.advance_amount:,.2f}"))
                self.table.setItem(i, 2, QTableWidgetItem(str(adv.date_issued)))
                self.table.setItem(i, 3, QTableWidgetItem(adv.reason or ""))
                self.table.setItem(i, 4, QTableWidgetItem(f"₹{adv.emi_amount:,.2f}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"₹{adv.balance_amount:,.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(adv.status))
        finally:
            db.close()

    def save_advance(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            QMessageBox.warning(self, "Selection Required", "Please select an employee.")
            return

        try:
            amount = float(self.txt_amount.text())
            emi = float(self.txt_emi.text())
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid numeric amounts for Advance and EMI.")
            return

        if emi > amount or emi <= 0:
            QMessageBox.warning(self, "Validation Error", "EMI must be greater than zero and cannot exceed total advance amount.")
            return

        issue_dt = self.date_issued.date().toPython()
        reason = self.txt_reason.text().strip()

        db = SessionLocal()
        try:
            # Check if there is an active advance already running
            active = db.query(Advance).filter(
                Advance.employee_id == emp_id, 
                Advance.status == "Active"
            ).first()
            
            if active:
                QMessageBox.critical(self, "Grant Failed", "This employee already has an active pending salary advance. Clear the active balance first.")
                return

            adv = Advance(
                employee_id=emp_id,
                advance_amount=amount,
                balance_amount=amount,
                emi_amount=emi,
                date_issued=issue_dt,
                reason=reason,
                status="Active"
            )
            db.add(adv)
            db.commit()
            
            emp_name = self.cmb_employee.currentText()
            AuditLogger.log("Advance Issued", f"Granted salary advance of ₹{amount:,.2f} to {emp_name} with EMI ₹{emi:,.2f}")
            QMessageBox.information(self, "Success", "Advance granted successfully.")
            self.txt_amount.clear()
            self.txt_emi.clear()
            self.txt_reason.clear()
            self.refresh_table()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save advance: {e}")
        finally:
            db.close()
