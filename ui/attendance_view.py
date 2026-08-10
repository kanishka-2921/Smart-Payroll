from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QFormLayout, QSpinBox, QDateEdit, QFileDialog, QCheckBox,
                             QDialog, QDialogButtonBox, QProgressBar, QMenu, QGridLayout)
from PySide6.QtCore import Qt, QDate, QPoint, Signal
from PySide6.QtGui import QFont, QShortcut, QKeySequence
from database.connection import SessionLocal
from database.models import Employee, Attendance, HolidayCalendar, Department, Designation
from services.leave_service import LeaveService
from utilities.audit_logger import AuditLogger
from datetime import datetime, date
import calendar
import pandas as pd

class ClickableFrame(QFrame):
    clicked = Signal()
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class AttendanceView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.load_employees_list()
        self.update_category_cards_theme()

    def create_category_button(self, icon_text, title_text, desc_text):
        btn = QPushButton()
        btn.setFixedHeight(85)
        btn.setCursor(Qt.PointingHandCursor)
        
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(6, 8, 6, 8)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignCenter)
        
        # White circle for icon
        circle = QLabel(icon_text)
        circle.setFixedSize(28, 28)
        circle.setAlignment(Qt.AlignCenter)
        circle.setFont(QFont("Segoe UI", 12))
        circle.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(circle, 0, Qt.AlignCenter)
        
        # Text label
        lbl = QLabel(f"{title_text}\n{desc_text}")
        lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(lbl, 0, Qt.AlignCenter)
        
        return btn

    def init_ui(self):
        from PySide6.QtWidgets import QScrollArea
        
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
        layout.setSpacing(12)

        # ── 1. HEADER LAYOUT ──────────────────────────────────────────────────
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Round Icon + Title V-Layout
        icon_lbl = QLabel("👥")
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background-color: #4338ca; color: white; border-radius: 10px; font-size: 22px;")
        header_layout.addWidget(icon_lbl)

        title_v_layout = QVBoxLayout()
        title_v_layout.setSpacing(2)
        title_lbl = QLabel("Mark Employee Attendance")
        title_lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_lbl.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")

        subtitle_lbl = QLabel("Quick • Easy • Accurate")
        subtitle_lbl.setFont(QFont("Segoe UI", 10))
        subtitle_lbl.setStyleSheet("color: #64748b;" if self.theme == "light" else "color: #94a3b8;")
        title_v_layout.addWidget(title_lbl)
        title_v_layout.addWidget(subtitle_lbl)
        header_layout.addLayout(title_v_layout)

        # Right Month/Year selector dropdowns
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Month"))
        self.cmb_month = QComboBox()
        self.cmb_month.setFixedWidth(130)
        self.cmb_month.setFixedHeight(34)
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        for m_idx, m_name in enumerate(months):
            self.cmb_month.addItem(f"📅  {m_name}", m_idx + 1)
        header_layout.addWidget(self.cmb_month)
        
        header_layout.addWidget(QLabel("Year"))
        self.cmb_year = QComboBox()
        self.cmb_year.setFixedWidth(100)
        self.cmb_year.setFixedHeight(34)
        current_year = datetime.now().year
        for yr in range(current_year - 2, current_year + 3):
            self.cmb_year.addItem(f"📅  {yr}", yr)
        header_layout.addWidget(self.cmb_year)

        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)
        
        # Set default selection
        cur_m = datetime.now().month
        cur_y = datetime.now().year
        self.cmb_month.setCurrentIndex(cur_m - 1)
        self.cmb_year.setCurrentText(f"📅  {cur_y}")
        
        self.cmb_month.currentIndexChanged.connect(self.sync_month_year_dropdowns_to_date)
        self.cmb_year.currentIndexChanged.connect(self.sync_month_year_dropdowns_to_date)
        layout.addWidget(header_widget)

        # ── 2. ROW 2: PROFILE CARD, SEARCH BAR, NAV & QUICK ADD ─────────────
        nav_widget = QWidget()
        nav_outer_layout = QVBoxLayout(nav_widget)
        nav_outer_layout.setContentsMargins(0, 0, 0, 0)
        nav_outer_layout.setSpacing(4)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(10)

        # Left Clickable Profile Card
        self.btn_profile_card = ClickableFrame(self)
        self.btn_profile_card.setObjectName("ProfileCard")
        self.btn_profile_card.setCursor(Qt.PointingHandCursor)
        self.btn_profile_card.setStyleSheet("""
            QFrame#ProfileCard {
                background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px;
            }
            QFrame#ProfileCard:hover { border-color: #6366f1; }
            QLabel { border: none; background: transparent; }
        """ if self.theme == "light" else """
            QFrame#ProfileCard {
                background-color: #1a1a20; border: 1px solid #2d2d35; border-radius: 8px;
            }
            QFrame#ProfileCard:hover { border-color: #6366f1; }
            QLabel { border: none; background: transparent; }
        """)
        self.btn_profile_card.clicked.connect(self.show_employee_dropdown)
        
        profile_layout = QHBoxLayout(self.btn_profile_card)
        profile_layout.setContentsMargins(10, 6, 10, 6)
        profile_layout.setSpacing(10)
        
        self.lbl_avatar = QLabel("RK")
        self.lbl_avatar.setFixedSize(36, 36)
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        self.lbl_avatar.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_avatar.setStyleSheet("background-color: #6366f1; color: white; border-radius: 18px;")
        profile_layout.addWidget(self.lbl_avatar)
        
        self.lbl_profile_details = QLabel("<b>Select Employee</b><br/>None selected<br/>None")
        self.lbl_profile_details.setFont(QFont("Segoe UI", 9))
        self.lbl_profile_details.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")
        profile_layout.addWidget(self.lbl_profile_details)
        
        chevron_lbl = QLabel("▼")
        chevron_lbl.setStyleSheet("color: #64748b;")
        profile_layout.addWidget(chevron_lbl)

        # Left Select Employee Column (Vertical layout to include Select Employee label)
        emp_col = QVBoxLayout()
        emp_col.setSpacing(4)
        emp_col.setContentsMargins(0, 0, 0, 0)
        emp_lbl = QLabel("Select Employee")
        emp_lbl.setFont(QFont("Segoe UI", 9))
        emp_lbl.setStyleSheet("color: #64748b;" if self.theme == "light" else "color: #94a3b8;")
        emp_col.addWidget(emp_lbl)
        emp_col.addWidget(self.btn_profile_card)
        nav_layout.addLayout(emp_col, 3)

        # Center Search Box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Search employee by name or ID...")
        self.txt_search.setMinimumWidth(220)
        self.txt_search.setFixedHeight(50) # Matching profile card height
        
        search_col = QVBoxLayout()
        search_col.setSpacing(4)
        search_col.setContentsMargins(0, 0, 0, 0)
        search_lbl = QLabel("") # Spacing match
        search_col.addWidget(search_lbl)
        search_col.addWidget(self.txt_search)
        nav_layout.addLayout(search_col, 3)

        # Prev/Next Navigation Buttons
        self.btn_prev_emp = QPushButton("◀")
        self.btn_prev_emp.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_prev_emp.setFixedSize(40, 50) # Height match
        self.btn_prev_emp.setProperty("class", "SecondaryBtn")
        self.btn_prev_emp.setStyleSheet("padding: 0px;")
        self.btn_prev_emp.clicked.connect(self.prev_employee)

        self.btn_next_emp = QPushButton("▶")
        self.btn_next_emp.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_next_emp.setFixedSize(40, 50) # Height match
        self.btn_next_emp.setProperty("class", "SecondaryBtn")
        self.btn_next_emp.setStyleSheet("padding: 0px;")
        self.btn_next_emp.clicked.connect(self.next_employee)

        nav_btns_layout = QHBoxLayout()
        nav_btns_layout.setSpacing(6)
        nav_btns_layout.addWidget(self.btn_prev_emp)
        nav_btns_layout.addWidget(self.btn_next_emp)

        nav_col = QVBoxLayout()
        nav_col.setSpacing(4)
        nav_col.setContentsMargins(0, 0, 0, 0)
        nav_lbl = QLabel("") # Spacing match
        nav_col.addWidget(nav_lbl)
        nav_col.addLayout(nav_btns_layout)
        nav_layout.addLayout(nav_col)

        # Quick Add Button
        self.btn_quick_add = QPushButton("👤+  Quick Add Employee")
        self.btn_quick_add.setProperty("class", "SecondaryBtn")
        self.btn_quick_add.setFixedHeight(50) # Height match
        self.btn_quick_add.setStyleSheet("""
            QPushButton {
                background: transparent; color: #a5b4fc; border: 1.5px solid #6366f1; border-radius: 8px;
                font-weight: bold; font-size: 12px; padding: 0 16px;
            }
            QPushButton:hover { background: #6366f1; color: white; }
        """)
        self.btn_quick_add.clicked.connect(self.quick_add_employee)

        add_col = QVBoxLayout()
        add_col.setSpacing(4)
        add_col.setContentsMargins(0, 0, 0, 0)
        add_lbl = QLabel("") # Spacing match
        add_col.addWidget(add_lbl)
        add_col.addWidget(self.btn_quick_add)
        nav_layout.addLayout(add_col, 2)

        nav_outer_layout.addLayout(nav_layout)

        # Department / Designation info row
        self.lbl_emp_info = QLabel("Department: —  |  Designation: —")
        self.lbl_emp_info.setFont(QFont("Segoe UI", 9))
        self.lbl_emp_info.setStyleSheet("color: #64748b;" if self.theme == "light" else "color: #64748b;")
        nav_outer_layout.addWidget(self.lbl_emp_info)

        layout.addWidget(nav_widget)

        # Hidden employee combo box for state persistence
        self.cmb_employee = QComboBox()
        self.cmb_employee.currentIndexChanged.connect(self.load_attendance)
        self.cmb_employee.hide()
        layout.addWidget(self.cmb_employee)

        # ── 3. ROW 3: SUMMARY STATS CARDS ─────────────────────────────────────
        stats_frame = QWidget()
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(10)

        # Card 1: Working Days (Auto)
        self.card_working = QFrame()
        self.card_working.setProperty("class", "DashboardCard")
        cw_layout = QVBoxLayout(self.card_working)
        cw_layout.setContentsMargins(12, 10, 12, 10)
        
        cw_header = QHBoxLayout()
        cw_icon = QLabel("📅")
        cw_icon.setFont(QFont("Segoe UI", 15))
        cw_icon.setStyleSheet("color: #3b82f6;")
        cw_title = QLabel("Working Days (Auto)")
        cw_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        cw_title.setStyleSheet("color: #94a3b8;")
        cw_header.addWidget(cw_icon)
        cw_header.addWidget(cw_title)
        cw_header.addStretch()
        
        cw_badge = QLabel("Auto")
        cw_badge.setStyleSheet("background-color: #2563eb; color: #ffffff; border-radius: 4px; padding: 1px 6px; font-weight: bold; font-size: 9px;")
        cw_header.addWidget(cw_badge)
        cw_layout.addLayout(cw_header)
        
        self.lbl_working_days_stat = QLabel("25")
        self.lbl_working_days_stat.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.lbl_working_days_stat.setStyleSheet("color: #ffffff;")
        cw_layout.addWidget(self.lbl_working_days_stat)
        stats_layout.addWidget(self.card_working, 0, 0)

        # Card 2: Month Days
        self.card_month_days = QFrame()
        self.card_month_days.setProperty("class", "DashboardCard")
        cmd_layout = QVBoxLayout(self.card_month_days)
        cmd_layout.setContentsMargins(12, 10, 12, 10)
        
        cmd_header = QHBoxLayout()
        cmd_icon = QLabel("📅")
        cmd_icon.setFont(QFont("Segoe UI", 15))
        cmd_icon.setStyleSheet("color: #10b981;")
        cmd_title = QLabel("Month Days")
        cmd_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        cmd_title.setStyleSheet("color: #94a3b8;")
        cmd_header.addWidget(cmd_icon)
        cmd_header.addWidget(cmd_title)
        cmd_header.addStretch()
        cmd_layout.addLayout(cmd_header)
        
        self.lbl_month_days_stat = QLabel("31")
        self.lbl_month_days_stat.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.lbl_month_days_stat.setStyleSheet("color: #ffffff;")
        cmd_layout.addWidget(self.lbl_month_days_stat)
        stats_layout.addWidget(self.card_month_days, 0, 1)

        # Card 3: Holidays
        self.card_holidays = QFrame()
        self.card_holidays.setProperty("class", "DashboardCard")
        ch_layout = QVBoxLayout(self.card_holidays)
        ch_layout.setContentsMargins(12, 10, 12, 10)
        
        ch_header = QHBoxLayout()
        ch_icon = QLabel("🏖️")
        ch_icon.setFont(QFont("Segoe UI", 15))
        ch_icon.setStyleSheet("color: #f59e0b;")
        ch_title = QLabel("Holidays")
        ch_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        ch_title.setStyleSheet("color: #94a3b8;")
        ch_header.addWidget(ch_icon)
        ch_header.addWidget(ch_title)
        ch_header.addStretch()
        ch_layout.addLayout(ch_header)
        
        self.lbl_holidays_stat = QLabel("2")
        self.lbl_holidays_stat.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.lbl_holidays_stat.setStyleSheet("color: #ffffff;")
        ch_layout.addWidget(self.lbl_holidays_stat)
        stats_layout.addWidget(self.card_holidays, 0, 2)

        # Card 4: Weekly Off Days selector card
        self.card_weekly_off = QFrame()
        self.card_weekly_off.setProperty("class", "DashboardCard")
        cwo_layout = QVBoxLayout(self.card_weekly_off)
        cwo_layout.setContentsMargins(12, 10, 12, 10)
        
        cwo_header = QHBoxLayout()
        cwo_icon = QLabel("📅")
        cwo_icon.setFont(QFont("Segoe UI", 15))
        cwo_icon.setStyleSheet("color: #8b5cf6;")
        
        # Weekly off dropdown
        self.cmb_weekly_off_day = QComboBox()
        self.cmb_weekly_off_day.addItems(["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"])
        self.cmb_weekly_off_day.setMinimumWidth(65)
        self.cmb_weekly_off_day.setStyleSheet("""
            QComboBox {
                font-size: 10px;
                font-weight: bold;
                padding: 1px 2px 1px 4px;
                border: 1px solid #4b5563;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                width: 12px;
                border: none;
            }
        """)
        self.cmb_weekly_off_day.currentIndexChanged.connect(self.recalculate_working_days)
        
        cwo_header.addWidget(cwo_icon)
        cwo_header.addWidget(QLabel("Weekly Off"))
        cwo_header.addWidget(self.cmb_weekly_off_day)
        cwo_header.addStretch()
        cwo_layout.addLayout(cwo_header)
        
        self.lbl_weekly_off_stat = QLabel("4")
        self.lbl_weekly_off_stat.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.lbl_weekly_off_stat.setStyleSheet("color: #ffffff;")
        cwo_layout.addWidget(self.lbl_weekly_off_stat)
        stats_layout.addWidget(self.card_weekly_off, 1, 0)

        # Card 5: Attendance Date Date Picker
        self.card_date = QFrame()
        self.card_date.setProperty("class", "DashboardCard")
        cd_layout = QVBoxLayout(self.card_date)
        cd_layout.setContentsMargins(12, 10, 12, 10)
        
        cd_header = QHBoxLayout()
        cd_icon = QLabel("📅")
        cd_icon.setFont(QFont("Segoe UI", 15))
        cd_icon.setStyleSheet("color: #14b8a6;")
        cd_title = QLabel("Attendance Date")
        cd_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        cd_title.setStyleSheet("color: #94a3b8;")
        cd_header.addWidget(cd_icon)
        cd_header.addWidget(cd_title)
        cd_header.addStretch()
        cd_layout.addLayout(cd_header)
        
        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setStyleSheet("""
            QDateEdit {
                background: transparent; border: none; font-size: 16px; font-weight: bold;
                color: #ffffff; padding: 0px;
            }
            QDateEdit::drop-down { border: none; }
        """)
        self.date_selector.dateChanged.connect(self.sync_date_picker_to_dropdown)
        cd_layout.addWidget(self.date_selector)
        stats_layout.addWidget(self.card_date, 1, 1, 1, 2)

        layout.addWidget(stats_frame)

        # ── 4. INFO BANNER ────────────────────────────────────────────────────
        info_banner = QFrame()
        info_banner.setStyleSheet("""
            QFrame { background: #1e3b8a; border: 1px solid #2563eb; border-radius: 6px; }
            QLabel { background: transparent; border: none; color: #93c5fd; font-size: 11px; }
        """)
        info_banner_layout = QHBoxLayout(info_banner)
        info_banner_layout.setContentsMargins(12, 6, 12, 6)
        
        lbl_info = QLabel("ℹ️   Working Days are calculated automatically based on selected month, weekly off and holidays.")
        info_banner_layout.addWidget(lbl_info)
        layout.addWidget(info_banner)

        # ── 5. FORM & SUMMARY SPLIT LAYOUT ─────────────────────────────────────
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(12)

        # LEFT COLUMN - Mark Attendance Card
        left_card = QFrame()
        left_card.setProperty("class", "DashboardCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 12, 16, 12)
        left_layout.setSpacing(10)
        
        left_title = QLabel("Mark Attendance")
        left_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        left_layout.addWidget(left_title)

        # Category Buttons Row (7 Buttons in a Grid)
        cat_widget = QWidget()
        cat_layout = QGridLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(6)
        
        self.btn_card_present     = self.create_category_button("✔️", "Present Day", "(Full Day)")
        self.btn_card_half        = self.create_category_button("🌓", "Half Day", "(0.5 Day)")
        self.btn_card_paid        = self.create_category_button("💼", "Paid Leave", "(PL)")
        self.btn_card_unpaid      = self.create_category_button("📄", "Unpaid Leave", "(UL)")
        self.btn_card_absent      = self.create_category_button("❌", "Absent Day", "(A)")
        self.btn_card_undo_absent  = self.create_category_button("↩️", "Undo Absent", "(Deduct)")
        self.btn_card_worked_off   = self.create_category_button("📅", "Worked Off", "(WWO)")

        cat_layout.addWidget(self.btn_card_present, 0, 0)
        cat_layout.addWidget(self.btn_card_half, 0, 1)
        cat_layout.addWidget(self.btn_card_paid, 0, 2)
        cat_layout.addWidget(self.btn_card_unpaid, 0, 3)
        cat_layout.addWidget(self.btn_card_absent, 1, 0)
        cat_layout.addWidget(self.btn_card_undo_absent, 1, 1)
        cat_layout.addWidget(self.btn_card_worked_off, 1, 2)

        self.btn_card_present.clicked.connect(self.quick_fill_present)
        self.btn_card_half.clicked.connect(self.quick_increment_half)
        self.btn_card_paid.clicked.connect(self.quick_increment_paid)
        self.btn_card_unpaid.clicked.connect(self.quick_increment_unpaid)
        self.btn_card_absent.clicked.connect(self.quick_increment_absent)
        self.btn_card_undo_absent.clicked.connect(self.quick_deduct_absent)
        self.btn_card_worked_off.clicked.connect(self.quick_increment_worked_off)
        left_layout.addWidget(cat_widget)

        # Inputs Grid
        inputs_widget = QWidget()
        inputs_layout = QGridLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(8)
        
        def create_input_col(label_text, sb_attr, row, col_idx):
            col = QVBoxLayout()
            col.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet("color: #94a3b8;")
            sb = QSpinBox()
            sb.setRange(0, 1)
            sb.setFixedHeight(34)
            sb.setAlignment(Qt.AlignCenter)
            sb.setStyleSheet("""
                QSpinBox {
                    background-color: #1a1a20; border: 1px solid #2e2e38; border-radius: 6px;
                    color: #ffffff; font-size: 13px; font-weight: bold;
                }
            """)
            sb.valueChanged.connect(self.validate_attendance_days)
            setattr(self, sb_attr, sb)
            col.addWidget(lbl)
            col.addWidget(sb)
            inputs_layout.addLayout(col, row, col_idx)

        create_input_col("Present Days", "sb_full_days", 0, 0)
        create_input_col("Half Days", "sb_half_days", 0, 1)
        create_input_col("Paid Leave", "sb_paid_leave", 0, 2)
        create_input_col("Unpaid Leave", "sb_unpaid_leave", 1, 0)
        create_input_col("Worked Weekly Off", "sb_worked_weekly_off", 1, 1)

        left_layout.addWidget(inputs_widget)

        # Late / Early ComboBox Row & Designation Row
        details_widget = QWidget()
        details_layout = QHBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(10)

        # Late Coming Row
        late_row = QHBoxLayout()
        late_row.setSpacing(6)
        late_lbl = QLabel("Late Coming?")
        late_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        late_lbl.setStyleSheet("color: #94a3b8;")
        self.cmb_late = QComboBox()
        self.cmb_late.addItems(["No", "Yes"])
        self.cmb_late.setFixedWidth(80)
        self.cmb_late.setFixedHeight(28)
        self.cmb_late.setStyleSheet("""
            QComboBox {
                background-color: #1e1e24;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 1px 2px 1px 6px;
                color: #ffffff;
                font-weight: bold;
            }
            QComboBox::drop-down {
                width: 14px;
                border: none;
            }
        """)
        late_row.addWidget(late_lbl)
        late_row.addWidget(self.cmb_late)
        late_row.addStretch()
        details_layout.addLayout(late_row, 1)

        # Early Leaving Row
        early_row = QHBoxLayout()
        early_row.setSpacing(6)
        early_lbl = QLabel("Early Leaving?")
        early_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        early_lbl.setStyleSheet("color: #94a3b8;")
        self.cmb_early = QComboBox()
        self.cmb_early.addItems(["No", "Yes"])
        self.cmb_early.setFixedWidth(80)
        self.cmb_early.setFixedHeight(28)
        self.cmb_early.setStyleSheet("""
            QComboBox {
                background-color: #1e1e24;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 1px 2px 1px 6px;
                color: #ffffff;
                font-weight: bold;
            }
            QComboBox::drop-down {
                width: 14px;
                border: none;
            }
        """)
        early_row.addWidget(early_lbl)
        early_row.addWidget(self.cmb_early)
        early_row.addStretch()
        details_layout.addLayout(early_row, 1)

        # Remarks (Optional) character counter layout
        rem_col = QVBoxLayout()
        rem_col.setSpacing(4)
        rem_header = QHBoxLayout()
        rem_lbl = QLabel("Remarks (Optional)")
        rem_lbl.setFont(QFont("Segoe UI", 9))
        rem_lbl.setStyleSheet("color: #94a3b8;")
        rem_header.addWidget(rem_lbl)
        rem_header.addStretch()
        
        self.lbl_remarks_count = QLabel("0 / 250")
        self.lbl_remarks_count.setFont(QFont("Segoe UI", 8))
        self.lbl_remarks_count.setStyleSheet("color: #64748b;")
        rem_header.addWidget(self.lbl_remarks_count)
        rem_col.addLayout(rem_header)
        
        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Add any remarks here...")
        self.txt_remarks.setFixedHeight(34)
        self.txt_remarks.setMaxLength(250)
        self.txt_remarks.textChanged.connect(self.update_remarks_count)
        
        rem_col.addWidget(self.txt_remarks)
        details_layout.addLayout(rem_col, 2)

        left_layout.addWidget(details_widget)

        # Form actions buttons
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("🗑️  Clear")
        self.btn_clear.setProperty("class", "SecondaryBtn")
        self.btn_clear.setFixedHeight(36)
        self.btn_clear.clicked.connect(self.clear_fields)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("💾  Save (Ctrl + S)")
        self.btn_save.setProperty("class", "PrimaryBtn")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setStyleSheet("background-color: #16a34a; color: white; border-radius: 6px; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_attendance)
        btn_layout.addWidget(self.btn_save)

        self.btn_save_next = QPushButton("➡️  Save & Next (Alt + N)")
        self.btn_save_next.setProperty("class", "PrimaryBtn")
        self.btn_save_next.setFixedHeight(36)
        self.btn_save_next.setStyleSheet("background-color: #4f46e5; color: white; border-radius: 6px; font-weight: bold;")
        self.btn_save_next.clicked.connect(self.save_and_next)
        btn_layout.addWidget(self.btn_save_next)
        
        left_layout.addLayout(btn_layout)
        split_layout.addWidget(left_card, 3)

        # RIGHT COLUMN - Attendance Summary Card
        right_card = QFrame()
        right_card.setProperty("class", "DashboardCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)
        
        right_title = QLabel("Attendance Summary")
        right_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        right_layout.addWidget(right_title)

        # Summary list
        self.summary_list = QFormLayout()
        self.summary_list.setVerticalSpacing(6)
        
        self.lbl_sum_working = QLabel("31")
        self.lbl_sum_present = QLabel("0")
        self.lbl_sum_half = QLabel("0")
        self.lbl_sum_paid = QLabel("0")
        self.lbl_sum_unpaid = QLabel("0")
        self.lbl_sum_weekly_off = QLabel("0")
        self.lbl_sum_holidays = QLabel("0")
        self.lbl_sum_absent = QLabel("0")
        self.lbl_sum_worked_woff = QLabel("0")
        self.lbl_sum_total = QLabel("0")
        
        for lbl in [self.lbl_sum_working, self.lbl_sum_present, self.lbl_sum_half, self.lbl_sum_paid,
                    self.lbl_sum_unpaid, self.lbl_sum_weekly_off, self.lbl_sum_holidays,
                    self.lbl_sum_absent, self.lbl_sum_worked_woff, self.lbl_sum_total]:
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("color: #ffffff;")
        
        def add_summary_row(emoji, text, widget):
            row_lbl = QLabel(f"{emoji}  {text}")
            row_lbl.setFont(QFont("Segoe UI", 9.5))
            row_lbl.setStyleSheet("color: #cbd5e1;")
            self.summary_list.addRow(row_lbl, widget)

        add_summary_row("🔵", "Working Days", self.lbl_sum_working)
        add_summary_row("🟢", "Present Days", self.lbl_sum_present)
        add_summary_row("🟠", "Half Days (0.5)", self.lbl_sum_half)
        add_summary_row("🔵", "Paid Leave", self.lbl_sum_paid)
        add_summary_row("🟣", "Unpaid Leave", self.lbl_sum_unpaid)
        add_summary_row("📅", "Weekly Off Days", self.lbl_sum_weekly_off)
        add_summary_row("🎉", "Paid Holidays", self.lbl_sum_holidays)
        add_summary_row("🔴", "Absent Days (Auto)", self.lbl_sum_absent)
        add_summary_row("🟡", "Worked Weekly Off", self.lbl_sum_worked_woff)
        
        # Divider line
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background-color: #2e2e38;")
        self.summary_list.addRow(div)

        lbl_tot_title = QLabel("Total Accounted")
        lbl_tot_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_tot_title.setStyleSheet("color: #6366f1;")
        self.lbl_sum_total.setStyleSheet("color: #6366f1; font-size: 11px;")
        self.summary_list.addRow(lbl_tot_title, self.lbl_sum_total)
        
        right_layout.addLayout(self.summary_list)

        # Attendance Progress Card
        prog_card = QFrame()
        prog_card.setObjectName("ProgressCard")
        prog_card.setStyleSheet("""
            QFrame#ProgressCard {
                background-color: #14532d; border: 1.5px solid #16a34a; border-radius: 8px; padding: 10px;
            }
            QLabel { background: transparent; border: none; }
        """)
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setSpacing(4)
        
        prog_header = QHBoxLayout()
        prog_title = QLabel("Attendance Progress")
        prog_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        prog_title.setStyleSheet("color: #4ade80;")
        self.lbl_progress_percent = QLabel("87%")
        self.lbl_progress_percent.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_progress_percent.setStyleSheet("color: #4ade80;")
        prog_header.addWidget(prog_title)
        prog_header.addStretch()
        prog_header.addWidget(self.lbl_progress_percent)
        prog_layout.addLayout(prog_header)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(87)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #1a1a20; border-radius: 4px; }
            QProgressBar::chunk { background-color: #16a34a; border-radius: 4px; }
        """)
        prog_layout.addWidget(self.progress_bar)
        
        prog_footer = QHBoxLayout()
        self.lbl_progress_ratio = QLabel("27 / 31 Days")
        self.lbl_progress_ratio.setFont(QFont("Segoe UI", 9))
        self.lbl_progress_ratio.setStyleSheet("color: #a7f3d0;")
        prog_footer.addWidget(self.lbl_progress_ratio)
        prog_footer.addStretch()
        prog_layout.addLayout(prog_footer)

        # Green tick status bar inside card
        self.status_box = QFrame()
        self.status_box.setStyleSheet("background-color: #166534; border-radius: 4px;")
        status_box_lay = QHBoxLayout(self.status_box)
        status_box_lay.setContentsMargins(8, 4, 8, 4)
        status_box_lay.setSpacing(6)
        
        self.lbl_check_icon = QLabel("✔️")
        self.lbl_check_icon.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_check_icon.setStyleSheet("color: #4ade80;")
        self.lbl_progress_status = QLabel("All days accounted successfully!")
        self.lbl_progress_status.setFont(QFont("Segoe UI", 9))
        self.lbl_progress_status.setStyleSheet("color: #4ade80;")
        
        status_box_lay.addWidget(self.lbl_check_icon)
        status_box_lay.addWidget(self.lbl_progress_status)
        status_box_lay.addStretch()
        prog_layout.addWidget(self.status_box)
        
        right_layout.addWidget(prog_card)

        # Import Sheet & Template clickable cards (bottom horizontal layout)
        import_layout = QHBoxLayout()
        import_layout.setSpacing(8)

        # Import Excel card
        self.btn_import_card = ClickableFrame(self)
        self.btn_import_card.setCursor(Qt.PointingHandCursor)
        self.btn_import_card.setStyleSheet("""
            QFrame {
                background-color: #1a1a20; border: 1.5px solid #16a34a; border-radius: 8px;
            }
            QFrame:hover { background-color: #202028; }
            QLabel { background: transparent; border: none; }
        """)
        self.btn_import_card.clicked.connect(self.import_attendance)
        
        imp_card_lay = QHBoxLayout(self.btn_import_card)
        imp_card_lay.setContentsMargins(8, 6, 8, 6)
        imp_card_lay.setSpacing(8)
        
        imp_icon = QLabel("📊")
        imp_icon.setFont(QFont("Segoe UI", 28))
        imp_icon.setStyleSheet("color: #16a34a;")
        imp_text_lay = QVBoxLayout()
        imp_text_lay.setSpacing(1)
        imp_title = QLabel("Import Sheet")
        imp_title.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        imp_title.setStyleSheet("color: #ffffff;")
        imp_desc = QLabel("Upload attendance\nfrom Excel")
        imp_desc.setFont(QFont("Segoe UI", 8))
        imp_desc.setStyleSheet("color: #94a3b8;")
        imp_text_lay.addWidget(imp_title)
        imp_text_lay.addWidget(imp_desc)
        imp_card_lay.addWidget(imp_icon)
        imp_card_lay.addLayout(imp_text_lay)
        import_layout.addWidget(self.btn_import_card, 1)

        # Download Template card
        self.btn_template_card = ClickableFrame(self)
        self.btn_template_card.setCursor(Qt.PointingHandCursor)
        self.btn_template_card.setStyleSheet("""
            QFrame {
                background-color: #1a1a20; border: 1.5px solid #8b5cf6; border-radius: 8px;
            }
            QFrame:hover { background-color: #202028; }
            QLabel { background: transparent; border: none; }
        """)
        self.btn_template_card.clicked.connect(self.download_template)
        
        temp_card_lay = QHBoxLayout(self.btn_template_card)
        temp_card_lay.setContentsMargins(8, 6, 8, 6)
        temp_card_lay.setSpacing(8)
        
        temp_icon = QLabel("📝")
        temp_icon.setFont(QFont("Segoe UI", 28))
        temp_icon.setStyleSheet("color: #8b5cf6;")
        temp_text_lay = QVBoxLayout()
        temp_text_lay.setSpacing(1)
        temp_title = QLabel("Template")
        temp_title.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        temp_title.setStyleSheet("color: #ffffff;")
        temp_desc = QLabel("Download attendance\ntemplate")
        temp_desc.setFont(QFont("Segoe UI", 8))
        temp_desc.setStyleSheet("color: #94a3b8;")
        temp_text_lay.addWidget(temp_title)
        temp_text_lay.addWidget(temp_desc)
        temp_card_lay.addWidget(temp_icon)
        temp_card_lay.addLayout(temp_text_lay)
        import_layout.addWidget(self.btn_template_card, 1)
        
        right_layout.addLayout(import_layout)

        split_layout.addWidget(right_card, 2)
        layout.addWidget(split_widget)

        # ── 6. KEYBOARD SHORTCUTS FOOTER ──────────────────────────────────────
        self.footer_frame = QFrame()
        self.footer_frame.setStyleSheet("background-color: #2b2b3b; border-radius: 6px;" if self.theme == "dark" else "background-color: #f1f5f9; border-radius: 6px;")
        footer_layout = QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(15, 8, 15, 8)
        
        self.shortcuts_lbl = QLabel("💡 Shortcuts:  Tab → Next Field  |  Ctrl + S → Save  |  Alt + N → Save & Next  |  Esc → Clear")
        self.shortcuts_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.shortcuts_lbl.setStyleSheet("color: #a5b4fc;" if self.theme == "dark" else "color: #4f46e5;")
        footer_layout.addWidget(self.shortcuts_lbl)
        layout.addWidget(self.footer_frame)

        # Hidden spinboxes/inputs to keep DB operations stable
        self.sb_working_days = QSpinBox()
        self.sb_working_days.setValue(31)
        self.sb_weekly_off = QSpinBox()
        self.sb_weekly_off.setValue(4)
        self.sb_absent = QSpinBox()
        
        # Register Hotkeys
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_attendance)
        self.shortcut_next = QShortcut(QKeySequence("Alt+N"), self)
        self.shortcut_next.activated.connect(self.save_and_next)
        self.shortcut_clear = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_clear.activated.connect(self.clear_fields)

        # Set scroll area widget and add to main layout
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def update_theme(self, theme):
        self.theme = theme
        self.update_category_cards_theme()
        
        is_light = (theme == "light")
        is_blueish = (theme == "blueish")
        
        # Profile Card background and borders
        if is_light:
            self.btn_profile_card.setStyleSheet("""
                QFrame#ProfileCard {
                    background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px;
                }
                QFrame#ProfileCard:hover { border-color: #6366f1; }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_profile_details.setStyleSheet("color: #0f172a;")
            self.lbl_emp_info.setStyleSheet("color: #64748b;")
        elif is_blueish:
            self.btn_profile_card.setStyleSheet("""
                QFrame#ProfileCard {
                    background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;
                }
                QFrame#ProfileCard:hover { border-color: #3b82f6; }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_profile_details.setStyleSheet("color: #f8fafc;")
            self.lbl_emp_info.setStyleSheet("color: #94a3b8;")
        else: # dark
            self.btn_profile_card.setStyleSheet("""
                QFrame#ProfileCard {
                    background-color: #1a1a20; border: 1px solid #2d2d35; border-radius: 8px;
                }
                QFrame#ProfileCard:hover { border-color: #6366f1; }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_profile_details.setStyleSheet("color: #f8fafc;")
            self.lbl_emp_info.setStyleSheet("color: #94a3b8;")
            
        # Footer
        if is_light:
            self.footer_frame.setStyleSheet("background-color: #f1f5f9; border-radius: 6px;")
            self.shortcuts_lbl.setStyleSheet("color: #4f46e5;")
        elif is_blueish:
            self.footer_frame.setStyleSheet("background-color: #1e293b; border-radius: 6px;")
            self.shortcuts_lbl.setStyleSheet("color: #60a5fa;")
        else: # dark
            self.footer_frame.setStyleSheet("background-color: #2b2b3b; border-radius: 6px;")
            self.shortcuts_lbl.setStyleSheet("color: #a5b4fc;")

    def update_remarks_count(self):
        self.lbl_remarks_count.setText(f"{len(self.txt_remarks.text())} / 250")

    def update_category_cards_theme(self):
        is_dark = (self.theme == "dark")
        
        # Styles: (btn, dark_bg, dark_border, dark_fg, light_bg, light_border, light_fg)
        styles = [
            (self.btn_card_present,     "#14532d", "1.5px solid #16a34a", "#4ade80", "#f0fdf4", "1.5px solid #bbf7d0", "#166534"),
            (self.btn_card_half,        "#7c2d12", "1.5px solid #ea580c", "#ffedd5", "#fff7ed", "1.5px solid #ffedd5", "#9a3412"),
            (self.btn_card_paid,        "#1e3a8a", "1.5px solid #2563eb", "#dbeafe", "#eff6ff", "1.5px solid #dbeafe", "#1e40af"),
            (self.btn_card_unpaid,      "#581c87", "1.5px solid #9333ea", "#f3e8ff", "#faf5ff", "1.5px solid #f3e8ff", "#6b21a8"),
            (self.btn_card_absent,      "#7f1d1d", "1.5px solid #dc2626", "#fee2e2", "#fef2f2", "1.5px solid #fee2e2", "#991b1b"),
            (self.btn_card_undo_absent,  "#450a0a", "1.8px dashed #f43f5e", "#fca5a5", "#fef2f2", "1.8px dashed #f43f5e", "#991b1b"),
            (self.btn_card_worked_off,   "#713f12", "1.5px solid #ca8a04", "#fef08a", "#fef9c3", "1.5px solid #fef08a", "#854d0e")
        ]
        
        for btn, d_bg, d_border, d_fg, l_bg, l_border, l_fg in styles:
            bg = d_bg if is_dark else l_bg
            border = d_border if is_dark else l_border
            fg = d_fg if is_dark else l_fg
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    border: {border};
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {bg}ee;
                }}
            """)
            
            # Find and update the labels inside the button
            layout = btn.layout()
            if layout:
                # First child is the circle label
                circle = layout.itemAt(0).widget()
                if circle:
                    circle.setStyleSheet(f"""
                        background-color: #ffffff;
                        border-radius: 14px;
                        color: {fg};
                        font-weight: bold;
                    """)
                # Second child is the text label
                text_lbl = layout.itemAt(1).widget()
                if text_lbl:
                    text_lbl.setStyleSheet(f"color: {fg}; font-weight: bold;")

    def sync_month_year_dropdowns_to_date(self):
        m = self.cmb_month.currentData()
        y = self.cmb_year.currentData()
        if m and y:
            self.date_selector.blockSignals(True)
            current_day = self.date_selector.date().day()
            max_days = calendar.monthrange(y, m)[1]
            target_day = min(current_day, max_days)
            self.date_selector.setDate(QDate(y, m, target_day))
            self.date_selector.blockSignals(False)
            self.load_attendance()

    def sync_date_picker_to_dropdown(self):
        qdate = self.date_selector.date()
        m = qdate.month()
        y = qdate.year()
        
        self.cmb_month.blockSignals(True)
        self.cmb_month.setCurrentIndex(m - 1)
        self.cmb_month.blockSignals(False)
        
        self.cmb_year.blockSignals(True)
        self.cmb_year.setCurrentText(str(y))
        self.cmb_year.blockSignals(False)
        
        self.load_attendance()

    def load_employees_list(self):
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

    def update_employee_profile_card(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.lbl_avatar.setText("RK")
            self.lbl_avatar.setStyleSheet("background-color: #6366f1; color: white; border-radius: 18px; font-weight: bold;")
            self.lbl_profile_details.setText("<b>None selected</b><br/>Select an employee")
            self.lbl_emp_info.setText("Department: —  |  Designation: —")
            return
            
        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            if emp:
                names = emp.name.split()
                initials = "".join([n[0] for n in names[:2]]).upper() if names else "?"
                self.lbl_avatar.setText(initials)
                
                # Colors based on initials for a dynamic aesthetic touch
                colors = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"]
                color_idx = sum(ord(c) for c in initials) % len(colors)
                self.lbl_avatar.setStyleSheet(f"background-color: {colors[color_idx]}; color: white; border-radius: 18px; font-weight: bold;")
                
                dept_name = emp.department.name if emp.department else "General"
                desig_name = emp.designation.name if emp.designation else "Staff"
                
                self.lbl_profile_details.setText(f"<b>{emp.name} ({emp.employee_code})</b><br/>Select an employee")
                self.lbl_emp_info.setText(f"Department: {dept_name}  |  Designation: {desig_name}")
        finally:
            db.close()

    def show_employee_dropdown(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #1e1e24; border: 1px solid #2d2d34; border-radius: 6px; padding: 5px; }
            QMenu::item { padding: 6px 20px; color: #e2e8f0; }
            QMenu::item:selected { background-color: #6366f1; color: white; }
        """ if self.theme == "dark" else """
            QMenu { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px; }
            QMenu::item { padding: 6px 20px; color: #0f172a; }
            QMenu::item:selected { background-color: #6366f1; color: white; }
        """)
        
        db = SessionLocal()
        try:
            employees = db.query(Employee).filter(Employee.status == "Active").order_by(Employee.name).all()
            for emp in employees:
                action = menu.addAction(f"{emp.name} ({emp.employee_code})")
                action.setData(emp.id)
        finally:
            db.close()

        pos = self.btn_profile_card.mapToGlobal(QPoint(0, self.btn_profile_card.height()))
        selected_action = menu.exec(pos)
        if selected_action:
            emp_id = selected_action.data()
            idx = self.cmb_employee.findData(emp_id)
            if idx >= 0:
                self.cmb_employee.setCurrentIndex(idx)

    def filter_employee_search(self):
        txt = self.txt_search.text().strip().lower()
        if not txt:
            return
        for idx in range(1, self.cmb_employee.count()):
            item_text = self.cmb_employee.itemText(idx).lower()
            if txt in item_text:
                self.cmb_employee.setCurrentIndex(idx)
                break

    def prev_employee(self):
        idx = self.cmb_employee.currentIndex()
        if idx > 1:
            self.cmb_employee.setCurrentIndex(idx - 1)
        elif self.cmb_employee.count() > 1:
            self.cmb_employee.setCurrentIndex(self.cmb_employee.count() - 1)

    def next_employee(self):
        idx = self.cmb_employee.currentIndex()
        if idx < self.cmb_employee.count() - 1:
            self.cmb_employee.setCurrentIndex(idx + 1)
        elif self.cmb_employee.count() > 1:
            self.cmb_employee.setCurrentIndex(1)

    def quick_fill_present(self):
        self.sb_full_days.setValue(1)
        self.sb_half_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_unpaid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)

    def quick_increment_half(self):
        self.sb_half_days.setValue(1)
        self.sb_full_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_unpaid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)

    def quick_increment_paid(self):
        self.sb_paid_leave.setValue(1)
        self.sb_full_days.setValue(0)
        self.sb_half_days.setValue(0)
        self.sb_unpaid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)

    def quick_increment_unpaid(self):
        self.sb_unpaid_leave.setValue(1)
        self.sb_full_days.setValue(0)
        self.sb_half_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)

    def quick_increment_absent(self):
        """Mark absent daily: all status spinboxes reset to 0."""
        self.sb_full_days.setValue(0)
        self.sb_half_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_unpaid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)

    def quick_deduct_absent(self):
        """Undo absent: marks Present Day (Full Day) instead."""
        self.sb_full_days.setValue(1)
        self.sb_half_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_unpaid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)

    def quick_increment_worked_off(self):
        self.sb_worked_weekly_off.setValue(1)
        self.sb_full_days.setValue(0)
        self.sb_half_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_unpaid_leave.setValue(0)

    def clear_fields(self):
        self.sb_full_days.setValue(0)
        self.sb_half_days.setValue(0)
        self.sb_paid_leave.setValue(0)
        self.sb_unpaid_leave.setValue(0)
        self.sb_worked_weekly_off.setValue(0)
        self.cmb_late.setCurrentText("No")
        self.cmb_early.setCurrentText("No")
        self.txt_remarks.clear()
        self.lbl_remarks_count.setText("0 / 250")

    def validate_attendance_days(self) -> bool:
        # Prevent recursive loops
        if hasattr(self, "_validating") and self._validating:
            return True
        self._validating = True
        try:
            sender = self.sender()
            # If a spinbox value was set to 1, clear all others for single-day mutual exclusion
            if isinstance(sender, QSpinBox) and sender.value() > 0:
                for sb in [self.sb_full_days, self.sb_half_days, self.sb_paid_leave,
                           self.sb_unpaid_leave, self.sb_worked_weekly_off]:
                    if sb != sender:
                        sb.setValue(0)

            present = self.sb_full_days.value()
            half = self.sb_half_days.value()
            paid = self.sb_paid_leave.value()
            unpaid = self.sb_unpaid_leave.value()
            worked_woff = self.sb_worked_weekly_off.value()

            total_day = present + half + paid + unpaid + worked_woff
            if total_day > 1:
                self.lbl_check_icon.setText("⚠️")
                self.lbl_check_icon.setStyleSheet("color: #fca5a5; font-weight: bold;")
                self.lbl_progress_status.setText("Error: A single day can only have one status!")
                self.lbl_progress_status.setStyleSheet("color: #fca5a5;")
                self.status_box.setStyleSheet("background-color: #7f1d1d; border-radius: 4px;")
                return False

            self.lbl_check_icon.setText("✔️")
            self.lbl_check_icon.setStyleSheet("color: #4ade80; font-weight: bold;")
            self.lbl_progress_status.setText("Inputs valid for selected date.")
            self.lbl_progress_status.setStyleSheet("color: #4ade80;")
            self.status_box.setStyleSheet("background-color: #166534; border-radius: 4px;")
            return True
        finally:
            self._validating = False

    def recalculate_working_days(self):
        qdate = self.date_selector.date()
        m = qdate.month()
        y = qdate.year()

        month_days = calendar.monthrange(y, m)[1]
        
        # Get target weekday index from selected text
        day_map = {
            "MON": 0, "TUE": 1, "WED": 2, "THU": 3,
            "FRI": 4, "SAT": 5, "SUN": 6
        }
        target_day = day_map.get(self.cmb_weekly_off_day.currentText(), 6)
        
        off_count = 0
        for d in range(1, month_days + 1):
            if date(y, m, d).weekday() == target_day:
                off_count += 1

        db = SessionLocal()
        try:
            start_date = date(y, m, 1)
            end_date = date(y, m, month_days)
            hols_count = db.query(HolidayCalendar).filter(
                HolidayCalendar.holiday_date >= start_date,
                HolidayCalendar.holiday_date <= end_date,
                HolidayCalendar.is_paid == True
            ).count()

            self.lbl_month_days_stat.setText(str(month_days))
            self.lbl_weekly_off_stat.setText(str(off_count))
            self.lbl_holidays_stat.setText(str(hols_count))
            
            working_days = month_days
            self.lbl_working_days_stat.setText(str(working_days))
            
            # Sync hidden settings
            self.sb_working_days.setValue(working_days)
            self.sb_weekly_off.setValue(off_count)

            self.validate_attendance_days()

        finally:
            db.close()

    def refresh_data(self):
        self.load_employees_list()
        self.load_attendance()

    def load_attendance(self):
        emp_id = self.cmb_employee.currentData()
        self.update_employee_profile_card()
        
        qdate = self.date_selector.date()
        m = qdate.month()
        y = qdate.year()
        d = qdate.day()
        date_val = date(y, m, d)

        if emp_id:
            db = SessionLocal()
            try:
                emp = db.query(Employee).filter(Employee.id == emp_id).first()
                if emp:
                    pref_day = emp.weekly_off_day or "SUN"
                    self.cmb_weekly_off_day.blockSignals(True)
                    idx = self.cmb_weekly_off_day.findText(pref_day)
                    if idx >= 0:
                        self.cmb_weekly_off_day.setCurrentIndex(idx)
                    self.cmb_weekly_off_day.blockSignals(False)
            finally:
                db.close()

        # Recalculate working days and weekly off count based on active selections
        self.recalculate_working_days()

        month_days = calendar.monthrange(y, m)[1]
        off_count = int(self.lbl_weekly_off_stat.text())
        hols_count = int(self.lbl_holidays_stat.text())

        if not emp_id:
            self.lbl_sum_working.setText(str(month_days))
            self.lbl_sum_present.setText("0")
            self.lbl_sum_half.setText("0")
            self.lbl_sum_paid.setText("0")
            self.lbl_sum_unpaid.setText("0")
            self.lbl_sum_weekly_off.setText(str(off_count))
            self.lbl_sum_holidays.setText(str(hols_count))
            self.lbl_sum_absent.setText("0")
            self.lbl_sum_worked_woff.setText("0")
            self.lbl_sum_total.setText(f"0 / {month_days} Days")
            self.progress_bar.setValue(0)
            self.lbl_progress_percent.setText("0%")
            self.lbl_progress_ratio.setText(f"0 / {month_days} Days")
            return

        db = SessionLocal()
        try:
            # 1. Load Daily Attendance for selected date
            daily_att = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.date == date_val
            ).first()

            # Prevent recursive validation loops
            self._validating = True
            try:
                if daily_att:
                    self.sb_full_days.setValue(1 if daily_att.status == "Present" else 0)
                    self.sb_half_days.setValue(1 if daily_att.status == "Half Day" else 0)
                    self.sb_paid_leave.setValue(1 if daily_att.status == "Paid Leave" else 0)
                    self.sb_unpaid_leave.setValue(1 if daily_att.status == "Unpaid Leave" else 0)
                    self.sb_worked_weekly_off.setValue(1 if daily_att.status == "Worked Off" else 0)
                    self.cmb_late.setCurrentText("Yes" if daily_att.late_coming else "No")
                    self.cmb_early.setCurrentText("Yes" if daily_att.early_leaving else "No")
                    self.txt_remarks.setText(daily_att.remarks or "")
                else:
                    # Default: all 0 on date-level load when no record exists
                    self.sb_full_days.setValue(0)
                    self.sb_half_days.setValue(0)
                    self.sb_paid_leave.setValue(0)
                    self.sb_unpaid_leave.setValue(0)
                    self.sb_worked_weekly_off.setValue(0)
                    self.cmb_late.setCurrentText("No")
                    self.cmb_early.setCurrentText("No")
                    self.txt_remarks.clear()
            finally:
                self._validating = False

            # 2. Recalculate monthly summary from all daily records for this month
            month_days = calendar.monthrange(y, m)[1]
            start_date = date(y, m, 1)
            end_date = date(y, m, month_days)

            daily_records = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).all()

            present_sum = sum(1 for r in daily_records if r.status == "Present")
            half_sum = sum(1 for r in daily_records if r.status == "Half Day")
            paid_sum = sum(1 for r in daily_records if r.status == "Paid Leave")
            unpaid_sum = sum(1 for r in daily_records if r.status == "Unpaid Leave")
            worked_woff_sum = sum(1 for r in daily_records if r.status == "Worked Off")
            absent_sum = sum(1 for r in daily_records if r.status == "Absent")

            off_count = int(self.lbl_weekly_off_stat.text())
            hols_count = int(self.lbl_holidays_stat.text())

            self.lbl_sum_working.setText(str(month_days))
            self.lbl_sum_present.setText(str(present_sum))
            self.lbl_sum_half.setText(f"{half_sum} ({half_sum * 0.5:.1f} Day)")
            self.lbl_sum_paid.setText(str(paid_sum))
            self.lbl_sum_unpaid.setText(str(unpaid_sum))
            self.lbl_sum_weekly_off.setText(str(off_count))
            self.lbl_sum_holidays.setText(str(hols_count))
            self.lbl_sum_worked_woff.setText(str(worked_woff_sum))
            self.lbl_sum_absent.setText(str(absent_sum))

            total_accounted = present_sum + half_sum + paid_sum + unpaid_sum + worked_woff_sum
            self.lbl_sum_total.setText(f"{total_accounted} / {month_days} Days")

            # Progress bar based on present + worked woff sum over the entire month
            total_count = present_sum + worked_woff_sum
            ratio = int((total_count / max(1, month_days)) * 100)
            self.progress_bar.setValue(ratio)
            self.lbl_progress_percent.setText(f"{ratio}%")
            self.lbl_progress_ratio.setText(f"{total_count} / {month_days} Days")

            self.lbl_check_icon.setText("✔️")
            self.lbl_check_icon.setStyleSheet("color: #4ade80; font-weight: bold;")
            self.lbl_progress_status.setText("Monthly summary computed dynamically.")
            self.lbl_progress_status.setStyleSheet("color: #4ade80;")
            self.status_box.setStyleSheet("background-color: #166534; border-radius: 4px;")

        finally:
            db.close()

    def save_attendance(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            QMessageBox.warning(self, "Selection Required", "Please select an employee first.")
            return

        if not self.validate_attendance_days():
            QMessageBox.critical(self, "Validation Error", "A single day can only have one status.")
            return

        qdate = self.date_selector.date()
        m = qdate.month()
        y = qdate.year()
        d = qdate.day()
        date_val = date(y, m, d)

        # Determine daily status from inputs
        if self.sb_full_days.value() > 0:
            status_val = "Present"
        elif self.sb_half_days.value() > 0:
            status_val = "Half Day"
        elif self.sb_paid_leave.value() > 0:
            status_val = "Paid Leave"
        elif self.sb_unpaid_leave.value() > 0:
            status_val = "Unpaid Leave"
        elif self.sb_worked_weekly_off.value() > 0:
            status_val = "Worked Off"
        else:
            status_val = "Absent"

        late_coming = (self.cmb_late.currentText() == "Yes")
        early_leaving = (self.cmb_early.currentText() == "Yes")
        remarks_val = self.txt_remarks.text().strip()

        db = SessionLocal()
        try:
            # Update employee preferred weekly off day
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            if emp:
                emp.weekly_off_day = self.cmb_weekly_off_day.currentText()

            # 1. Update or create DailyAttendance record
            daily_att = db.query(DailyAttendance).filter(
                DailyAttendance.employee_id == emp_id,
                DailyAttendance.date == date_val
            ).first()

            if not daily_att:
                daily_att = DailyAttendance(
                    employee_id=emp_id,
                    date=date_val,
                    status=status_val,
                    late_coming=late_coming,
                    early_leaving=early_leaving,
                    remarks=remarks_val
                )
                db.add(daily_att)
            else:
                daily_att.status = status_val
                daily_att.late_coming = late_coming
                daily_att.early_leaving = early_leaving
                daily_att.remarks = remarks_val

            db.commit()

            # 2. Recalculate monthly summary and save to Attendance table (for engine compatibility)
            month_days = calendar.monthrange(y, m)[1]
            start_date = date(y, m, 1)
            end_date = date(y, m, month_days)

            daily_records = db.query(DailyAttendance).filter(
                DailyAttendance.employee_id == emp_id,
                DailyAttendance.date >= start_date,
                DailyAttendance.date <= end_date
            ).all()

            present_sum = sum(1 for r in daily_records if r.status == "Present")
            half_sum = sum(1 for r in daily_records if r.status == "Half Day")
            paid_sum = sum(1 for r in daily_records if r.status == "Paid Leave")
            unpaid_sum = sum(1 for r in daily_records if r.status == "Unpaid Leave")
            worked_woff_sum = sum(1 for r in daily_records if r.status == "Worked Off")
            absent_sum = sum(1 for r in daily_records if r.status == "Absent")
            late_coming_days = sum(1 for r in daily_records if r.late_coming)
            early_leaving_days = sum(1 for r in daily_records if r.early_leaving)

            off_count = int(self.lbl_weekly_off_stat.text())
            hols_count = int(self.lbl_holidays_stat.text())

            att = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.month == m,
                Attendance.year == y
            ).first()

            if not att:
                att = Attendance(employee_id=emp_id, month=m, year=y)
                db.add(att)

            att.working_days = month_days
            att.full_days = present_sum
            att.half_days = half_sum
            att.absent_days = absent_sum
            att.paid_leave = paid_sum
            att.unpaid_leave = unpaid_sum
            att.weekly_off = off_count
            att.holidays = hols_count
            att.worked_on_weekly_off = worked_woff_sum
            att.overtime_hours = 0.0
            att.late_coming_days = late_coming_days
            att.early_leaving_days = early_leaving_days
            att.remarks = remarks_val

            db.commit()

            emp_name = self.cmb_employee.currentText()
            AuditLogger.log("Attendance Saved", f"Saved daily status '{status_val}' on {date_val} for {emp_name}")
            QMessageBox.information(self, "Success", "Attendance saved successfully.")
            
            # Reload to refresh summary labels
            self.load_attendance()

        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save attendance: {e}")
        finally:
            db.close()

    def save_and_next(self):
        self.save_attendance()
        self.next_employee()

    def download_template(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Attendance Template", "Attendance_Template.xlsx", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return

        columns = [
            "EmployeeCode", "Month", "Year", "WorkingDays", "FullDays", 
            "HalfDays", "AbsentDays", "WeekdayPaidLeave", "UnpaidLeave", 
            "WeeklyOff", "OvertimeHours", 
            "LateDays", "EarlyDays", "Remarks"
        ]
        sample_data = [{
            "EmployeeCode": "EMP001",
            "Month": datetime.now().month,
            "Year": datetime.now().year,
            "WorkingDays": 26,
            "FullDays": 22,
            "HalfDays": 0,
            "AbsentDays": 0,
            "WeekdayPaidLeave": 0,
            "UnpaidLeave": 0,
            "WeeklyOff": 4,
            "OvertimeHours": 0.0,
            "LateDays": 0,
            "EarlyDays": 0,
            "Remarks": "Regular month"
        }]
        df = pd.DataFrame(sample_data, columns=columns)
        try:
            df.to_excel(filepath, index=False)
            QMessageBox.information(self, "Success", f"Template saved successfully:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")

    def import_attendance(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Attendance File", "", "Spreadsheets (*.xlsx *.csv)"
        )
        if not filepath:
            return

        try:
            if filepath.endswith(".xlsx"):
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath)

            required_cols = [
                "EmployeeCode", "Month", "Year", "WorkingDays", "FullDays", 
                "HalfDays", "AbsentDays", "UnpaidLeave", "WeeklyOff"
            ]

            for col in required_cols:
                if col not in df.columns:
                    QMessageBox.critical(self, "Import Error", f"Missing required column in spreadsheet: {col}")
                    return

            if "WeekdayPaidLeave" in df.columns:
                leave_col = "WeekdayPaidLeave"
            elif "PaidLeave" in df.columns:
                leave_col = "PaidLeave"
            else:
                QMessageBox.critical(self, "Import Error", "Missing required column in spreadsheet: WeekdayPaidLeave or PaidLeave")
                return

            db = SessionLocal()
            imported = 0
            failed = 0
            errors = []

            for index, row in df.iterrows():
                code = str(row["EmployeeCode"]).strip()
                month = int(row["Month"])
                year = int(row["Year"])

                emp = db.query(Employee).filter(Employee.employee_code == code).first()
                if not emp:
                    failed += 1
                    errors.append(f"Row {index+2}: Employee code '{code}' not found.")
                    continue

                working = int(row["WorkingDays"])
                full = int(row["FullDays"])
                half = int(row["HalfDays"])
                absent = int(row["AbsentDays"])
                leave = int(row[leave_col])
                weekly = int(row["WeeklyOff"])

                sum_days = full + half + absent + leave + weekly
                if sum_days != working:
                    failed += 1
                    errors.append(f"Row {index+2}: Validation mismatch. Sum of days is {sum_days}, must equal {working} for code '{code}'.")
                    continue

                att = db.query(Attendance).filter(
                    Attendance.employee_id == emp.id,
                    Attendance.month == month,
                    Attendance.year == year
                ).first()

                if not att:
                    att = Attendance(employee_id=emp.id, month=month, year=year)
                    db.add(att)

                att.working_days = working
                att.full_days = full
                att.half_days = half
                att.absent_days = absent
                att.paid_leave = leave
                att.unpaid_leave = int(row.get("UnpaidLeave", 0))
                att.weekly_off = weekly
                att.holidays = 0
                att.worked_on_weekly_off = 0
                att.overtime_hours = 0.0
                att.late_coming_days = int(row.get("LateDays", 0))
                att.early_leaving_days = int(row.get("EarlyDays", 0))
                att.remarks = str(row.get("Remarks", ""))

                imported += 1

            db.commit()
            AuditLogger.log("Attendance Imported", f"Imported {imported} records. {failed} failed.")

            msg = f"Import Summary:\n- Successfully imported: {imported} records\n- Failed: {failed} records"
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    msg += f"\n... and {len(errors)-10} more errors."

            if failed > 0:
                QMessageBox.warning(self, "Import Complete", msg)
            else:
                QMessageBox.information(self, "Import Success", msg)

            self.load_attendance()

        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to read or parse file: {e}")

    def quick_add_employee(self):
        dlg = QuickAddDialog(self, theme=self.theme)
        if dlg.exec() == QDialog.Accepted:
            new_id = getattr(dlg, "new_emp_id", None)
            self.load_employees_list()
            if new_id:
                idx = self.cmb_employee.findData(new_id)
                if idx >= 0:
                    self.cmb_employee.setCurrentIndex(idx)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_employees_list()

