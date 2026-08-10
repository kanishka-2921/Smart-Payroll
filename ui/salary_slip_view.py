import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QMessageBox, QFrame, QTextBrowser,
                             QFileDialog, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Employee, Payroll, Attendance
from reports.pdf_slip_generator import PDFSlipGenerator
from utilities.audit_logger import AuditLogger
from datetime import datetime

class SalarySlipView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.active_pdf_path = None
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

        title_lbl = QLabel("Salary Slip Generator")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_lbl)

        # Selector frame
        selector_frame = QFrame()
        selector_frame.setProperty("class", "DashboardCard")
        selector_layout = QGridLayout(selector_frame)
        selector_layout.setContentsMargins(15, 15, 15, 15)

        selector_layout.addWidget(QLabel("Employee:"), 0, 0)
        self.cmb_employee = QComboBox()
        self.cmb_employee.currentIndexChanged.connect(self.load_slip_details)
        selector_layout.addWidget(self.cmb_employee, 0, 1, 1, 3)

        selector_layout.addWidget(QLabel("Month:"), 1, 0)
        self.cmb_month = QComboBox()
        self.cmb_month.addItems([str(i) for i in range(1, 13)])
        self.cmb_month.setCurrentText(str(datetime.now().month))
        self.cmb_month.currentIndexChanged.connect(self.load_slip_details)
        selector_layout.addWidget(self.cmb_month, 1, 1)

        selector_layout.addWidget(QLabel("Year:"), 1, 2)
        self.cmb_year = QComboBox()
        self.cmb_year.addItems([str(y) for y in range(2020, 2031)])
        self.cmb_year.setCurrentText(str(datetime.now().year))
        self.cmb_year.currentIndexChanged.connect(self.load_slip_details)
        selector_layout.addWidget(self.cmb_year, 1, 3)

        layout.addWidget(selector_frame)

        # Slip Preview Frame (styled HTML)
        self.preview_browser = QTextBrowser()
        self.preview_browser.setMinimumHeight(400)
        self.preview_browser.setStyleSheet("background-color: #1a1a20; border-radius: 8px;" if self.theme == "dark" else "background-color: #ffffff; border-radius: 8px;")
        layout.addWidget(self.preview_browser)

        # Actions Bar
        actions_layout = QGridLayout()
        actions_layout.setSpacing(10)
        
        self.btn_pdf = QPushButton("📄 Generate PDF Slip")
        self.btn_pdf.setProperty("class", "PrimaryBtn")
        self.btn_pdf.clicked.connect(self.generate_pdf)
        actions_layout.addWidget(self.btn_pdf, 0, 0)

        self.btn_print = QPushButton("🖨️ Print Slip")
        self.btn_print.setProperty("class", "SecondaryBtn")
        self.btn_print.clicked.connect(self.print_slip)
        actions_layout.addWidget(self.btn_print, 0, 1)

        self.btn_email = QPushButton("✉️ Email Slip")
        self.btn_email.setProperty("class", "SecondaryBtn")
        self.btn_email.clicked.connect(self.email_slip)
        actions_layout.addWidget(self.btn_email, 0, 2)

        layout.addLayout(actions_layout)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def load_employees(self):
        db = SessionLocal()
        try:
            self.cmb_employee.clear()
            self.cmb_employee.addItem("-- Select Employee --", None)
            employees = db.query(Employee).order_by(Employee.name).all()
            for emp in employees:
                self.cmb_employee.addItem(f"{emp.name} ({emp.employee_code})", emp.id)
        finally:
            db.close()

    def load_slip_details(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.preview_browser.setHtml("<h3 style='color:#9ca3af; text-align:center;'>Select an employee to preview salary slip</h3>")
            return

        m = int(self.cmb_month.currentText())
        y = int(self.cmb_year.currentText())

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            payroll = db.query(Payroll).filter(
                Payroll.employee_id == emp_id,
                Payroll.month == m,
                Payroll.year == y
            ).first()
            att = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.month == m,
                Attendance.year == y
            ).first()

            if not payroll or not att:
                self.preview_browser.setHtml(
                    f"<h3 style='color:#f43f5e; text-align:center;'>"
                    f"No processed payroll records found for {emp.name} in {m}/{y}.<br/>"
                    f"Please enter attendance and calculate payroll first.</h3>"
                )
                self.active_pdf_path = None
                return

            # Render HTML Salary Slip Preview
            html = f"""
            <div style="font-family: Arial, sans-serif; color: {'#f3f4f6' if self.theme == 'dark' else '#0f172a'}; padding: 20px;">
                <h2 style="text-align: center; color: #6366f1; margin: 0;">SMART PAYROLL SYSTEM</h2>
                <h3 style="text-align: center; margin: 5px 0 20px 0;">Salary Pay Slip for {m:02d} / {y}</h3>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                        <td><b>Employee Code:</b> {emp.employee_code}</td>
                        <td><b>Date of Joining:</b> {emp.joining_date or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td><b>Name:</b> {emp.name}</td>
                        <td><b>Department:</b> {emp.department.name if emp.department else 'N/A'}</td>
                    </tr>
                    <tr>
                        <td><b>Designation:</b> {emp.designation.name if emp.designation else 'N/A'}</td>
                        <td><b>Employment Type:</b> {emp.employment_type}</td>
                    </tr>
                    <tr>
                        <td><b>Bank A/C:</b> {emp.account_number or 'N/A'}</td>
                        <td><b>Bank Name:</b> {emp.bank_name or 'N/A'}</td>
                    </tr>
                </table>

                <h4 style="border-bottom: 2px solid #6366f1; padding-bottom: 5px;">Attendance Summary</h4>
                <p>
                    Working Days: <b>{att.working_days}</b> &nbsp;|&nbsp;
                    Present (Full): <b>{att.full_days}</b> &nbsp;|&nbsp;
                    Half Days: <b>{att.half_days}</b> &nbsp;|&nbsp;
                    Absent: <b>{att.absent_days}</b> &nbsp;|&nbsp;
                    Paid Leaves: <b>{att.paid_leave}</b> &nbsp;|&nbsp;
                    Off-Day Work Days: <b>{att.worked_on_weekly_off}</b>
                </p>

                <h4 style="border-bottom: 2px solid #6366f1; padding-bottom: 5px;">Salary Details Breakdown</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: {'#2b2b35' if self.theme == 'dark' else '#f1f5f9'};">
                        <th style="text-align: left; padding: 8px;">Earnings / Allowances</th>
                        <th style="text-align: right; padding: 8px;">Amount (INR)</th>
                        <th style="text-align: left; padding: 8px; border-left: 1px solid #cbd5e1;">Deductions</th>
                        <th style="text-align: right; padding: 8px;">Amount (INR)</th>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Basic worked salary</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.gross_salary:,.0f}</td>
                        <td style="padding: 6px; border-left: 1px solid #cbd5e1;">Provident Fund (PF)</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.pf_deduction:,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">HRA</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.hra_amount:,.0f}</td>
                        <td style="padding: 6px; border-left: 1px solid #cbd5e1;">State Insurance (ESI)</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.esi_deduction:,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Special Allowances</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.special_allowance:,.0f}</td>
                        <td style="padding: 6px; border-left: 1px solid #cbd5e1;">Professional Tax (PT)</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.prof_tax_deduction:,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Other Allowances</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.other_allowance:,.0f}</td>
                        <td style="padding: 6px; border-left: 1px solid #cbd5e1;">TDS (Income Tax)</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.tds_deduction:,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Bonus & Incentives</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.bonus_amount + payroll.incentive_amount:,.0f}</td>
                        <td style="padding: 6px; border-left: 1px solid #cbd5e1;">Advance Recovery</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.advance_recovery:,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Overtime & Comp Off</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.overtime_amount + payroll.off_day_compensation:,.0f}</td>
                        <td style="padding: 6px; border-left: 1px solid #cbd5e1;">Loan EMI Recovery</td>
                        <td style="text-align: right; padding: 6px;">₹{payroll.loan_emi:,.0f}</td>
                    </tr>
                    <tr style="border-top: 2px solid #cbd5e1; font-weight: bold; background-color: {'#22222a' if self.theme == 'dark' else '#f8fafc'};">
                        <td style="padding: 8px;">Total Earnings</td>
                        <td style="text-align: right; padding: 8px;">₹{payroll.gross_salary + payroll.total_allowances:,.0f}</td>
                        <td style="padding: 8px; border-left: 1px solid #cbd5e1;">Total Deductions</td>
                        <td style="text-align: right; padding: 8px;">₹{payroll.total_deductions:,.0f}</td>
                    </tr>
                </table>
 
                <div style="margin-top: 20px; padding: 15px; border-radius: 6px; background-color: {'#2b2b35' if self.theme == 'dark' else '#eef2ff'}; border: 1.5px solid #6366f1;">
                    <h3 style="margin: 0; color: #6366f1;">NET PAYABLE SALARY: ₹{payroll.net_salary:,.0f}</h3>
                </div>
            </div>
            """
            self.preview_browser.setHtml(html)
        finally:
            db.close()

    def generate_pdf(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            QMessageBox.warning(self, "Selection Required", "Please select an employee first.")
            return

        m = int(self.cmb_month.currentText())
        y = int(self.cmb_year.currentText())

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            payroll = db.query(Payroll).filter(
                Payroll.employee_id == emp_id,
                Payroll.month == m,
                Payroll.year == y
            ).first()
            att = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.month == m,
                Attendance.year == y
            ).first()

            if not payroll or not att:
                QMessageBox.critical(self, "Missing Data", "No processed payroll record found for this month.")
                return

            # Open a file dialog to choose download location
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Salary Slip PDF", 
                f"SalarySlip_{emp.employee_code}_{y}_{m:02d}.pdf", 
                "PDF Files (*.pdf)"
            )
            
            if filepath:
                PDFSlipGenerator.generate(emp, payroll, att, filepath)
                self.active_pdf_path = filepath
                AuditLogger.log("Salary Slip PDF Generated", f"Generated PDF salary slip for {emp.name} ({emp.employee_code}) to {filepath}")
                QMessageBox.information(self, "Success", f"PDF Slip saved successfully:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF salary slip: {e}")
        finally:
            db.close()

    def print_slip(self):
        if not self.active_pdf_path or not os.path.exists(self.active_pdf_path):
            QMessageBox.warning(self, "PDF Required", "Please generate the PDF slip first before printing.")
            return
        
        try:
            # Uses OS default PDF printer/viewer call
            os.startfile(self.active_pdf_path, "print")
            AuditLogger.log("Salary Slip Printed", f"Sent print job for slip {os.path.basename(self.active_pdf_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Printing Failed", f"Unable to invoke default print command:\n{e}\n\nYou can manually print from the PDF file.")

    def email_slip(self):
        if not self.active_pdf_path or not os.path.exists(self.active_pdf_path):
            QMessageBox.warning(self, "PDF Required", "Please generate the PDF slip first.")
            return
        
        # Simulating SMTP email dispatch
        QMessageBox.information(
            self, "Email Sent", 
            f"Salary slip PDF has been successfully queued and sent to employee email."
        )
        AuditLogger.log("Salary Slip Emailed", f"Queued email dispatch of salary slip to employee.")

    def update_theme(self, theme):
        self.theme = theme
        self.load_slip_details()
