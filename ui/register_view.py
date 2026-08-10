from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QScrollArea, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Employee, Payroll, Department
from reports.excel_exporter import ExcelExporter
import pandas as pd
from datetime import datetime

class RegisterView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.current_df = None
        self.init_ui()
        self.refresh_register()

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

        title_lbl = QLabel("Monthly Payroll Register")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_lbl)

        # Period Selection
        selection_frame = QFrame()
        selection_frame.setProperty("class", "DashboardCard")
        selection_layout = QHBoxLayout(selection_frame)
        selection_layout.setContentsMargins(15, 15, 15, 15)

        selection_layout.addWidget(QLabel("Month:"))
        self.cmb_month = QComboBox()
        self.cmb_month.addItems([str(i) for i in range(1, 13)])
        self.cmb_month.setCurrentText(str(datetime.now().month))
        self.cmb_month.currentIndexChanged.connect(self.refresh_register)
        selection_layout.addWidget(self.cmb_month, 1)

        selection_layout.addWidget(QLabel("Year:"))
        self.cmb_year = QComboBox()
        self.cmb_year.addItems([str(y) for y in range(2020, 2031)])
        self.cmb_year.setCurrentText(str(datetime.now().year))
        self.cmb_year.currentIndexChanged.connect(self.refresh_register)
        selection_layout.addWidget(self.cmb_year, 1)
        
        selection_layout.addStretch(4)

        layout.addWidget(selection_frame)

        # Register Table
        table_frame = QFrame()
        table_frame.setProperty("class", "DashboardCard")
        table_layout = QVBoxLayout(table_frame)
        table_layout.addWidget(QLabel("<b>Payroll Registry Rows</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Employee ID", "Name", "Department", "Gross Salary", "PF", "ESI", "Advance", "Loan EMI", "Bonus/Inc", "Net Salary"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_layout.addWidget(self.table)

        layout.addWidget(table_frame)

        # Actions Bar
        actions_layout = QGridLayout()
        actions_layout.setSpacing(10)
        self.btn_excel = QPushButton("📥 Export Register (Excel)")
        self.btn_excel.setProperty("class", "PrimaryBtn")
        self.btn_excel.clicked.connect(self.export_excel)
        actions_layout.addWidget(self.btn_excel, 0, 0)

        self.btn_csv = QPushButton("📝 Export Register (CSV)")
        self.btn_csv.setProperty("class", "SecondaryBtn")
        self.btn_csv.clicked.connect(self.export_csv)
        actions_layout.addWidget(self.btn_csv, 0, 1)

        layout.addLayout(actions_layout)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def refresh_register(self):
        m = int(self.cmb_month.currentText())
        y = int(self.cmb_year.currentText())

        db = SessionLocal()
        try:
            payroll_records = db.query(Payroll).filter(
                Payroll.month == m,
                Payroll.year == y,
                Payroll.status == "Processed"
            ).all()

            self.table.setRowCount(len(payroll_records))
            
            data = []
            for i, pay in enumerate(payroll_records):
                emp = pay.employee
                dept_name = emp.department.name if emp.department else "N/A"
                
                # Fill Table
                self.table.setItem(i, 0, QTableWidgetItem(emp.employee_code))
                self.table.setItem(i, 1, QTableWidgetItem(emp.name))
                self.table.setItem(i, 2, QTableWidgetItem(dept_name))
                self.table.setItem(i, 3, QTableWidgetItem(f"₹{int(round(pay.gross_salary)):,}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"₹{int(round(pay.pf_deduction)):,}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"₹{int(round(pay.esi_deduction)):,}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"₹{int(round(pay.advance_recovery)):,}"))
                self.table.setItem(i, 7, QTableWidgetItem(f"₹{int(round(pay.loan_emi)):,}"))
                self.table.setItem(i, 8, QTableWidgetItem(f"₹{int(round(pay.bonus_amount + pay.incentive_amount)):,}"))
                self.table.setItem(i, 9, QTableWidgetItem(f"₹{int(round(pay.net_salary)):,}"))
                
                # Collect for export
                data.append({
                    "Employee ID": emp.employee_code,
                    "Name": emp.name,
                    "Department": dept_name,
                    "Gross Salary": pay.gross_salary,
                    "PF": pay.pf_deduction,
                    "ESI": pay.esi_deduction,
                    "Advance": pay.advance_recovery,
                    "Loan": pay.loan_emi,
                    "Bonus/Inc": pay.bonus_amount + pay.incentive_amount,
                    "Net Salary": pay.net_salary
                })
            
            self.current_df = pd.DataFrame(data)
        finally:
            db.close()

    def export_excel(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "No Data", "No processed payroll records to export.")
            return

        m = self.cmb_month.currentText()
        y = self.cmb_year.currentText()
        fn = f"PayrollRegister_{y}_{m}.xlsx"
        try:
            path = ExcelExporter.export_dataframe(self.current_df, "Payroll Register", fn)
            QMessageBox.information(self, "Export Successful", f"Register spreadsheet saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Excel generation failed: {e}")

    def export_csv(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "No Data", "No processed payroll records to export.")
            return

        m = self.cmb_month.currentText()
        y = self.cmb_year.currentText()
        fn = f"PayrollRegister_{y}_{m}.csv"
        try:
            path = ExcelExporter.export_csv(self.current_df, fn)
            QMessageBox.information(self, "Export Successful", f"Register CSV saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"CSV generation failed: {e}")
