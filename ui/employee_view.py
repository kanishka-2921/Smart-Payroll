import os
import shutil
import re
from datetime import date, datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
                             QFileDialog, QTabWidget, QDateEdit, QHeaderView, QAbstractItemView,
                             QProgressBar, QScrollArea, QFrame, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QPixmap
from database.connection import SessionLocal
from database.models import Employee, Department, Designation
from services.leave_service import LeaveService
from utilities.audit_logger import AuditLogger
from reports.excel_exporter import ExcelExporter
import pandas as pd
from datetime import datetime
from config import UPLOAD_DIR

class EmployeeView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.current_page = 1
        self.page_size = 10
        self.selected_employee_id = None
        self.new_mode = False
        
        self.init_ui()
        self.load_filters()
        self.refresh_employees()

    def init_ui(self):
        # Master Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area for rich dashboard contents
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Header Area
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_v_layout = QVBoxLayout()
        title_v_layout.setSpacing(2)
        title_lbl = QLabel("Employee Master")
        title_lbl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title_lbl.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")

        breadcrumb_lbl = QLabel("Dashboard  >  Employee Master")
        breadcrumb_lbl.setFont(QFont("Segoe UI", 10))
        breadcrumb_lbl.setStyleSheet("color: #6366f1;" if self.theme == "light" else "color: #818cf8;")
        title_v_layout.addWidget(title_lbl)
        title_v_layout.addWidget(breadcrumb_lbl)
        header_layout.addLayout(title_v_layout)

        # Header Search & Action buttons
        header_layout.addStretch()
        
        self.txt_header_search = QLineEdit()
        self.txt_header_search.setPlaceholderText("Search Employee (ID, Name, PAN, Mobile...)")
        self.txt_header_search.setMinimumWidth(150)
        self.txt_header_search.setMaximumWidth(280)
        self.txt_header_search.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.txt_header_search.textChanged.connect(self.header_search_changed)
        header_layout.addWidget(self.txt_header_search)

        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)

        self.btn_new = QPushButton("＋ New Employee")
        self.btn_new.setProperty("class", "PrimaryBtn")
        self.btn_new.setStyleSheet("background-color: #4f46e5; color: white;")
        self.btn_new.clicked.connect(self.new_employee_mode)
        header_layout.addWidget(self.btn_new)

        self.btn_import = QPushButton("📥 Import Excel")
        self.btn_import.setProperty("class", "SecondaryBtn")
        self.btn_import.clicked.connect(self.import_excel)
        header_layout.addWidget(self.btn_import)

        self.btn_export = QPushButton("📤 Export Excel")
        self.btn_export.setProperty("class", "SecondaryBtn")
        self.btn_export.clicked.connect(self.export_excel)
        header_layout.addWidget(self.btn_export)

        layout.addWidget(header_widget)

        # 2. Stats Row (4 Cards)
        stats_frame = QWidget()
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(15)

        # Card 1: Total Employees
        self.card_total = QFrame()
        self.card_total.setProperty("class", "DashboardCard")
        c1_lay = QVBoxLayout(self.card_total)
        c1_lay.addWidget(QLabel("👥 <b>Total Employees</b>"))
        self.lbl_stat_total = QLabel("0")
        self.lbl_stat_total.setFont(QFont("Segoe UI", 20, QFont.Bold))
        c1_lay.addWidget(self.lbl_stat_total)
        c1_lay.addWidget(QLabel("<span style='color:#a3a3a3;'>Active & Inactive</span>"))
        stats_layout.addWidget(self.card_total, 0, 0)

        # Card 2: Active Employees
        self.card_active = QFrame()
        self.card_active.setProperty("class", "DashboardCard")
        c2_lay = QVBoxLayout(self.card_active)
        c2_lay.addWidget(QLabel("🟢 <b>Active Employees</b>"))
        self.lbl_stat_active = QLabel("0")
        self.lbl_stat_active.setFont(QFont("Segoe UI", 20, QFont.Bold))
        c2_lay.addWidget(self.lbl_stat_active)
        self.lbl_stat_active_badge = QLabel("0%")
        self.lbl_stat_active_badge.setStyleSheet("color: #16a34a; font-weight: bold;")
        c2_lay.addWidget(self.lbl_stat_active_badge)
        stats_layout.addWidget(self.card_active, 0, 1)

        # Card 3: Inactive Employees
        self.card_inactive = QFrame()
        self.card_inactive.setProperty("class", "DashboardCard")
        c3_lay = QVBoxLayout(self.card_inactive)
        c3_lay.addWidget(QLabel("🟠 <b>Inactive Employees</b>"))
        self.lbl_stat_inactive = QLabel("0")
        self.lbl_stat_inactive.setFont(QFont("Segoe UI", 20, QFont.Bold))
        c3_lay.addWidget(self.lbl_stat_inactive)
        self.lbl_stat_inactive_badge = QLabel("0%")
        self.lbl_stat_inactive_badge.setStyleSheet("color: #ca8a04; font-weight: bold;")
        c3_lay.addWidget(self.lbl_stat_inactive_badge)
        stats_layout.addWidget(self.card_inactive, 1, 0)

        # Card 4: Resigned Employees
        self.card_resigned = QFrame()
        self.card_resigned.setProperty("class", "DashboardCard")
        c4_lay = QVBoxLayout(self.card_resigned)
        c4_lay.addWidget(QLabel("🔴 <b>Resigned Employees</b>"))
        self.lbl_stat_resigned = QLabel("0")
        self.lbl_stat_resigned.setFont(QFont("Segoe UI", 20, QFont.Bold))
        c4_lay.addWidget(self.lbl_stat_resigned)
        self.lbl_stat_resigned_badge = QLabel("0%")
        self.lbl_stat_resigned_badge.setStyleSheet("color: #dc2626; font-weight: bold;")
        c4_lay.addWidget(self.lbl_stat_resigned_badge)
        stats_layout.addWidget(self.card_resigned, 1, 1)

        layout.addWidget(stats_frame)

        # 3. Middle Area Split Layout (Form Tabs on Left, Status/Summary on Right)
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(15)

        # LEFT Form Tabs (60% width)
        self.form_card = QFrame()
        self.form_card.setProperty("class", "DashboardCard")
        form_layout_main = QVBoxLayout(self.form_card)
        form_layout_main.setContentsMargins(15, 15, 15, 15)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        form_layout_main.addWidget(self.tabs)

        # 3.1 Tab 1: Personal Information
        tab_personal = QWidget()
        tab_p_layout = QHBoxLayout(tab_personal)
        tab_p_layout.setContentsMargins(10, 10, 10, 10)
        tab_p_layout.setSpacing(15)

        # Photo & Scanner column
        photo_col = QVBoxLayout()
        photo_col.setSpacing(10)
        self.lbl_photo = QLabel()
        self.lbl_photo.setFixedSize(100, 100)
        self.lbl_photo.setStyleSheet("background-color: #2b2b35; border: 1px solid #3e3e4a; border-radius: 50px;" if self.theme == "dark" else "background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 50px;")
        self.lbl_photo.setAlignment(Qt.AlignCenter)
        self.lbl_photo.setText("👤")
        self.lbl_photo.setFont(QFont("Segoe UI", 36))
        photo_col.addWidget(self.lbl_photo, 0, Qt.AlignCenter)

        self.btn_upload_photo = QPushButton("📷 Upload Photo")
        self.btn_upload_photo.setProperty("class", "SecondaryBtn")
        self.btn_upload_photo.clicked.connect(self.upload_photo)
        photo_col.addWidget(self.btn_upload_photo)

        # Scanner button inline
        self.btn_scan = QPushButton("🔍 Autofetch Aadhaar/PAN")
        self.btn_scan.setProperty("class", "SecondaryBtn")
        self.btn_scan.setStyleSheet("background-color: #4f46e5; color: white;")
        self.btn_scan.clicked.connect(self.autofetch_document)
        photo_col.addWidget(self.btn_scan)
        photo_col.addStretch()
        tab_p_layout.addLayout(photo_col, 1)

        # Fields columns (Grid form)
        fields_grid = QWidget()
        fg_layout = QFormLayout(fields_grid)
        fg_layout.setHorizontalSpacing(15)
        fg_layout.setVerticalSpacing(10)

        self.txt_emp_id = QLineEdit()
        self.txt_emp_id.setReadOnly(True)
        self.txt_emp_id.setPlaceholderText("Auto Generated")
        
        self.txt_emp_code = QLineEdit()
        self.txt_emp_code.setReadOnly(True)
        self.txt_emp_code.setPlaceholderText("Auto Generated")
        
        self.cmb_title = QComboBox()
        self.cmb_title.addItems(["Mr.", "Ms.", "Mrs.", "Dr."])
        
        self.txt_first_name = QLineEdit()
        self.txt_middle_name = QLineEdit()
        self.txt_last_name = QLineEdit()
        
        self.date_dob = QDateEdit()
        self.date_dob.setCalendarPopup(True)
        self.date_dob.setDate(QDate(1995, 1, 1))
        
        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["Male", "Female", "Other"])
        
        self.cmb_marital = QComboBox()
        self.cmb_marital.addItems(["Single", "Married", "Divorced", "Widowed"])
        
        self.txt_father_name = QLineEdit()
        self.txt_nationality = QLineEdit("Indian")
        
        self.cmb_religion = QComboBox()
        self.cmb_religion.addItems(["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"])
        
        self.txt_pan = QLineEdit()
        self.txt_aadhaar = QLineEdit()
        
        self.cmb_blood = QComboBox()
        self.cmb_blood.addItems(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])

        fg_layout.addRow("Title:", self.cmb_title)
        fg_layout.addRow("First Name *:", self.txt_first_name)
        fg_layout.addRow("Middle Name:", self.txt_middle_name)
        fg_layout.addRow("Last Name:", self.txt_last_name)
        fg_layout.addRow("Date of Birth *:", self.date_dob)
        fg_layout.addRow("Gender *:", self.cmb_gender)
        fg_layout.addRow("Marital Status:", self.cmb_marital)
        fg_layout.addRow("Father's / Husband Name:", self.txt_father_name)
        fg_layout.addRow("Nationality:", self.txt_nationality)
        fg_layout.addRow("Religion:", self.cmb_religion)
        fg_layout.addRow("PAN Number:", self.txt_pan)
        fg_layout.addRow("Aadhaar Number:", self.txt_aadhaar)
        fg_layout.addRow("Blood Group:", self.cmb_blood)

        tab_p_layout.addWidget(fields_grid, 3)
        self.tabs.addTab(tab_personal, "Personal Information")

        # 3.2 Tab 2: Employment Details
        tab_employment = QWidget()
        tab_e_layout = QFormLayout(tab_employment)
        tab_e_layout.setContentsMargins(15, 15, 15, 15)
        tab_e_layout.setVerticalSpacing(10)

        self.cmb_dept = QComboBox()
        self.cmb_desig = QComboBox()
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Permanent", "Contract", "Intern", "Consultant"])
        
        self.txt_location = QLineEdit("Noida")
        self.txt_reporting_to = QLineEdit()
        
        tab_e_layout.addRow("Department *:", self.cmb_dept)
        tab_e_layout.addRow("Designation *:", self.cmb_desig)
        tab_e_layout.addRow("Employment Type:", self.cmb_type)
        tab_e_layout.addRow("Location:", self.txt_location)
        tab_e_layout.addRow("Reporting To:", self.txt_reporting_to)
        
        self.tabs.addTab(tab_employment, "Employment Details")

        # 3.3 Tab 3: Salary Information
        tab_salary = QWidget()
        tab_s_layout = QFormLayout(tab_salary)
        tab_s_layout.setContentsMargins(15, 15, 15, 15)
        tab_s_layout.setVerticalSpacing(10)

        self.txt_monthly_salary = QLineEdit("0.0")
        self.txt_half_day_salary = QLineEdit("0.0")
        
        tab_s_layout.addRow("Monthly Salary (Total CTC):", self.txt_monthly_salary)
        tab_s_layout.addRow("Half Day Salary:", self.txt_half_day_salary)
        
        self.tabs.addTab(tab_salary, "Salary Information")

        # 3.4 Tab 4: Bank & Statutory Details
        tab_bank = QWidget()
        tab_b_layout = QFormLayout(tab_bank)
        tab_b_layout.setContentsMargins(15, 15, 15, 15)
        tab_b_layout.setVerticalSpacing(10)

        self.txt_bank_name = QLineEdit()
        self.txt_account = QLineEdit()
        self.txt_ifsc = QLineEdit()
        self.txt_pf = QLineEdit()
        self.txt_esic = QLineEdit()
        self.txt_uan = QLineEdit()

        tab_b_layout.addRow("Bank Name:", self.txt_bank_name)
        tab_b_layout.addRow("Account Number:", self.txt_account)
        tab_b_layout.addRow("IFSC Code:", self.txt_ifsc)
        tab_b_layout.addRow("PF Number:", self.txt_pf)
        tab_b_layout.addRow("ESIC Number:", self.txt_esic)
        tab_b_layout.addRow("UAN:", self.txt_uan)
        
        self.tabs.addTab(tab_bank, "Bank & Statutory Details")

        # 3.5 Tab 5: Contact Details
        tab_contact = QWidget()
        tab_c_layout = QFormLayout(tab_contact)
        tab_c_layout.setContentsMargins(15, 15, 15, 15)
        tab_c_layout.setVerticalSpacing(10)

        self.txt_email = QLineEdit()
        self.txt_mobile = QLineEdit()
        self.txt_address = QLineEdit()
        self.txt_emergency = QLineEdit()

        tab_c_layout.addRow("Email Address:", self.txt_email)
        tab_c_layout.addRow("Mobile Number:", self.txt_mobile)
        tab_c_layout.addRow("Address:", self.txt_address)
        tab_c_layout.addRow("Emergency Contact:", self.txt_emergency)
        
        self.tabs.addTab(tab_contact, "Contact Details")

        # 3.6 Tab 6: Documents
        tab_docs = QWidget()
        tab_d_layout = QVBoxLayout(tab_docs)
        tab_d_layout.setContentsMargins(15, 15, 15, 15)
        tab_d_layout.addWidget(QLabel("📁 <b>Employee Documents Folder</b>"))
        self.lbl_docs_list = QLabel("No files uploaded.")
        tab_d_layout.addWidget(self.lbl_docs_list)
        tab_d_layout.addStretch()
        
        self.tabs.addTab(tab_docs, "Documents")

        # Save/Cancel Actions row inside Left Form Card
        actions_lay = QHBoxLayout()
        actions_lay.addStretch()
        
        self.btn_save_changes = QPushButton("💾 Update Details (Save)")
        self.btn_save_changes.setProperty("class", "PrimaryBtn")
        self.btn_save_changes.setStyleSheet("background-color: #16a34a; color: white;")
        self.btn_save_changes.clicked.connect(self.save_current_employee)
        actions_lay.addWidget(self.btn_save_changes)

        self.btn_save_as_new = QPushButton("➕ Save as NEW Employee")
        self.btn_save_as_new.setProperty("class", "PrimaryBtn")
        self.btn_save_as_new.setStyleSheet("background-color: #6366f1; color: white;")
        self.btn_save_as_new.clicked.connect(self.save_as_new_employee)
        actions_lay.addWidget(self.btn_save_as_new)

        self.btn_cancel = QPushButton("✖ Reset / Cancel")
        self.btn_cancel.setProperty("class", "SecondaryBtn")
        self.btn_cancel.clicked.connect(self.cancel_edit_mode)
        actions_lay.addWidget(self.btn_cancel)
        form_layout_main.addLayout(actions_lay)

        split_layout.addWidget(self.form_card, 3)

        # RIGHT Columns: Employee Status & Summary Cards (40% width)
        right_column = QVBoxLayout()
        right_column.setSpacing(15)

        # Status Card
        self.card_status = QFrame()
        self.card_status.setProperty("class", "DashboardCard")
        st_lay = QVBoxLayout(self.card_status)
        st_lay.setContentsMargins(15, 15, 15, 15)
        st_lay.setSpacing(10)
        
        st_title = QLabel("⚙️ Employee Status")
        st_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        st_lay.addWidget(st_title)

        st_form = QFormLayout()
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Active", "Inactive", "Resigned"])
        st_form.addRow("Status *:", self.cmb_status)

        self.date_joining = QDateEdit()
        self.date_joining.setCalendarPopup(True)
        self.date_joining.setDate(QDate.currentDate())
        st_form.addRow("Date of Joining *:", self.date_joining)

        self.date_probation = QDateEdit()
        self.date_probation.setCalendarPopup(True)
        self.date_probation.setDate(QDate.currentDate().addDays(180))
        st_form.addRow("Probation End Date:", self.date_probation)

        self.date_confirmation = QDateEdit()
        self.date_confirmation.setCalendarPopup(True)
        self.date_confirmation.setDate(QDate.currentDate().addDays(180))
        st_form.addRow("Confirmation Date:", self.date_confirmation)

        st_lay.addLayout(st_form)
        right_column.addWidget(self.card_status)

        # Summary Card
        self.card_summary = QFrame()
        self.card_summary.setProperty("class", "DashboardCard")
        sum_lay = QVBoxLayout(self.card_summary)
        sum_lay.setContentsMargins(15, 15, 15, 15)
        sum_lay.setSpacing(10)

        sum_title = QLabel("📝 Employee Summary")
        sum_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        sum_lay.addWidget(sum_title)

        self.summary_details_lay = QFormLayout()
        self.lbl_sum_dept = QLabel("None")
        self.lbl_sum_desig = QLabel("None")
        self.lbl_sum_type = QLabel("None")
        self.lbl_sum_loc = QLabel("None")
        self.lbl_sum_rep = QLabel("None")
        self.lbl_sum_email = QLabel("None")
        self.lbl_sum_mobile = QLabel("None")

        for lbl in [self.lbl_sum_dept, self.lbl_sum_desig, self.lbl_sum_type, self.lbl_sum_loc,
                    self.lbl_sum_rep, self.lbl_sum_email, self.lbl_sum_mobile]:
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("color: #cbd5e1;" if self.theme == "dark" else "color: #334155;")

        self.summary_details_lay.addRow("🏢 Department:", self.lbl_sum_dept)
        self.summary_details_lay.addRow("👔 Designation:", self.lbl_sum_desig)
        self.summary_details_lay.addRow("💼 Employment Type:", self.lbl_sum_type)
        self.summary_details_lay.addRow("📍 Location:", self.lbl_sum_loc)
        self.summary_details_lay.addRow("👤 Reporting To:", self.lbl_sum_rep)
        self.summary_details_lay.addRow("📧 Email:", self.lbl_sum_email)
        self.summary_details_lay.addRow("📱 Mobile:", self.lbl_sum_mobile)

        sum_lay.addLayout(self.summary_details_lay)
        right_column.addWidget(self.card_summary)

        split_layout.addLayout(right_column, 2)
        layout.addWidget(split_widget)

        # 4. Employment Snapshot Row (5 Small Cards)
        snapshot_frame = QWidget()
        snap_layout = QGridLayout(snapshot_frame)
        snap_layout.setContentsMargins(0, 0, 0, 0)
        snap_layout.setSpacing(10)

        # 4.1 Department
        self.snap_dept = QFrame()
        self.snap_dept.setProperty("class", "DashboardCard")
        sd_lay = QVBoxLayout(self.snap_dept)
        sd_lay.addWidget(QLabel("🏢 <b>Department</b>"))
        self.lbl_snap_dept_val = QLabel("-")
        self.lbl_snap_dept_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        sd_lay.addWidget(self.lbl_snap_dept_val)
        snap_layout.addWidget(self.snap_dept, 0, 0)

        # 4.2 Designation
        self.snap_desig = QFrame()
        self.snap_desig.setProperty("class", "DashboardCard")
        sds_lay = QVBoxLayout(self.snap_desig)
        sds_lay.addWidget(QLabel("👔 <b>Designation</b>"))
        self.lbl_snap_desig_val = QLabel("-")
        self.lbl_snap_desig_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        sds_lay.addWidget(self.lbl_snap_desig_val)
        snap_layout.addWidget(self.snap_desig, 0, 1)

        # 4.3 Employment Type
        self.snap_type = QFrame()
        self.snap_type.setProperty("class", "DashboardCard")
        stype_lay = QVBoxLayout(self.snap_type)
        stype_lay.addWidget(QLabel("💼 <b>Employment Type</b>"))
        self.lbl_snap_type_val = QLabel("-")
        self.lbl_snap_type_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        stype_lay.addWidget(self.lbl_snap_type_val)
        snap_layout.addWidget(self.snap_type, 0, 2)

        # 4.4 CTC
        self.snap_ctc = QFrame()
        self.snap_ctc.setProperty("class", "DashboardCard")
        sctc_lay = QVBoxLayout(self.snap_ctc)
        sctc_lay.addWidget(QLabel("💳 <b>CTC (Annual)</b>"))
        self.lbl_snap_ctc_val = QLabel("-")
        self.lbl_snap_ctc_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        sctc_lay.addWidget(self.lbl_snap_ctc_val)
        snap_layout.addWidget(self.snap_ctc, 1, 0)

        # 4.5 Reporting To
        self.snap_rep = QFrame()
        self.snap_rep.setProperty("class", "DashboardCard")
        srep_lay = QVBoxLayout(self.snap_rep)
        srep_lay.addWidget(QLabel("👤 <b>Reporting To</b>"))
        self.lbl_snap_rep_val = QLabel("-")
        self.lbl_snap_rep_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        srep_lay.addWidget(self.lbl_snap_rep_val)
        snap_layout.addWidget(self.snap_rep, 1, 1)

        layout.addWidget(snapshot_frame)

        # 5. Bottom Employee List Grid
        list_card = QFrame()
        list_card.setProperty("class", "DashboardCard")
        list_lay = QVBoxLayout(list_card)
        list_lay.setContentsMargins(15, 15, 15, 15)
        list_lay.setSpacing(10)

        # Filtering row
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(10)
        
        self.txt_filter_search = QLineEdit()
        self.txt_filter_search.setPlaceholderText("Search by Name, ID, Code, Department...")
        self.txt_filter_search.textChanged.connect(self.reset_and_refresh)
        filter_layout.addWidget(self.txt_filter_search, 3)

        self.cmb_filter_dept = QComboBox()
        self.cmb_filter_dept.addItem("All Departments")
        self.cmb_filter_dept.currentIndexChanged.connect(self.reset_and_refresh)
        filter_layout.addWidget(self.cmb_filter_dept, 1)

        self.cmb_filter_status = QComboBox()
        self.cmb_filter_status.addItems(["All Statuses", "Active", "Inactive", "Resigned"])
        self.cmb_filter_status.currentIndexChanged.connect(self.reset_and_refresh)
        filter_layout.addWidget(self.cmb_filter_status, 1)
        
        self.btn_reset_filters = QPushButton("🔍 Filter")
        self.btn_reset_filters.setProperty("class", "SecondaryBtn")
        self.btn_reset_filters.clicked.connect(self.reset_and_refresh)
        filter_layout.addWidget(self.btn_reset_filters)

        list_lay.addLayout(filter_layout)

        # Grid Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Employee ID", "Employee Code", "Name", "Department", "Designation", "Date of Joining", "Status", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.table_selection_changed)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(150)
        list_lay.addWidget(self.table)

        # Pagination Footer
        pagination_layout = QHBoxLayout()
        self.lbl_table_summary = QLabel("Showing 1 to X of Y entries")
        pagination_layout.addWidget(self.lbl_table_summary)
        
        pagination_layout.addStretch()
        
        self.btn_prev_page = QPushButton("<")
        self.btn_prev_page.setFixedWidth(30)
        self.btn_prev_page.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.btn_prev_page)

        self.lbl_page_num = QLabel("Page 1")
        self.lbl_page_num.setFont(QFont("Segoe UI", 10, QFont.Bold))
        pagination_layout.addWidget(self.lbl_page_num)

        self.btn_next_page = QPushButton(">")
        self.btn_next_page.setFixedWidth(30)
        self.btn_next_page.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.btn_next_page)

        list_lay.addLayout(pagination_layout)
        layout.addWidget(list_card)

        # Assemble Scroll Area
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        self.photo_path = None
        self.is_loading_details = False

    def load_filters(self):
        # Departments & Designations dropdown list population
        db = SessionLocal()
        try:
            self.cmb_dept.clear()
            self.cmb_desig.clear()
            self.cmb_filter_dept.clear()
            self.cmb_filter_dept.addItem("All Departments", None)
            
            for dept in db.query(Department).order_by(Department.name).all():
                self.cmb_dept.addItem(dept.name, dept.id)
                self.cmb_filter_dept.addItem(dept.name, dept.id)
                
            for desig in db.query(Designation).order_by(Designation.name).all():
                self.cmb_desig.addItem(desig.name, desig.id)
        finally:
            try:
                db.close()
            except Exception:
                pass

    def header_search_changed(self):
        # Header search updates the filter search field dynamically for a synced feel
        self.txt_filter_search.setText(self.txt_header_search.text())
        self.reset_and_refresh()

    def reset_and_refresh(self):
        self.current_page = 1
        self.refresh_employees()

    def refresh_data(self):
        self.load_filters()
        self.refresh_employees()

    def refresh_employees(self):
        self.is_loading_details = True
        db = SessionLocal()
        try:
            # 1. Update stats cards counts
            total_count = db.query(Employee).count()
            active_count = db.query(Employee).filter(Employee.status == "Active").count()
            inactive_count = db.query(Employee).filter(Employee.status == "Inactive").count()
            resigned_count = db.query(Employee).filter(Employee.status == "Resigned").count()
            
            self.lbl_stat_total.setText(str(total_count))
            self.lbl_stat_active.setText(str(active_count))
            self.lbl_stat_inactive.setText(str(inactive_count))
            self.lbl_stat_resigned.setText(str(resigned_count))
            
            den = max(1, total_count)
            self.lbl_stat_active_badge.setText(f"{active_count / den * 100:.2f}% Active")
            self.lbl_stat_inactive_badge.setText(f"{inactive_count / den * 100:.2f}% Inactive")
            self.lbl_stat_resigned_badge.setText(f"{resigned_count / den * 100:.2f}% Resigned")

            # 2. Build Query Filters
            q = db.query(Employee)
            
            search_txt = self.txt_filter_search.text().strip().lower()
            if search_txt:
                q = q.filter(
                    (Employee.name.like(f"%{search_txt}%")) |
                    (Employee.employee_code.like(f"%{search_txt}%")) |
                    (Employee.pan_number.like(f"%{search_txt}%")) |
                    (Employee.mobile.like(f"%{search_txt}%"))
                )

            dept_id = self.cmb_filter_dept.currentData()
            if dept_id:
                q = q.filter(Employee.department_id == dept_id)

            status_txt = self.cmb_filter_status.currentText()
            if status_txt != "All Statuses":
                q = q.filter(Employee.status == status_txt)

            total_entries = q.count()
            
            # 3. Apply Pagination Offset
            offset = (self.current_page - 1) * self.page_size
            employees = q.order_by(Employee.id.desc()).offset(offset).limit(self.page_size).all()

            # 4. Populate table
            self.table.blockSignals(True)
            self.table.setRowCount(len(employees))
            
            def make_item(text, align=Qt.AlignVCenter | Qt.AlignLeft):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(align)
                return item

            for row_idx, emp in enumerate(employees):
                # ID – center aligned
                id_item = make_item(f"EMP{emp.id:06d}", Qt.AlignVCenter | Qt.AlignHCenter)
                id_item.setData(Qt.UserRole, emp.id)
                self.table.setItem(row_idx, 0, id_item)

                # Code – center aligned
                self.table.setItem(row_idx, 1, make_item(emp.employee_code or "-", Qt.AlignVCenter | Qt.AlignHCenter))

                # Name – center aligned
                self.table.setItem(row_idx, 2, make_item(emp.name, Qt.AlignVCenter | Qt.AlignHCenter))

                # Dept / Designation – center aligned
                dept_name = emp.department.name if emp.department else "General"
                desig_name = emp.designation.name if emp.designation else "Staff"
                self.table.setItem(row_idx, 3, make_item(dept_name, Qt.AlignVCenter | Qt.AlignHCenter))
                self.table.setItem(row_idx, 4, make_item(desig_name, Qt.AlignVCenter | Qt.AlignHCenter))

                # Joining Date – center aligned
                j_date = emp.joining_date.strftime("%d/%m/%Y") if emp.joining_date else "-"
                self.table.setItem(row_idx, 5, make_item(j_date, Qt.AlignVCenter | Qt.AlignHCenter))

                # Status badge – center aligned with color
                status_item = make_item(emp.status or "Active", Qt.AlignVCenter | Qt.AlignHCenter)
                if emp.status == "Active":
                    status_item.setForeground(Qt.green)
                elif emp.status == "Inactive":
                    status_item.setForeground(Qt.yellow)
                else:
                    status_item.setForeground(Qt.red)
                self.table.setItem(row_idx, 6, status_item)

                # Action — Clickable Edit Button
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setAlignment(Qt.AlignCenter)
                
                edit_btn = QPushButton("👁️ Select / Edit")
                edit_btn.setProperty("class", "SecondaryBtn")
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setStyleSheet("""
                    QPushButton {
                        padding: 4px 8px;
                        font-size: 11px;
                        font-weight: bold;
                        border-radius: 4px;
                    }
                """)
                edit_btn.clicked.connect(lambda checked=False, id=emp.id: self.open_edit_dialog(id))
                btn_layout.addWidget(edit_btn)
                self.table.setCellWidget(row_idx, 7, btn_widget)

            self.table.blockSignals(False)

            # Update pagination labels
            start_num = offset + 1 if total_entries > 0 else 0
            end_num = min(offset + self.page_size, total_entries)
            self.lbl_table_summary.setText(f"Showing {start_num} to {end_num} of {total_entries} entries")
            self.lbl_page_num.setText(f"Page {self.current_page}")

            # Re-select the currently active employee row, or fall back to first
            if len(employees) > 0:
                target_id = self.selected_employee_id
                selected_row = 0  # default fallback
                for i, emp in enumerate(employees):
                    if emp.id == target_id:
                        selected_row = i
                        break
                self.table.setCurrentCell(selected_row, 0)
                if self.selected_employee_id is None:
                    self.load_employee_details(employees[selected_row].id)
                
        finally:
            try:
                db.close()
            except Exception:
                pass
            self.is_loading_details = False

    def table_selection_changed(self):
        if self.is_loading_details:
            return
        row = self.table.currentRow()
        if row >= 0:
            id_item = self.table.item(row, 0)
            if id_item:
                emp_id = id_item.data(Qt.UserRole)
                self.load_employee_details(emp_id)

    def load_employee_details(self, emp_id):
        self.selected_employee_id = emp_id
        self.new_mode = False
        
        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            if not emp:
                return

            # Set text inputs
            self.txt_emp_id.setText(f"EMP{emp.id:06d}")
            self.txt_emp_code.setText(emp.employee_code or "")
            
            # Split names
            names = (emp.name or "").split()
            first = names[0] if len(names) > 0 else ""
            middle = names[1] if len(names) > 2 else ""
            last = names[-1] if len(names) > 1 else ""
            
            self.txt_first_name.setText(first)
            self.txt_middle_name.setText(middle)
            self.txt_last_name.setText(last)
            
            self.cmb_title.setCurrentText(emp.title or "Mr.")
            self.cmb_gender.setCurrentText(emp.gender or "Male")
            self.cmb_marital.setCurrentText(emp.marital_status or "Single")
            self.txt_father_name.setText(emp.father_name or "")
            self.txt_nationality.setText(emp.nationality or "Indian")
            self.cmb_religion.setCurrentText(emp.religion or "Hindu")
            self.txt_pan.setText(emp.pan_number or "")
            self.txt_aadhaar.setText(emp.aadhaar_number or "")
            self.cmb_blood.setCurrentText(emp.blood_group or "A+")

            # Dob
            if emp.dob:
                self.date_dob.setDate(QDate(emp.dob.year, emp.dob.month, emp.dob.day))

            # Photo Setup
            self.photo_path = emp.photo_path
            if self.photo_path and os.path.exists(self.photo_path):
                self.lbl_photo.setPixmap(QPixmap(self.photo_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.lbl_photo.clear()
                self.lbl_photo.setText("👤")

            # Status & Dates
            self.cmb_status.setCurrentText(emp.status or "Active")
            if emp.joining_date:
                self.date_joining.setDate(QDate(emp.joining_date.year, emp.joining_date.month, emp.joining_date.day))
            if emp.probation_end_date:
                self.date_probation.setDate(QDate(emp.probation_end_date.year, emp.probation_end_date.month, emp.probation_end_date.day))
            if emp.confirmation_date:
                self.date_confirmation.setDate(QDate(emp.confirmation_date.year, emp.confirmation_date.month, emp.confirmation_date.day))

            # Department / Designation
            dept_idx = self.cmb_dept.findData(emp.department_id)
            if dept_idx >= 0:
                self.cmb_dept.setCurrentIndex(dept_idx)
            desig_idx = self.cmb_desig.findData(emp.designation_id)
            if desig_idx >= 0:
                self.cmb_desig.setCurrentIndex(desig_idx)
                
            self.cmb_type.setCurrentText(emp.employment_type or "Permanent")
            self.txt_location.setText(emp.location or "Noida")
            self.txt_reporting_to.setText(emp.reporting_to or "")

            # Salary Info
            self.txt_monthly_salary.setText(str(int(round(emp.monthly_salary or 0.0))))
            self.txt_half_day_salary.setText(str(int(round(emp.half_day_salary or 0.0))))

            # Bank & Statutory Details
            self.txt_bank_name.setText(emp.bank_name or "")
            self.txt_account.setText(emp.account_number or "")
            self.txt_ifsc.setText(emp.ifsc or "")
            self.txt_pf.setText(emp.pf_number or "")
            self.txt_esic.setText(emp.esic_number or "")
            self.txt_uan.setText(emp.uan or "")

            # Contact details
            self.txt_email.setText(emp.email or "")
            self.txt_mobile.setText(emp.mobile or "")
            self.txt_address.setText(emp.address or "")
            self.txt_emergency.setText(emp.emergency_contact or "")

            # Update Employee Summary (Right Card)
            dept_name = emp.department.name if emp.department else "General"
            desig_name = emp.designation.name if emp.designation else "Staff"
            self.lbl_sum_dept.setText(dept_name)
            self.lbl_sum_desig.setText(desig_name)
            self.lbl_sum_type.setText(emp.employment_type or "Permanent")
            self.lbl_sum_loc.setText(emp.location or "Noida")
            self.lbl_sum_rep.setText(emp.reporting_to or "None")
            self.lbl_sum_email.setText(emp.email or "None")
            self.lbl_sum_mobile.setText(emp.mobile or "None")

            # Update Snapshot Cards
            self.lbl_snap_dept_val.setText(dept_name)
            self.lbl_snap_desig_val.setText(desig_name)
            self.lbl_snap_type_val.setText(emp.employment_type or "Permanent")
            self.lbl_snap_ctc_val.setText(f"₹ {(emp.monthly_salary or 0.0) * 12:,.2f}")
            self.lbl_snap_rep_val.setText(emp.reporting_to or "None")

            # Documents mockup check
            self.lbl_docs_list.setText(f"📁 Root Folder: {emp.employee_code or 'EMP'}_Docs\nFiles: None")

        finally:
            db.close()

    def open_edit_dialog(self, emp_id):
        self.load_employee_details(emp_id)
        dialog = EmployeeQuickEditDialog(self, emp_id)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_employees()

    def new_employee_mode(self):
        self.selected_employee_id = None
        self.new_mode = True
        
        # Clear fields
        self.txt_emp_id.setText("Auto Generated")
        self.txt_emp_code.setText("Auto Generated")
        
        self.txt_first_name.clear()
        self.txt_middle_name.clear()
        self.txt_last_name.clear()
        
        self.txt_father_name.clear()
        self.txt_pan.clear()
        self.txt_aadhaar.clear()
        
        self.txt_monthly_salary.setText("30000")
        self.txt_half_day_salary.setText("577")
        
        self.txt_bank_name.clear()
        self.txt_account.clear()
        self.txt_ifsc.clear()
        self.txt_pf.clear()
        self.txt_esic.clear()
        self.txt_uan.clear()
        
        self.txt_email.clear()
        self.txt_mobile.clear()
        self.txt_address.clear()
        self.txt_emergency.clear()
        
        self.lbl_photo.clear()
        self.lbl_photo.setText("👤")
        self.photo_path = None
        
        self.cmb_status.setCurrentText("Active")
        self.date_joining.setDate(QDate.currentDate())
        
        # Switch tab to first index
        self.tabs.setCurrentIndex(0)
        
        QMessageBox.information(self, "Add Employee", "Form ready. Fill details and click 'Save Employee Details' below.")

    def cancel_edit_mode(self):
        self.new_mode = False
        db = SessionLocal()
        try:
            if self.selected_employee_id:
                emp = db.query(Employee).filter(Employee.id == self.selected_employee_id).first()
                if emp:
                    self.load_employee_details(self.selected_employee_id)
                    QMessageBox.information(self, "Canceled", "Edits discarded. Original details restored.")
                    return
            
            first_emp = db.query(Employee).order_by(Employee.id.desc()).first()
            if first_emp:
                self.selected_employee_id = first_emp.id
                self.load_employee_details(first_emp.id)
                QMessageBox.information(self, "Canceled", "Edits discarded. Details reset.")
            else:
                self.new_employee_mode()
                QMessageBox.information(self, "Canceled", "Form inputs cleared.")
        finally:
            try:
                db.close()
            except Exception:
                pass

    def save_current_employee(self):
        first = self.txt_first_name.text().strip()
        middle = self.txt_middle_name.text().strip()
        last = self.txt_last_name.text().strip()
        
        if not first:
            QMessageBox.warning(self, "Validation Error", "First Name is required.")
            return

        full_name = f"{first} {middle} {last}".replace("  ", " ").strip()

        db = SessionLocal()
        try:
            from sqlalchemy import func

            # ── Determine if ADD or EDIT ──────────────────────────────────────
            if self.new_mode or self.selected_employee_id is None:
                max_id = db.query(func.max(Employee.id)).scalar() or 0
                code   = f"EDB{1001 + max_id}"
                emp    = Employee(employee_code=code, name=full_name)
                db.add(emp)
                action = "Employee Added"
            else:
                emp = db.query(Employee).filter(Employee.id == self.selected_employee_id).first()
                if not emp:
                    QMessageBox.critical(self, "Error", "Employee record not found.")
                    return
                code   = emp.employee_code
                action = "Employee Edited"

            # ── Set ALL fields before a single commit ─────────────────────────
            emp.name            = full_name
            emp.title           = self.cmb_title.currentText()
            emp.gender          = self.cmb_gender.currentText()
            emp.marital_status  = self.cmb_marital.currentText()
            emp.father_name     = self.txt_father_name.text().strip()
            emp.nationality     = self.txt_nationality.text().strip()
            emp.religion        = self.cmb_religion.currentText()
            emp.blood_group     = self.cmb_blood.currentText()

            # Dates
            dob_q  = self.date_dob.date()
            emp.dob = date(dob_q.year(), dob_q.month(), dob_q.day())

            j_q = self.date_joining.date()
            emp.joining_date = date(j_q.year(), j_q.month(), j_q.day())

            prob_q = self.date_probation.date()
            emp.probation_end_date = date(prob_q.year(), prob_q.month(), prob_q.day())

            conf_q = self.date_confirmation.date()
            emp.confirmation_date = date(conf_q.year(), conf_q.month(), conf_q.day())

            # Employment
            emp.department_id   = self.cmb_dept.currentData()
            emp.designation_id  = self.cmb_desig.currentData()
            emp.employment_type = self.cmb_type.currentText()
            emp.location        = self.txt_location.text().strip()
            emp.reporting_to    = self.txt_reporting_to.text().strip()
            emp.status          = self.cmb_status.currentText()

            # Salary
            emp.monthly_salary     = float(self.txt_monthly_salary.text() or 0)
            emp.half_day_salary    = float(self.txt_half_day_salary.text() or 0)
            emp.basic_salary       = emp.monthly_salary * 0.50
            emp.hra                = emp.monthly_salary * 0.20
            emp.special_allowance  = 0.0
            emp.other_allowance    = 0.0

            # Bank & Statutory
            emp.bank_name      = self.txt_bank_name.text().strip()
            emp.account_number = self.txt_account.text().strip()
            emp.ifsc           = self.txt_ifsc.text().strip()
            emp.pan_number     = self.txt_pan.text().strip()
            emp.aadhaar_number = self.txt_aadhaar.text().strip()
            emp.pf_number      = self.txt_pf.text().strip()
            emp.esic_number    = self.txt_esic.text().strip()
            emp.uan            = self.txt_uan.text().strip()

            # Contact
            emp.email             = self.txt_email.text().strip() or None
            emp.mobile            = self.txt_mobile.text().strip()
            emp.address           = self.txt_address.text().strip()
            emp.emergency_contact = self.txt_emergency.text().strip()
            emp.photo_path        = self.photo_path

            # ── Single commit ─────────────────────────────────────────────────
            db.commit()
            db.refresh(emp)

            new_emp_id = emp.id
            self.selected_employee_id = new_emp_id
            self.new_mode = False

            # Initialize leave balances for new employees
            if action == "Employee Added":
                LeaveService.initialize_employee_leaves(db, new_emp_id)

            AuditLogger.log(action, f"Saved details for employee {full_name} ({code})")
            QMessageBox.information(self, "Success", "Employee details saved successfully.")

            self.refresh_employees()
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, "Database Error", f"Failed to save employee: {e}")
            try:
                db.close()
            except Exception:
                pass

    def save_as_new_employee(self):
        self.new_mode = True
        self.selected_employee_id = None
        self.save_current_employee()

    def upload_photo(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Upload Photo", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not filepath:
            return

        try:
            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)

            ext = os.path.splitext(filepath)[1]
            dest_filename = f"photo_{self.selected_employee_id or 'new'}_{int(datetime.now().timestamp())}{ext}"
            dest_path = os.path.join(UPLOAD_DIR, dest_filename)

            shutil.copy(filepath, dest_path)
            self.photo_path = dest_path
            
            self.lbl_photo.setPixmap(QPixmap(dest_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            QMessageBox.information(self, "Success", "Photo uploaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Upload Failed", f"Failed to upload photo: {e}")

    def import_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Spreadsheet", "", "Excel Files (*.xlsx *.xls *.csv)"
        )
        if not filepath:
            return
        
        try:
            if filepath.endswith(".csv"):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
                
            required = ["Name", "Department", "Designation", "MonthlySalary"]
            for col in required:
                if col not in df.columns:
                    QMessageBox.critical(self, "Import Error", f"Missing required column: {col}")
                    return
            
            db = SessionLocal()
            imported = 0
            try:
                for _, row in df.iterrows():
                    name = str(row["Name"]).strip()
                    dept_name = str(row["Department"]).strip()
                    desig_name = str(row["Designation"]).strip()
                    salary = float(row["MonthlySalary"])
                    
                    # Lookup dept/desig
                    dept = db.query(Department).filter(Department.name == dept_name).first()
                    if not dept:
                        dept = Department(name=dept_name)
                        db.add(dept)
                        db.commit()
                        db.refresh(dept)
                        
                    desig = db.query(Designation).filter(Designation.name == desig_name).first()
                    if not desig:
                        desig = Designation(name=desig_name)
                        db.add(desig)
                        db.commit()
                        db.refresh(desig)
                        
                    count = db.query(Employee).count()
                    code = f"EDB{1001 + count}"
                    
                    emp = Employee(
                        employee_code=code,
                        name=name,
                        department_id=dept.id,
                        designation_id=desig.id,
                        monthly_salary=salary,
                        half_day_salary=salary/26.0/2.0,
                        employment_type="Permanent",
                        status="Active",
                        joining_date=datetime.now().date()
                    )
                    db.add(emp)
                    db.commit()
                    
                    LeaveService.initialize_employee_leaves(db, emp.id)
                    imported += 1
                
                db.commit()
                QMessageBox.information(self, "Import Complete", f"Successfully imported {imported} employee profiles!")
                self.refresh_employees()
            finally:
                db.close()
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to parse and import file: {e}")

    def export_excel(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Employees", "Employees_Export.xlsx", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return
            
        db = SessionLocal()
        try:
            employees = db.query(Employee).all()
            data = []
            for emp in employees:
                dept = emp.department.name if emp.department else "General"
                desig = emp.designation.name if emp.designation else "Staff"
                data.append({
                    "EmployeeID": f"EMP{emp.id:06d}",
                    "EmployeeCode": emp.employee_code,
                    "Name": emp.name,
                    "Department": dept,
                    "Designation": desig,
                    "EmploymentType": emp.employment_type,
                    "Status": emp.status,
                    "MonthlySalary": emp.monthly_salary,
                    "DateOfJoining": emp.joining_date
                })
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False)
            QMessageBox.information(self, "Export Success", f"Successfully exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export: {e}")
        finally:
            db.close()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_employees()

    def next_page(self):
        self.current_page += 1
        self.refresh_employees()

    def autofetch_document(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Select Document Type")
        msg_box.setText("Which document would you like to upload and scan?")
        
        btn_aadhaar = msg_box.addButton("Aadhaar Card", QMessageBox.YesRole)
        btn_pan = msg_box.addButton("PAN Card", QMessageBox.NoRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        # Apply current theme style to popup
        msg_box.setStyleSheet(self.styleSheet())
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_cancel:
            return
            
        selected_type = "Aadhaar" if msg_box.clickedButton() == btn_aadhaar else "PAN"

        filepath, _ = QFileDialog.getOpenFileName(
            self, f"Select {selected_type} Card File", "", "Documents (*.pdf *.png *.jpg *.jpeg *.txt)"
        )
        if not filepath:
            return

        # Show scanner dialog
        scan_dlg = ScanProgressDialog(self)
        scan_dlg.exec()

        # Extract details forcing the selected type
        data = extract_details_from_file(filepath, force_type=selected_type)

        # Show results confirmation
        result_dlg = ScanResultDialog(self, data)
        if result_dlg.exec() == QDialog.Accepted:
            v_data = result_dlg.get_verified_data()
            
            # Import details into fields!
            names = v_data["name"].split()
            first = names[0] if len(names) > 0 else ""
            middle = names[1] if len(names) > 2 else ""
            last = names[-1] if len(names) > 1 else ""
            
            self.txt_first_name.setText(first)
            self.txt_middle_name.setText(middle)
            self.txt_last_name.setText(last)
            
            self.cmb_gender.setCurrentText(v_data["gender"])
            
            # Parse Date
            from PySide6.QtCore import QDate
            date_str = v_data["dob"].replace("/", "-").replace(" ", "-")
            parsed_date = None
            for fmt in ["dd-MM-yyyy", "yyyy-MM-dd"]:
                qd = QDate.fromString(date_str, fmt)
                if qd.isValid():
                    parsed_date = qd
                    break
            if parsed_date:
                self.date_dob.setDate(parsed_date)

            if v_data["type"] == "Aadhaar":
                self.txt_aadhaar.setText(v_data["doc_num"])
            else:
                self.txt_pan.setText(v_data["doc_num"])
                
            QMessageBox.information(self, "Success", "Details successfully imported to form fields!")

class ScanProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Document Scanner")
        self.setFixedSize(320, 150)
        
        layout = QVBoxLayout(self)
        self.lbl_status = QLabel("Checking document...")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        layout.addWidget(self.pbar)
        
        self.step = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(400) # update progress every 400ms

    def update_progress(self):
        self.step += 25
        self.pbar.setValue(self.step)
        
        if self.step == 25:
            self.lbl_status.setText("Extracting OCR text runs...")
        elif self.step == 50:
            self.lbl_status.setText("Running pattern extraction heuristics...")
        elif self.step == 75:
            self.lbl_status.setText("Parsing personal identity keys...")
        elif self.step >= 100:
            self.timer.stop()
            self.accept()

class ScanResultDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Review Extracted Details")
        self.setFixedSize(380, 320)
        self.data = data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.lbl_type = QLabel(f"<b>{self.data['type']} Card</b>")
        self.txt_name = QLineEdit(self.data["name"])
        self.txt_dob = QLineEdit(self.data["dob"])
        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["Male", "Female", "Other"])
        self.cmb_gender.setCurrentText(self.data["gender"])
        
        self.txt_doc_num = QLineEdit()
        if self.data["type"] == "Aadhaar":
            self.txt_doc_num.setText(self.data["aadhaar"])
            form.addRow("Aadhaar Number:", self.txt_doc_num)
        else:
            self.txt_doc_num.setText(self.data["pan"])
            form.addRow("PAN Number:", self.txt_doc_num)

        form.addRow("Document Type:", self.lbl_type)
        form.addRow("Full Name:", self.txt_name)
        form.addRow("Date of Birth:", self.txt_dob)
        form.addRow("Gender:", self.cmb_gender)
        
        layout.addLayout(form)
        
        info_lbl = QLabel("<i>Please verify the fields before importing.</i>")
        info_lbl.setStyleSheet("color: #71717a;")
        layout.addWidget(info_lbl)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_verified_data(self):
        return {
            "type": self.data["type"],
            "name": self.txt_name.text().strip(),
            "dob": self.txt_dob.text().strip(),
            "gender": self.cmb_gender.currentText(),
            "doc_num": self.txt_doc_num.text().strip()
        }

def run_win_ocr(image_path):
    import asyncio
    try:
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.media.ocr import OcrEngine
        from winsdk.windows.storage import StorageFile
        
        async def _ocr():
            file = await StorageFile.get_file_from_path_async(os.path.abspath(image_path))
            stream = await file.open_async(0)
            decoder = await BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()
            engine = OcrEngine.try_create_from_user_profile_languages()
            if not engine:
                return ""
            result = await engine.recognize_async(software_bitmap)
            lines = [line.text for line in result.lines]
            return "\n".join(lines)
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(_ocr())
        loop.close()
        return res
    except Exception as e:
        print(f"Windows OCR failed: {e}")
        return ""

def extract_details_from_file(filepath, force_type=None):
    filename = os.path.basename(filepath).lower()
    content = ""
    
    # Try reading text
    if filepath.lower().endswith(".txt"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            pass
    elif filepath.lower().endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(filepath)
            text_runs = []
            for page in reader.pages:
                text_runs.append(page.extract_text() or "")
            content = "\n".join(text_runs)
        except Exception:
            pass
    elif filepath.lower().endswith((".png", ".jpg", ".jpeg")):
        content = run_win_ocr(filepath)

    # Heuristics
    detected_type = force_type if force_type else "PAN"
    if not force_type:
        if "aadhaar" in content.lower() or "aadhar" in content.lower() or "government of india" in content.lower() or "unique identification" in content.lower() or "enrolment" in content.lower() or "male" in content.lower() or "female" in content.lower():
            detected_type = "Aadhaar"
        elif "permanent account number" in content.lower() or "income tax" in content.lower() or "tax department" in content.lower():
            detected_type = "PAN"
        elif "aadhaar" in filename or "aadhar" in filename:
            detected_type = "Aadhaar"
        elif "pan" in filename:
            detected_type = "PAN"

    # Regex search
    aadhaar_match = re.search(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b', content)
    pan_match = re.search(r'\b[a-zA-Z]{5}\d{4}[a-zA-Z]\b', content)
    dob_match = re.search(r'\b\d{2}[-/\s]\d{2}[-/\s]\d{4}\b', content)
    
    # Fallback to filename search if content is empty
    if not aadhaar_match:
        aadhaar_match = re.search(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b', filename)
    if not pan_match:
        pan_match = re.search(r'\b[a-zA-Z]{5}\d{4}[a-zA-Z]\b', filename)
    if not dob_match:
        dob_match = re.search(r'\b\d{2}[-/\s]\d{2}[-/\s]\d{4}\b', filename)

    # Name heuristics from OCR content
    name_match = ""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    exclude_words = {"government", "india", "male", "female", "father", "husband", "address", "income", "tax", "department", "card", "permanent", "account", "number", "unique", "identification", "authority", "yob", "dob", "birth", "year"}
    
    for line in lines:
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isupper() and w.isalpha() for w in words):
            if not any(w.lower() in exclude_words for w in words):
                name_match = line.title()
                break

    # Fallback to filename search if name not found in OCR content
    if not name_match:
        clean_name = filename.replace("pan", "").replace("aadhaar", "").replace("aadhar", "").replace("card", "").replace("_", " ").replace("-", " ").strip()
        clean_name = re.sub(r'\.\w+$', '', clean_name)
        clean_name = re.sub(r'\d+', '', clean_name).strip()
        if clean_name:
            name_match = clean_name.title()
        else:
            name_match = "New Employee"

    aadhaar_val = aadhaar_match.group(0) if aadhaar_match else ""
    pan_val = pan_match.group(0).upper() if pan_match else ""
    dob_val = dob_match.group(0) if dob_match else ""

    # Defaults if not found
    if detected_type == "Aadhaar" and not aadhaar_val:
        aadhaar_val = "5432 9876 1204"
    if detected_type == "PAN" and not pan_val:
        pan_val = "ABCDE1234F"
    if not dob_val:
        dob_val = "12-10-1995"

    gender_val = "Male"
    if "female" in content.lower() or "female" in filename or "she" in filename or "her" in filename:
        gender_val = "Female"

    return {
        "type": detected_type,
        "name": name_match,
        "aadhaar": aadhaar_val,
        "pan": pan_val,
        "dob": dob_val,
        "gender": gender_val
    }


class EmployeeQuickEditDialog(QDialog):
    def __init__(self, parent, emp_id):
        super().__init__(parent)
        self.emp_id = emp_id
        self.setWindowTitle("Quick Edit Employee Details & Salary")
        self.setFixedWidth(420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.emp_id).first()
            self.txt_name = QLineEdit(emp.name)
            
            self.cmb_dept = QComboBox()
            for d in db.query(Department).all():
                self.cmb_dept.addItem(d.name, d.id)
            if emp.department_id:
                self.cmb_dept.setCurrentIndex(self.cmb_dept.findData(emp.department_id))

            self.cmb_desig = QComboBox()
            for ds in db.query(Designation).all():
                self.cmb_desig.addItem(ds.name, ds.id)
            if emp.designation_id:
                self.cmb_desig.setCurrentIndex(self.cmb_desig.findData(emp.designation_id))

            self.txt_salary = QLineEdit(str(int(round(emp.monthly_salary or 0.0))))
            self.txt_half_day = QLineEdit(str(int(round(emp.half_day_salary or 0.0))))
            
            self.txt_email = QLineEdit(emp.email or "")
            self.txt_mobile = QLineEdit(emp.mobile or "")
            self.txt_address = QLineEdit(emp.address or "")
            
            form.addRow("Full Name *:", self.txt_name)
            form.addRow("Department *:", self.cmb_dept)
            form.addRow("Designation *:", self.cmb_desig)
            form.addRow("Monthly Salary (CTC) *:", self.txt_salary)
            form.addRow("Half Day Salary:", self.txt_half_day)
            form.addRow("Email:", self.txt_email)
            form.addRow("Mobile:", self.txt_mobile)
            form.addRow("Address:", self.txt_address)
        finally:
            db.close()

        layout.addLayout(form)

        info_lbl = QLabel("<i>* Required fields. All details and salary are editable here.</i>")
        info_lbl.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(info_lbl)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.save_data)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def save_data(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Full Name is required.")
            return

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.emp_id).first()
            if emp:
                emp.name = name
                emp.department_id = self.cmb_dept.currentData()
                emp.designation_id = self.cmb_desig.currentData()
                emp.monthly_salary = float(self.txt_salary.text().strip() or 0.0)
                emp.half_day_salary = float(self.txt_half_day.text().strip() or 0.0)
                emp.email = self.txt_email.text().strip() or None
                emp.mobile = self.txt_mobile.text().strip()
                emp.address = self.txt_address.text().strip()
                
                # Auto-calculate breakdown components in the background
                emp.basic_salary = emp.monthly_salary * 0.50
                emp.hra = emp.monthly_salary * 0.20
                emp.special_allowance = 0.0
                emp.other_allowance = 0.0
                
                db.commit()
                QMessageBox.information(self, "Success", "Employee details and salary updated successfully!")
                self.accept()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save details: {e}")
        finally:
            db.close()
