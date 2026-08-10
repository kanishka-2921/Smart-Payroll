from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Employee, Bonus
from utilities.audit_logger import AuditLogger
from datetime import datetime

class BonusView(QWidget):
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
        title_lbl = QLabel("Bonus Management")
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

        # Split Layout: Left Form, Right Table
        split_layout = QHBoxLayout()
        split_layout.setSpacing(15)

        # Form Card
        form_card = QFrame()
        form_card.setProperty("class", "DashboardCard")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 15, 15, 15)
        
        form_layout.addRow(QLabel("<b>Grant Employee Bonus</b>"))
        
        self.cmb_employee = QComboBox()
        self.cmb_employee.currentIndexChanged.connect(self.employee_changed)
        form_layout.addRow("Employee:", self.cmb_employee)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Festival Bonus", "Performance Bonus", "Referral Bonus", "Custom Bonus"])
        form_layout.addRow("Bonus Type:", self.cmb_type)

        self.txt_amount = QLineEdit()
        form_layout.addRow("Amount (INR):", self.txt_amount)

        self.cmb_month = QComboBox()
        self.cmb_month.addItems([str(i) for i in range(1, 13)])
        self.cmb_month.setCurrentText(str(datetime.now().month))
        form_layout.addRow("Payout Month:", self.cmb_month)

        self.cmb_year = QComboBox()
        self.cmb_year.addItems([str(y) for y in range(2020, 2031)])
        self.cmb_year.setCurrentText(str(datetime.now().year))
        form_layout.addRow("Payout Year:", self.cmb_year)

        self.btn_save = QPushButton("Grant Bonus")
        self.btn_save.setProperty("class", "PrimaryBtn")
        self.btn_save.clicked.connect(self.save_bonus)
        form_layout.addRow("", self.btn_save)

        split_layout.addWidget(form_card, 2)

        # Table Card
        table_card = QFrame()
        table_card.setProperty("class", "DashboardCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)
        table_layout.addWidget(QLabel("<b>Bonus Distribution History</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Amount", "Period", "Status", "Actions"])
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
            bonuses = db.query(Bonus).filter(Bonus.employee_id == emp_id).order_by(Bonus.year.desc(), Bonus.month.desc()).all()
            self.table.setRowCount(len(bonuses))
            for i, b in enumerate(bonuses):
                self.table.setItem(i, 0, QTableWidgetItem(str(b.id)))
                self.table.setItem(i, 1, QTableWidgetItem(b.type))
                self.table.setItem(i, 2, QTableWidgetItem(f"₹{b.amount:,.2f}"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{b.month}/{b.year}"))
                self.table.setItem(i, 4, QTableWidgetItem(b.status))
                
                # Delete action button if Pending
                if b.status == "Pending":
                    btn_del = QPushButton("Delete")
                    btn_del.setProperty("class", "DangerBtn")
                    btn_del.clicked.connect(lambda checked=False, bid=b.id: self.delete_bonus(bid))
                    self.table.setCellWidget(i, 5, btn_del)
                else:
                    self.table.setItem(i, 5, QTableWidgetItem("Processed"))
        finally:
            db.close()

    def save_bonus(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            QMessageBox.warning(self, "Selection Required", "Please select an employee.")
            return

        try:
            amount = float(self.txt_amount.text())
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid numeric amount.")
            return

        b_type = self.cmb_type.currentText()
        month = int(self.cmb_month.currentText())
        year = int(self.cmb_year.currentText())

        db = SessionLocal()
        try:
            bonus = Bonus(
                employee_id=emp_id,
                type=b_type,
                amount=amount,
                month=month,
                year=year,
                status="Pending"
            )
            db.add(bonus)
            db.commit()
            
            emp_name = self.cmb_employee.currentText()
            AuditLogger.log("Bonus Granted", f"Granted {b_type} of ₹{amount:,.2f} to {emp_name} for period {month}/{year}")
            QMessageBox.information(self, "Success", "Bonus granted successfully.")
            self.txt_amount.clear()
            self.refresh_table()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save bonus: {e}")
        finally:
            db.close()

    def delete_bonus(self, bonus_id):
        db = SessionLocal()
        try:
            b = db.query(Bonus).filter(Bonus.id == bonus_id).first()
            if b and b.status == "Pending":
                db.delete(b)
                db.commit()
                QMessageBox.information(self, "Deleted", "Pending bonus deleted successfully.")
                self.refresh_table()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to delete bonus: {e}")
        finally:
            db.close()
