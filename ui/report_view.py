from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QDialog, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor
from database.connection import SessionLocal
from database.models import Employee, Attendance, Payroll, Department, Bonus, Advance, Loan
from reports.excel_exporter import ExcelExporter
import pandas as pd
from datetime import datetime

class ReportCard(QFrame):
    def __init__(self, title, desc, report_type, category, theme="dark", parent_view=None):
        super().__init__()
        self.title = title
        self.desc = desc
        self.report_type = report_type
        self.category = category
        self.theme = theme
        self.parent_view = parent_view
        
        self.setProperty("class", "DashboardCard")
        self.setMinimumHeight(90)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)
        
        # Left Icon Badge
        icon_badge = QLabel()
        icon_badge.setFixedSize(45, 45)
        icon_badge.setAlignment(Qt.AlignCenter)
        icon_badge.setFont(QFont("Segoe UI", 16))
        
        # Differentiate badge backgrounds by category
        if category == "Payroll":
            icon_badge.setText("⭐")
            icon_badge.setStyleSheet("background-color: #ede9fe; color: #7c3aed; border-radius: 8px;")
        elif category == "Attendance":
            icon_badge.setText("📅")
            icon_badge.setStyleSheet("background-color: #dcfce7; color: #16a34a; border-radius: 8px;")
        elif category == "Tax":
            icon_badge.setText("⚖️")
            icon_badge.setStyleSheet("background-color: #fee2e2; color: #dc2626; border-radius: 8px;")
        elif category == "Finance":
            icon_badge.setText("💰")
            icon_badge.setStyleSheet("background-color: #ffedd5; color: #ea580c; border-radius: 8px;")
        else: # Asset
            icon_badge.setText("💼")
            icon_badge.setStyleSheet("background-color: #e0f2fe; color: #0284c7; border-radius: 8px;")
            
        layout.addWidget(icon_badge)
        
        # Text details
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_lbl.setStyleSheet("color: #ffffff;" if theme == "dark" else "color: #0f172a;")
        
        desc_lbl = QLabel(desc)
        desc_lbl.setFont(QFont("Segoe UI", 9))
        desc_lbl.setStyleSheet("color: #94a3b8;")
        desc_lbl.setWordWrap(True)
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)
        layout.addLayout(text_layout, 4)
        
        # Actions Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        self.btn_preview = QPushButton("👁️")
        self.btn_preview.setToolTip("Quick Preview")
        self.btn_preview.setFixedSize(30, 30)
        self.btn_preview.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #334155; border-radius: 6px; color: #38bdf8; font-size: 14px;
            }
            QPushButton:hover { background-color: #1e293b; }
        """ if theme == "dark" else """
            QPushButton {
                background: transparent; border: 1px solid #cbd5e1; border-radius: 6px; color: #0284c7; font-size: 14px;
            }
            QPushButton:hover { background-color: #f1f5f9; }
        """)
        self.btn_preview.clicked.connect(self.trigger_generation)
        actions_layout.addWidget(self.btn_preview)
        
        self.btn_config = QPushButton("🔧")
        self.btn_config.setToolTip("Configure Options")
        self.btn_config.setFixedSize(30, 30)
        self.btn_config.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #334155; border-radius: 6px; color: #a855f7; font-size: 14px;
            }
            QPushButton:hover { background-color: #1e293b; }
        """ if theme == "dark" else """
            QPushButton {
                background: transparent; border: 1px solid #cbd5e1; border-radius: 6px; color: #7c3aed; font-size: 14px;
            }
            QPushButton:hover { background-color: #f1f5f9; }
        """)
        self.btn_config.clicked.connect(self.trigger_generation)
        actions_layout.addWidget(self.btn_config)
        
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setProperty("class", "PrimaryBtn")
        self.btn_generate.setStyleSheet("background-color: #4f46e5; color: white; padding: 5px 12px; font-weight: bold; border-radius: 6px;")
        self.btn_generate.clicked.connect(self.trigger_generation)
        actions_layout.addWidget(self.btn_generate)
        
        layout.addLayout(actions_layout, 2)

    def trigger_generation(self):
        if self.parent_view:
            self.parent_view.open_report_dialog(self.title, self.report_type)

class ReportPreviewDialog(QDialog):
    def __init__(self, title, report_type, theme="dark", parent=None):
        super().__init__(parent)
        self.title = title
        self.report_type = report_type
        self.theme = theme
        self.current_df = None
        self.init_ui()
        self.load_departments()
        self.run_preview()
        
    def init_ui(self):
        self.setWindowTitle(f"Generate Report: {self.title}")
        self.resize(900, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #111115;
                color: #ffffff;
            }
        """ if self.theme == "dark" else """
            QDialog {
                background-color: #f8fafc;
                color: #0f172a;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Report Title Header
        header = QLabel(self.title)
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Filters Form Frame
        filters_frame = QFrame()
        filters_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a20; border: 1px solid #2d2d35; border-radius: 8px; padding: 10px;
            }
        """ if self.theme == "dark" else """
            QFrame {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;
            }
        """)
        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(10, 5, 10, 5)
        filters_layout.setSpacing(12)
        
        filters_layout.addWidget(QLabel("Department:"))
        self.cmb_dept = QComboBox()
        self.cmb_dept.setMinimumWidth(120)
        filters_layout.addWidget(self.cmb_dept)
        
        filters_layout.addWidget(QLabel("Month:"))
        self.cmb_month = QComboBox()
        self.cmb_month.addItems(["All"] + [str(i) for i in range(1, 13)])
        self.cmb_month.setCurrentText(str(datetime.now().month))
        filters_layout.addWidget(self.cmb_month)
        
        filters_layout.addWidget(QLabel("Year:"))
        self.cmb_year = QComboBox()
        self.cmb_year.addItems([str(y) for y in range(2020, 2031)])
        self.cmb_year.setCurrentText(str(datetime.now().year))
        filters_layout.addWidget(self.cmb_year)
        
        self.btn_preview = QPushButton("🔍 Preview")
        self.btn_preview.setStyleSheet("background-color: #4f46e5; color: white; padding: 5px 15px; font-weight: bold; border-radius: 6px;")
        self.btn_preview.clicked.connect(self.run_preview)
        filters_layout.addWidget(self.btn_preview)
        
        layout.addWidget(filters_frame)
        
        # Preview Table
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a20;
                alternate-background-color: #22222a;
                border: 1px solid #2d2d35;
                color: #ffffff;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #272730;
                color: #94a3b8;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """ if self.theme == "dark" else """
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                color: #0f172a;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #64748b;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)
        
        # Export Actions Bottom Row
        actions_layout = QHBoxLayout()
        
        self.btn_excel = QPushButton("📥 Export to Excel")
        self.btn_excel.setStyleSheet("background-color: #16a34a; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_excel.clicked.connect(self.export_excel)
        actions_layout.addWidget(self.btn_excel)
        
        self.btn_csv = QPushButton("📝 Export to CSV")
        self.btn_csv.setStyleSheet("background-color: #0284c7; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_csv.clicked.connect(self.export_csv)
        actions_layout.addWidget(self.btn_csv)
        
        actions_layout.addStretch()
        
        self.btn_close = QPushButton("Cancel")
        self.btn_close.setStyleSheet("background-color: #334155; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_close.clicked.connect(self.reject)
        actions_layout.addWidget(self.btn_close)
        
        layout.addLayout(actions_layout)

    def load_departments(self):
        db = SessionLocal()
        try:
            self.cmb_dept.clear()
            self.cmb_dept.addItem("All", None)
            depts = db.query(Department).all()
            for d in depts:
                self.cmb_dept.addItem(d.name, d.id)
        finally:
            db.close()

    def run_preview(self):
        dept_id = self.cmb_dept.currentData()
        month_txt = self.cmb_month.currentText()
        year_txt = self.cmb_year.currentText()
        
        m = None if month_txt == "All" else int(month_txt)
        y = int(year_txt)

        db = SessionLocal()
        df = None
        try:
            if self.report_type == "Attendance Report":
                query = db.query(Attendance).join(Employee)
                if dept_id: query = query.filter(Employee.department_id == dept_id)
                if m: query = query.filter(Attendance.month == m)
                query = query.filter(Attendance.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "Month/Year": f"{r.month}/{r.year}",
                    "Working Days": r.working_days,
                    "Present Days": r.full_days + (r.half_days * 0.5),
                    "Absent Days": r.absent_days,
                    "Paid Leaves": r.paid_leave,
                    "Worked Weekly Off": r.worked_on_weekly_off,
                    "Overtime Hours": r.overtime_hours
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "Salary Report":
                query = db.query(Payroll).join(Employee)
                if dept_id: query = query.filter(Employee.department_id == dept_id)
                if m: query = query.filter(Payroll.month == m)
                query = query.filter(Payroll.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "Gross Salary": r.gross_salary,
                    "Allowances": r.total_allowances,
                    "Deductions": r.total_deductions,
                    "Net Salary": r.net_salary,
                    "Status": r.status
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "Department Report":
                results = db.query(
                    Department.name,
                    func.count(Employee.id),
                    func.sum(Employee.monthly_salary)
                ).join(Employee, Employee.department_id == Department.id).group_by(Department.name).all()
                data = [{
                    "Department": r[0],
                    "Total Employees": r[1],
                    "CTC Monthly": r[2] or 0.0
                } for r in results]
                df = pd.DataFrame(data)

            elif self.report_type == "Monthly Payroll Report":
                query = db.query(Payroll).join(Employee)
                if m: query = query.filter(Payroll.month == m)
                query = query.filter(Payroll.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "Net Salary": r.net_salary,
                    "PF": r.pf_deduction,
                    "ESI": r.esi_deduction,
                    "PT": r.prof_tax_deduction,
                    "TDS": r.tds_deduction,
                    "Processed At": r.processed_at
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "PF Report":
                query = db.query(Payroll).join(Employee)
                if m: query = query.filter(Payroll.month == m)
                query = query.filter(Payroll.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "PF Number": r.employee.pf_number or "N/A",
                    "UAN": r.employee.uan or "N/A",
                    "Basic Pay": r.gross_salary,
                    "PF Deduction (12%)": r.pf_deduction
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "ESI Report":
                query = db.query(Payroll).join(Employee)
                if m: query = query.filter(Payroll.month == m)
                query = query.filter(Payroll.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "ESI Number": r.employee.esic_number or "N/A",
                    "Gross Pay": r.gross_salary + r.total_allowances,
                    "ESI Deduction (0.75%)": r.esi_deduction
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "TDS Report":
                query = db.query(Payroll).join(Employee)
                if m: query = query.filter(Payroll.month == m)
                query = query.filter(Payroll.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "PAN Card": r.employee.pan_number or "N/A",
                    "Total Earnings": r.gross_salary + r.total_allowances,
                    "TDS Deducted": r.tds_deduction
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "Bonus Report":
                query = db.query(Bonus).join(Employee)
                if m: query = query.filter(Bonus.month == m)
                query = query.filter(Bonus.year == y)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "Bonus Type": r.type,
                    "Amount": r.amount,
                    "Status": r.status
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "Advance Report":
                query = db.query(Advance).join(Employee)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "Advance Amount": r.advance_amount,
                    "EMI Recovery": r.emi_amount,
                    "Balance Outstanding": r.balance_amount,
                    "Status": r.status
                } for r in records]
                df = pd.DataFrame(data)

            elif self.report_type == "Loan Report":
                query = db.query(Loan).join(Employee)
                records = query.all()
                data = [{
                    "Emp Code": r.employee.employee_code,
                    "Name": r.employee.name,
                    "Principal Loan": r.loan_amount,
                    "Interest Rate": f"{r.interest_rate}%",
                    "Monthly EMI": r.emi_amount,
                    "Outstanding Balance": r.balance_amount,
                    "Status": r.status
                } for r in records]
                df = pd.DataFrame(data)

            else: # Employee Summary & Default Empty Cases
                query = db.query(Employee)
                if dept_id: query = query.filter(Employee.department_id == dept_id)
                records = query.all()
                data = [{
                    "Emp Code": r.employee_code,
                    "Name": r.name,
                    "Mobile": r.mobile,
                    "Email": r.email,
                    "Employment Type": r.employment_type,
                    "CTC Salary": r.monthly_salary,
                    "Status": r.status
                } for r in records]
                df = pd.DataFrame(data)

            if df is None or df.empty:
                df = pd.DataFrame([["No data available for selected filters"]], columns=["Message"])

            self.current_df = df
            self.display_preview(df)

        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to execute report query: {e}")
        finally:
            db.close()

    def display_preview(self, df: pd.DataFrame):
        self.table.clear()
        self.table.setColumnCount(len(df.columns))
        self.table.setRowCount(len(df.index))
        self.table.setHorizontalHeaderLabels(list(df.columns))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row in range(len(df.index)):
            for col in range(len(df.columns)):
                val = df.iloc[row, col]
                if isinstance(val, float):
                    item = QTableWidgetItem(f"{int(round(val)):,}")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item = QTableWidgetItem(str(val if val is not None else ""))
                self.table.setItem(row, col, item)

    def export_excel(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "No Data", "Preview the report first before exporting.")
            return
        
        rep_type = self.report_type.replace(" ", "")
        fn = f"{rep_type}_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        try:
            path = ExcelExporter.export_dataframe(self.current_df, self.title, fn)
            QMessageBox.information(self, "Export Successful", f"Report saved successfully to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Excel generation failed: {e}")

    def export_csv(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "No Data", "Preview the report first before exporting.")
            return

        rep_type = self.report_type.replace(" ", "")
        fn = f"{rep_type}_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            path = ExcelExporter.export_csv(self.current_df, fn)
            QMessageBox.information(self, "Export Successful", f"Report CSV saved successfully to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"CSV generation failed: {e}")

class ReportView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.report_cards = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Header Row
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_v_layout = QVBoxLayout()
        title_v_layout.setSpacing(2)
        title_lbl = QLabel("Reports")
        title_lbl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title_lbl.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")
        
        subtitle_lbl = QLabel("Generate and download important reports")
        subtitle_lbl.setFont(QFont("Segoe UI", 10))
        subtitle_lbl.setStyleSheet("color: #64748b;" if self.theme == "light" else "color: #94a3b8;")
        title_v_layout.addWidget(title_lbl)
        title_v_layout.addWidget(subtitle_lbl)
        header_layout.addLayout(title_v_layout)
        
        # Center Search
        header_layout.addStretch()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search reports...")
        self.txt_search.setMinimumWidth(250)
        self.txt_search.textChanged.connect(self.filter_reports)
        header_layout.addWidget(self.txt_search)
        
        layout.addWidget(header_widget)

        # 2. Stats Bar Cards Row
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)
        
        stats_layout.addWidget(self.create_stat_card("Total Reports", "36", "All available reports", "purple"), 0, 0)
        stats_layout.addWidget(self.create_stat_card("Frequently Used", "12", "Your most used reports", "green"), 0, 1)
        stats_layout.addWidget(self.create_stat_card("Recently Generated", "05", "In last 7 days", "orange"), 1, 0)
        stats_layout.addWidget(self.create_stat_card("Scheduled Reports", "08", "Auto generated", "blue"), 1, 1)
        layout.addLayout(stats_layout)

        # 3. Report Categories
        # Category A: Payroll Reports
        layout.addWidget(self.create_category_header("Payroll Reports", "⭐"))
        grid_payroll = QGridLayout()
        grid_payroll.setSpacing(15)
        
        c1 = ReportCard("Muster Roll Report", "Monthly view of day wise attendance, fine, OT, etc. of all staff", "Attendance Report", "Payroll", self.theme, self)
        c2 = ReportCard("Staff Payroll Report", "Complete payroll report of all the staff", "Salary Report", "Payroll", self.theme, self)
        c3 = ReportCard("Staff Payroll Report (Date Range)", "Complete payroll report of all the staff based on date range", "Monthly Payroll Report", "Payroll", self.theme, self)
        
        self.report_cards.extend([c1, c2, c3])
        grid_payroll.addWidget(c1, 0, 0)
        grid_payroll.addWidget(c2, 0, 1)
        grid_payroll.addWidget(c3, 1, 0)
        
        layout.addLayout(grid_payroll)

        # Category B: Attendance & Leave Reports
        layout.addWidget(self.create_category_header("Attendance & Leave Reports", "📅"))
        grid_attendance = QGridLayout()
        grid_attendance.setSpacing(15)
        
        c4 = ReportCard("Applied Leaves Report", "This report will show all applied leaves details.", "Attendance Report", "Attendance", self.theme, self)
        c5 = ReportCard("Attendance Report", "Staff level summary for individual attendance cycle", "Attendance Report", "Attendance", self.theme, self)
        c6 = ReportCard("Daily Attendance Report", "Day wise attendance summary, individual attendance view and punch logs", "Attendance Report", "Attendance", self.theme, self)
        c7 = ReportCard("Leave Balance Report", "Staff level view of allowed leaves, leaves taken, leave remaining, etc.", "Employee Summary", "Attendance", self.theme, self)
        c8 = ReportCard("Leave Summary Report", "This report will show the leaves taken by an employee in a particular month", "Attendance Report", "Attendance", self.theme, self)
        c9 = ReportCard("Shift Performance Report", "Detailed breakdown of worked hours, fines, overtime, and breaks on daily-shift basis", "Attendance Report", "Attendance", self.theme, self)
        
        self.report_cards.extend([c4, c5, c6, c7, c8, c9])
        grid_attendance.addWidget(c4, 0, 0)
        grid_attendance.addWidget(c5, 0, 1)
        grid_attendance.addWidget(c6, 1, 0)
        grid_attendance.addWidget(c7, 1, 1)
        grid_attendance.addWidget(c8, 2, 0)
        grid_attendance.addWidget(c9, 2, 1)
        
        layout.addLayout(grid_attendance)

        # Category C: Tax & Deductions Reports
        layout.addWidget(self.create_category_header("Tax & Deductions Reports", "⚖️"))
        grid_tax = QGridLayout()
        grid_tax.setSpacing(15)
        
        c10 = ReportCard("PF Report", "Provident Fund deduction breakdown, UAN, and monthly deposits", "PF Report", "Tax", self.theme, self)
        c11 = ReportCard("ESI Report", "Employee State Insurance monthly contribution breakdown", "ESI Report", "Tax", self.theme, self)
        c12 = ReportCard("Professional Tax Report", "State-wise professional tax deductions report", "Professional Tax Report", "Tax", self.theme, self)
        c13 = ReportCard("TDS Report", "Tax Deducted at Source (Income Tax) monthly deductions report", "TDS Report", "Tax", self.theme, self)
        
        self.report_cards.extend([c10, c11, c12, c13])
        grid_tax.addWidget(c10, 0, 0)
        grid_tax.addWidget(c11, 0, 1)
        grid_tax.addWidget(c12, 1, 0)
        grid_tax.addWidget(c13, 1, 1)
        
        layout.addLayout(grid_tax)

        # Category D: Finance & Recovery Reports
        layout.addWidget(self.create_category_header("Finance & Recovery Reports", "💰"))
        grid_finance = QGridLayout()
        grid_finance.setSpacing(15)
        
        c14 = ReportCard("Bonus & Incentives Report", "All bonuses and incentives granted to employees in selected period", "Bonus Report", "Finance", self.theme, self)
        c15 = ReportCard("Advance Recovery Report", "Outstanding salary advances, recovery status, and balance", "Advance Report", "Finance", self.theme, self)
        c16 = ReportCard("Loan Recovery Report", "Outstanding employee loans, principal, EMI, and interest", "Loan Report", "Finance", self.theme, self)
        c17 = ReportCard("Employee Summary Report", "General summary list of active staff details and CTC salaries", "Employee Summary", "Finance", self.theme, self)
        
        self.report_cards.extend([c14, c15, c16, c17])
        grid_finance.addWidget(c14, 0, 0)
        grid_finance.addWidget(c15, 0, 1)
        grid_finance.addWidget(c16, 1, 0)
        grid_finance.addWidget(c17, 1, 1)
        
        layout.addLayout(grid_finance)

        # Category E: Asset Management Reports
        layout.addWidget(self.create_category_header("Asset Management Reports", "💼"))
        grid_assets = QGridLayout()
        grid_assets.setSpacing(15)
        
        c18 = ReportCard("Asset Assignment Report", "Assets currently assigned to employees with department, template and days held", "Employee Summary", "Asset", self.theme, self)
        c19 = ReportCard("Asset Inventory Report", "All assets with template, category, status, assignment and warranty details", "Employee Summary", "Asset", self.theme, self)
        
        self.report_cards.extend([c18, c19])
        grid_assets.addWidget(c18, 0, 0)
        grid_assets.addWidget(c19, 0, 1)
        
        layout.addLayout(grid_assets)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def create_stat_card(self, title, count, desc, color):
        card = QFrame()
        card.setProperty("class", "DashboardCard")
        card.setMinimumHeight(65)
        
        lay = QHBoxLayout(card)
        lay.setContentsMargins(15, 10, 15, 10)
        lay.setSpacing(12)
        
        icon = QLabel()
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont("Segoe UI", 13))
        
        if color == "purple":
            icon.setText("📄")
            icon.setStyleSheet("background-color: #ede9fe; color: #7c3aed; border-radius: 8px;")
        elif color == "green":
            icon.setText("📈")
            icon.setStyleSheet("background-color: #dcfce7; color: #16a34a; border-radius: 8px;")
        elif color == "orange":
            icon.setText("🕒")
            icon.setStyleSheet("background-color: #ffedd5; color: #ea580c; border-radius: 8px;")
        else: # blue
            icon.setText("☁️")
            icon.setStyleSheet("background-color: #e0f2fe; color: #0284c7; border-radius: 8px;")
            
        lay.addWidget(icon)
        
        v_lay = QVBoxLayout()
        v_lay.setSpacing(1)
        
        h_lay = QHBoxLayout()
        h_lay.setSpacing(5)
        lbl_count = QLabel(count)
        lbl_count.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl_title.setStyleSheet("color: #64748b;" if self.theme == "light" else "color: #94a3b8;")
        h_lay.addWidget(lbl_count)
        h_lay.addWidget(lbl_title)
        h_lay.addStretch()
        
        lbl_desc = QLabel(desc)
        lbl_desc.setFont(QFont("Segoe UI", 8))
        lbl_desc.setStyleSheet("color: #64748b;" if self.theme == "light" else "color: #475569;")
        
        v_lay.addLayout(h_lay)
        v_lay.addWidget(lbl_desc)
        
        lay.addLayout(v_lay)
        return card

    def create_category_header(self, title, icon_char):
        lbl = QLabel(f"<b>{icon_char} &nbsp; {title}</b>")
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setContentsMargins(0, 10, 0, 5)
        lbl.setStyleSheet("color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;" if self.theme == "light" else "color: #f8fafc; border-bottom: 2px solid #2d2d35; padding-bottom: 4px;")
        return lbl

    def filter_reports(self, text):
        search_query = text.lower().strip()
        for card in self.report_cards:
            if search_query in card.title.lower() or search_query in card.desc.lower():
                card.show()
            else:
                card.hide()

    def open_report_dialog(self, title, report_type):
        dialog = ReportPreviewDialog(title, report_type, self.theme, self)
        dialog.exec()