class QuickAddDialog(QDialog):
    def __init__(self, parent=None, theme="dark"):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Quick Add Employee")
        self.setFixedSize(350, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit()
        self.txt_code = QLineEdit()
        
        db = SessionLocal()
        try:
            count = db.query(Employee).count()
            self.txt_code.setText(f"EMP{1001 + count}")
        finally:
            db.close()

        self.cmb_dept = QComboBox()
        self.cmb_desig = QComboBox()
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Permanent", "Contract", "Intern", "Consultant"])

        db = SessionLocal()
        try:
            for d in db.query(Department).all():
                self.cmb_dept.addItem(d.name, d.id)
            for ds in db.query(Designation).all():
                self.cmb_desig.addItem(ds.name, ds.id)
        finally:
            db.close()

        form.addRow("Full Name:", self.txt_name)
        form.addRow("Employee Code:", self.txt_code)
        form.addRow("Department:", self.cmb_dept)
        form.addRow("Designation:", self.cmb_desig)
        form.addRow("Employment Type:", self.cmb_type)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def save(self):
        name = self.txt_name.text().strip()
        code = self.txt_code.text().strip()
        if not name or not code:
            QMessageBox.warning(self, "Validation Error", "Name and Code are required.")
            return

        db = SessionLocal()
        try:
            exists = db.query(Employee).filter(Employee.employee_code == code).first()
            if exists:
                QMessageBox.critical(self, "Error", "Employee Code already exists.")
                return

            emp = Employee(
                employee_code=code,
                name=name,
                department_id=self.cmb_dept.currentData(),
                designation_id=self.cmb_desig.currentData(),
                employment_type=self.cmb_type.currentText(),
                monthly_salary=30000.0,
                half_day_salary=576.92,
                basic_salary=15000.0,
                hra=6000.0,
                status="Active"
            )
            db.add(emp)
            db.commit()
            
            LeaveService.initialize_employee_leaves(db, emp.id)
            AuditLogger.log("Employee Added (Quick)", f"Quick-added employee {name} ({code}) from Attendance module.")
            
            self.new_emp_id = emp.id
            self.accept()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to add employee: {e}")
        finally:
            db.close()
