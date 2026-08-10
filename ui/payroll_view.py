from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QGridLayout, QFormLayout, QTableWidget, QTableWidgetItem, QDateEdit,
                             QHeaderView, QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from database.connection import SessionLocal
from database.models import Employee, Attendance, Payroll, Bonus
from services.payroll_engine import PayrollEngine
from utilities.audit_logger import AuditLogger
from datetime import datetime
from sqlalchemy import func

def number_to_words(num):
    if num == 0:
        return "Rupees Zero Only"
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    def helper(n):
        if n < 20:
            return units[n]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
        elif n < 1000:
            return units[n // 100] + " Hundred" + (" and " + helper(n % 100) if n % 100 != 0 else "")
        elif n < 100000:
            return helper(n // 1000) + " Thousand" + (" " + helper(n % 1000) if n % 1000 != 0 else "")
        elif n < 10000000:
            return helper(n // 100000) + " Lakh" + (" " + helper(n % 100000) if n % 100000 != 0 else "")
        else:
            return helper(n // 10000000) + " Crore" + (" " + helper(n % 10000000) if n % 10000000 != 0 else "")
    try:
        val = int(round(num))
        words = helper(val).strip()
        return f"Rupees {words} Only"
    except Exception:
        return ""


class DonutChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 110)
        self.total_deductions = 0
        self.slices = []

    def setData(self, total_deductions, slices):
        self.total_deductions = total_deductions
        self.slices = slices
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        total_val = sum(s[0] for s in self.slices)
        if total_val == 0:
            painter.setPen(QPen(QColor('#334155'), 14))
            painter.drawArc(rect, 0, 360 * 16)
        else:
            start_angle = 90 * 16
            for val, color in self.slices:
                if val == 0:
                    continue
                span_angle = int(-(val / total_val) * 360 * 16)
                painter.setPen(QPen(color, 14))
                painter.drawArc(rect, start_angle, span_angle)
                start_angle += span_angle
        painter.setPen(QColor('#ffffff'))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        total_text = f"₹{int(round(self.total_deductions)):,}"
        painter.drawText(self.rect().adjusted(0, -10, 0, -10), Qt.AlignCenter, total_text)
        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QColor('#94a3b8'))
        painter.drawText(self.rect().adjusted(0, 14, 0, 14), Qt.AlignCenter, "Total\nDeductions")


class PayrollView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.load_employees_list()

    # ─────────────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────────────
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # ── 1. HEADER ────────────────────────────────────────────────────────
        header = QWidget()
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        hdr_lay.setSpacing(12)

        # Icon + Title
        icon_lbl = QLabel("🧮")
        icon_lbl.setFont(QFont("Segoe UI", 22))
        hdr_lay.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t = QLabel("Payroll Calculation Engine")
        t.setFont(QFont("Segoe UI", 17, QFont.Bold))
        t.setStyleSheet("color: #f8fafc;" if self.theme == "dark" else "color: #0f172a;")
        sub = QLabel("Calculate employee salary and deductions")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #94a3b8;" if self.theme == "dark" else "color: #64748b;")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()

        # Buttons
        btn_grid = QGridLayout()
        btn_grid.setSpacing(8)
        col, row = 0, 0
        for label, primary in [("🔄 Refresh", False), ("📄 Export PDF", False), ("🖨️ Generate Payslip", False),
                                ("💾 Save as Draft", False), ("▶ Process Payroll", True)]:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            if primary:
                btn.setStyleSheet("""
                    QPushButton { background: #4f46e5; color: white; border-radius: 6px;
                        font-size: 13px; font-weight: bold; padding: 0 16px; }
                    QPushButton:hover { background: #4338ca; }
                """)
                btn.clicked.connect(self.process_payroll)
                self.btn_process = btn
            else:
                btn.setStyleSheet("""
                    QPushButton { background: transparent; color: #cbd5e1; border: 1px solid #475569;
                        border-radius: 6px; font-size: 12px; padding: 0 14px; }
                    QPushButton:hover { background: #1e293b; color: white; }
                """ if self.theme == "dark" else """
                    QPushButton { background: white; color: #475569; border: 1px solid #cbd5e1;
                        border-radius: 6px; font-size: 12px; padding: 0 14px; }
                    QPushButton:hover { background: #f1f5f9; }
                """)
                if "Refresh" in label:
                    self.btn_refresh = btn
                    btn.clicked.connect(self.refresh_dashboard)
                elif "Export" in label:
                    self.btn_export_pdf = btn
                elif "Payslip" in label:
                    self.btn_generate_payslip = btn
                else:
                    self.btn_save_draft = btn
            btn_grid.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

        hdr_lay.addLayout(btn_grid)

        layout.addWidget(header)

        # ── 2. EMPLOYEE SELECTION BAR ────────────────────────────────────────
        sel_card = QFrame()
        sel_card.setProperty("class", "DashboardCard")
        sel_outer = QVBoxLayout(sel_card)
        sel_outer.setContentsMargins(14, 10, 14, 10)
        sel_outer.setSpacing(4)

        sel_grid = QGridLayout()
        sel_grid.setSpacing(16)

        # Employee
        emp_col = QVBoxLayout()
        emp_col.setSpacing(4)
        emp_lbl = QLabel("Select Employee")
        emp_lbl.setFont(QFont("Segoe UI", 9))
        emp_lbl.setStyleSheet("color: #94a3b8;" if self.theme == "dark" else "color: #64748b;")
        self.cmb_employee = QComboBox()
        self.cmb_employee.setMinimumWidth(200)
        self.cmb_employee.setFixedHeight(34)
        self.cmb_employee.currentIndexChanged.connect(self.load_calculations)
        emp_col.addWidget(emp_lbl)
        emp_col.addWidget(self.cmb_employee)
        sel_grid.addLayout(emp_col, 0, 0, 1, 2)

        # From Date
        from_col = QVBoxLayout()
        from_col.setSpacing(4)
        from_lbl = QLabel("From Date")
        from_lbl.setFont(QFont("Segoe UI", 9))
        from_lbl.setStyleSheet("color: #94a3b8;" if self.theme == "dark" else "color: #64748b;")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setFixedHeight(34)
        today = QDate.currentDate()
        self.date_from.setDate(QDate(today.year(), today.month(), 1))
        from_col.addWidget(from_lbl)
        from_col.addWidget(self.date_from)
        sel_grid.addLayout(from_col, 0, 2)

        # To Date
        to_col = QVBoxLayout()
        to_col.setSpacing(4)
        to_lbl = QLabel("To Date")
        to_lbl.setFont(QFont("Segoe UI", 9))
        to_lbl.setStyleSheet("color: #94a3b8;" if self.theme == "dark" else "color: #64748b;")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setFixedHeight(34)
        import calendar
        last_day = calendar.monthrange(today.year(), today.month())[1]
        self.date_to.setDate(QDate(today.year(), today.month(), last_day))
        to_col.addWidget(to_lbl)
        to_col.addWidget(self.date_to)
        sel_grid.addLayout(to_col, 0, 3)

        # Period Summary Banner
        self.banner_period_summary = QFrame()
        self.banner_period_summary.setStyleSheet("""
            QFrame { background: #14532d; border: 1px solid #16a34a; border-radius: 8px; }
            QLabel { background: transparent; border: none; }
        """ if self.theme == "dark" else """
            QFrame { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; }
            QLabel { background: transparent; border: none; }
        """)
        banner_inner = QVBoxLayout(self.banner_period_summary)
        banner_inner.setContentsMargins(12, 8, 12, 8)
        banner_inner.setSpacing(3)

        banner_title_row = QHBoxLayout()
        banner_icon = QLabel("📅")
        banner_icon.setFont(QFont("Segoe UI", 12))
        banner_title_lbl = QLabel("Payroll Period Summary")
        banner_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        banner_title_lbl.setStyleSheet("color: #4ade80;" if self.theme == "dark" else "color: #15803d;")
        banner_title_row.addWidget(banner_icon)
        banner_title_row.addWidget(banner_title_lbl)
        banner_title_row.addStretch()

        self.lbl_attendance_info = QLabel("Select an employee first.")
        self.lbl_attendance_info.setFont(QFont("Segoe UI", 9))
        self.lbl_attendance_info.setStyleSheet("color: #a7f3d0;" if self.theme == "dark" else "color: #065f46;")
        self.lbl_attendance_info.setWordWrap(True)

        banner_inner.addLayout(banner_title_row)
        banner_inner.addWidget(self.lbl_attendance_info)
        sel_grid.addWidget(self.banner_period_summary, 1, 0, 1, 4)

        sel_outer.addLayout(sel_grid)

        # Department / Designation info row
        self.lbl_emp_info = QLabel("Department: —  |  Designation: —")
        self.lbl_emp_info.setFont(QFont("Segoe UI", 9))
        self.lbl_emp_info.setStyleSheet("color: #64748b;" if self.theme == "dark" else "color: #64748b;")
        sel_outer.addWidget(self.lbl_emp_info)

        self.date_from.dateChanged.connect(self.sync_dates_and_load)
        self.date_to.dateChanged.connect(self.load_calculations)
        layout.addWidget(sel_card)

        # ── 3. STAT CARDS ────────────────────────────────────────────────────
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)
        self.card_working   = self._stat_card("Working Days",    "0 / 0",  "📅", "#3b82f6", "#1e3a8a")
        self.card_overtime  = self._stat_card("Overtime Hours",  "0.0",    "🕒", "#10b981", "#064e3b")
        self.card_leave     = self._stat_card("Leave Deducted",  "0 Days", "👤", "#f59e0b", "#78350f")
        self.card_weekly_off= self._stat_card("Weekly Off",      "0 Days", "📅", "#8b5cf6", "#581c87")
        self.card_per_day   = self._stat_card("Per Day Salary",  "₹0",     "👛", "#ec4899", "#881337")
        
        stats_layout.addWidget(self.card_working, 0, 0)
        stats_layout.addWidget(self.card_overtime, 0, 1)
        stats_layout.addWidget(self.card_leave, 0, 2)
        stats_layout.addWidget(self.card_weekly_off, 1, 0)
        stats_layout.addWidget(self.card_per_day, 1, 1)
        
        layout.addLayout(stats_layout)

        # ── 4. SPLIT: LEFT (Earnings + Net) | RIGHT (Deductions + Summary) ──
        split = QHBoxLayout()
        split.setSpacing(12)

        # ── LEFT COLUMN ──────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(10)

        # Earnings card
        earn_card = QFrame()
        earn_card.setProperty("class", "DashboardCard")
        earn_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        earn_lay = QVBoxLayout(earn_card)
        earn_lay.setContentsMargins(14, 10, 14, 10)
        earn_lay.setSpacing(6)

        earn_title_row = QHBoxLayout()
        earn_ic = QLabel("📗")
        earn_ic.setFont(QFont("Segoe UI", 14))
        earn_title_lbl = QLabel("EARNINGS & ALLOWANCES")
        earn_title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        earn_title_lbl.setStyleSheet("color: #4ade80;" if self.theme == "dark" else "color: #16a34a;")
        earn_title_row.addWidget(earn_ic)
        earn_title_row.addWidget(earn_title_lbl)
        earn_title_row.addStretch()
        earn_lay.addLayout(earn_title_row)

        self.tbl_earnings = QTableWidget(6, 2)
        self._style_table(self.tbl_earnings)
        self.tbl_earnings.setHorizontalHeaderLabels(["Particulars", "Amount (₹)"])
        self._init_rows(self.tbl_earnings, [
            "Monthly Salary (CTC)",
            "Per Day Salary",
            "Half Day Salary",
            "Worked Weekly Off",
            "Leave Deduction",
            "Gross Earnings (A)",
        ])
        earn_lay.addWidget(self.tbl_earnings)
        left.addWidget(earn_card)

        # Net Payable card
        self.net_frame = QFrame()
        self.net_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.net_frame.setStyleSheet("""
            QFrame { background: #14532d; border: 1.5px solid #16a34a; border-radius: 10px; }
            QLabel { background: transparent; border: none; }
        """ if self.theme == "dark" else """
            QFrame { background: #f0fdf4; border: 1.5px solid #bbf7d0; border-radius: 10px; }
            QLabel { background: transparent; border: none; }
        """)
        net_lay = QVBoxLayout(self.net_frame)
        net_lay.setContentsMargins(16, 14, 16, 14)
        net_lay.setSpacing(10)

        # Net title row
        net_title_row = QHBoxLayout()
        net_ic = QLabel("💰")
        net_ic.setFont(QFont("Segoe UI", 14))
        net_title_lbl = QLabel("NET PAYABLE SALARY")
        net_title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        net_title_lbl.setStyleSheet("color: #4ade80;" if self.theme == "dark" else "color: #15803d;")
        net_title_row.addWidget(net_ic)
        net_title_row.addWidget(net_title_lbl)
        net_title_row.addStretch()

        self.lbl_net_value = QLabel("₹0")
        self.lbl_net_value.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.lbl_net_value.setStyleSheet("color: #4ade80;" if self.theme == "dark" else "color: #15803d;")
        net_title_row.addWidget(self.lbl_net_value)
        net_lay.addLayout(net_title_row)

        # In-Words
        in_words_lbl = QLabel("(In Words)")
        in_words_lbl.setFont(QFont("Segoe UI", 9))
        in_words_lbl.setStyleSheet("color: #a7f3d0;" if self.theme == "dark" else "color: #065f46;")
        net_lay.addWidget(in_words_lbl)

        self.lbl_net_words = QLabel("Rupees Zero Only")
        net_words_font = QFont("Segoe UI", 10)
        net_words_font.setItalic(True)
        self.lbl_net_words.setFont(net_words_font)
        self.lbl_net_words.setStyleSheet("color: #4ade80;" if self.theme == "dark" else "color: #15803d;")
        self.lbl_net_words.setWordWrap(True)
        net_lay.addWidget(self.lbl_net_words)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: 1px solid #166534;" if self.theme == "dark" else "border: 1px solid #bbf7d0;")
        net_lay.addWidget(sep)

        # Breakdown grid
        brk_grid = QGridLayout()
        brk_grid.setSpacing(8)
        brk_grid.setColumnStretch(0, 1)

        def brk_row(label_text, color="#a7f3d0"):
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet(f"color: {color};")
            val = QLabel("₹0")
            val.setFont(QFont("Segoe UI", 10, QFont.Bold))
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val.setStyleSheet("color: #ffffff;" if self.theme == "dark" else "color: #0f172a;")
            return lbl, val

        lbl_a, self.lbl_brk_earnings   = brk_row("Total Earnings (A)")
        lbl_b, self.lbl_brk_deductions = brk_row("Total Deductions (B)")
        lbl_n, self.lbl_brk_net        = brk_row("Net Payable Salary (A - B)", "#4ade80" if self.theme == "dark" else "#15803d")
        self.lbl_brk_deductions.setStyleSheet("color: #fca5a5;" if self.theme == "dark" else "color: #dc2626;")
        self.lbl_brk_net.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_brk_net.setStyleSheet("color: #4ade80;" if self.theme == "dark" else "color: #15803d;")

        lbl_a.setStyleSheet("color: #a7f3d0;" if self.theme == "dark" else "color: #065f46;")
        lbl_b.setStyleSheet("color: #a7f3d0;" if self.theme == "dark" else "color: #065f46;")
        lbl_n.setStyleSheet("color: #4ade80; font-weight: bold;" if self.theme == "dark" else "color: #15803d; font-weight: bold;")

        brk_grid.addWidget(lbl_a, 0, 0)
        brk_grid.addWidget(self.lbl_brk_earnings, 0, 1)
        brk_grid.addWidget(lbl_b, 1, 0)
        brk_grid.addWidget(self.lbl_brk_deductions, 1, 1)
        brk_grid.addWidget(lbl_n, 2, 0)
        brk_grid.addWidget(self.lbl_brk_net, 2, 1)
        net_lay.addLayout(brk_grid)
        net_lay.addStretch()

        left.addWidget(self.net_frame)
        split.addLayout(left, 1)

        # ── RIGHT COLUMN ─────────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(10)

        # Taxes card
        ded_card = QFrame()
        ded_card.setProperty("class", "DashboardCard")
        ded_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ded_lay = QVBoxLayout(ded_card)
        ded_lay.setContentsMargins(14, 10, 14, 10)
        ded_lay.setSpacing(6)

        ded_title_row = QHBoxLayout()
        ded_ic = QLabel("🛡️")
        ded_ic.setFont(QFont("Segoe UI", 14))
        ded_title_lbl = QLabel("TAXES & DEDUCTIONS")
        ded_title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ded_title_lbl.setStyleSheet("color: #f87171;" if self.theme == "dark" else "color: #dc2626;")
        ded_title_row.addWidget(ded_ic)
        ded_title_row.addWidget(ded_title_lbl)
        ded_title_row.addStretch()
        ded_lay.addLayout(ded_title_row)

        self.tbl_deductions = QTableWidget(7, 2)
        self._style_table(self.tbl_deductions)
        self.tbl_deductions.setHorizontalHeaderLabels(["Particulars", "Amount (₹)"])
        self._init_rows(self.tbl_deductions, [
            "Provident Fund (PF)",
            "State Insurance (ESI)",
            "Professional Tax (PT)",
            "TDS (Income Tax)",
            "Late Coming Penalty",
            "Advance Recovery",
            "Total Deductions (B)",
        ])
        ded_lay.addWidget(self.tbl_deductions)
        right.addWidget(ded_card)

        # Deduction Summary card
        summary_card = QFrame()
        summary_card.setProperty("class", "DashboardCard")
        summary_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sum_lay = QVBoxLayout(summary_card)
        sum_lay.setContentsMargins(14, 10, 14, 10)
        sum_lay.setSpacing(8)

        sum_title_row = QHBoxLayout()
        sum_ic = QLabel("🍩")
        sum_ic.setFont(QFont("Segoe UI", 14))
        sum_title_lbl = QLabel("DEDUCTION SUMMARY")
        sum_title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        sum_title_lbl.setStyleSheet("color: #f8fafc;" if self.theme == "dark" else "color: #0f172a;")
        sum_title_row.addWidget(sum_ic)
        sum_title_row.addWidget(sum_title_lbl)
        sum_title_row.addStretch()
        sum_lay.addLayout(sum_title_row)

        # Donut + legend side-by-side
        sum_body = QHBoxLayout()
        sum_body.setSpacing(14)

        self.donut_chart = DonutChartWidget()
        sum_body.addWidget(self.donut_chart, 0, Qt.AlignVCenter)

        # 3-column legend: dot+name | amount | %
        legend_grid = QGridLayout()
        legend_grid.setSpacing(6)
        legend_grid.setColumnStretch(0, 1)

        COLORS = ["#6366f1", "#10b981", "#f59e0b", "#3b82f6", "#f43f5e", "#ec4899"]
        LABELS = ["Provident Fund (PF)", "State Insurance (ESI)", "Professional Tax (PT)",
                  "TDS (Income Tax)", "Late Coming Penalty", "Advance Recovery"]

        self._legend_amt_lbls = []
        self._legend_pct_lbls = []

        for i, (label, color) in enumerate(zip(LABELS, COLORS)):
            # Dot + name
            name_row = QHBoxLayout()
            name_row.setSpacing(6)
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 10))
            dot.setStyleSheet(f"color: {color};")
            name_lbl = QLabel(label)
            name_lbl.setFont(QFont("Segoe UI", 9))
            name_lbl.setStyleSheet("color: #94a3b8;" if self.theme == "dark" else "color: #475569;")
            name_row.addWidget(dot)
            name_row.addWidget(name_lbl)
            name_row.addStretch()
            name_widget = QWidget()
            name_widget.setLayout(name_row)

            amt_lbl = QLabel("₹0")
            amt_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt_lbl.setStyleSheet("color: #e2e8f0;" if self.theme == "dark" else "color: #0f172a;")

            pct_lbl = QLabel("(0%)")
            pct_lbl.setFont(QFont("Segoe UI", 9))
            pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            pct_lbl.setStyleSheet("color: #64748b;")

            legend_grid.addWidget(name_widget, i, 0)
            legend_grid.addWidget(amt_lbl, i, 1)
            legend_grid.addWidget(pct_lbl, i, 2)

            self._legend_amt_lbls.append(amt_lbl)
            self._legend_pct_lbls.append(pct_lbl)

        sum_body.addLayout(legend_grid, 1)
        sum_lay.addLayout(sum_body)
        sum_lay.addStretch()

        right.addWidget(summary_card)
        split.addLayout(right, 1)

        layout.addLayout(split, 1)

        # ── 5. BOTTOM INFO BAR ───────────────────────────────────────────────
        self.info_bar = QFrame()
        self.info_bar.setStyleSheet("""
            QFrame { background: #1e3a5f; border: 1px solid #2563eb; border-radius: 8px; }
            QLabel { background: transparent; border: none; }
        """ if self.theme == "dark" else """
            QFrame { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; }
            QLabel { background: transparent; border: none; }
        """)
        info_lay = QHBoxLayout(self.info_bar)
        info_lay.setContentsMargins(14, 8, 14, 8)
        info_lay.setSpacing(10)
        info_lay.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        info_icon = QLabel("ℹ️")
        info_icon.setFont(QFont("Segoe UI", 11))
        self.info_text = QLabel("Please review all the details carefully before processing the payroll.")
        self.info_text.setFont(QFont("Segoe UI", 9))
        self.info_text.setStyleSheet("color: #93c5fd;" if self.theme == "dark" else "color: #1d4ed8;")
        info_lay.addWidget(info_icon)
        info_lay.addWidget(self.info_text)
        info_lay.addStretch()

        layout.addWidget(self.info_bar)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _stat_card(self, title, value, icon, accent, icon_bg):
        card = QFrame()
        card.setProperty("class", "DashboardCard")
        card.setFixedHeight(78)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)

        icon_container = QLabel(icon)
        icon_container.setFixedSize(42, 42)
        icon_container.setAlignment(Qt.AlignCenter)
        icon_container.setFont(QFont("Segoe UI", 15))
        icon_container.setStyleSheet(f"""
            background-color: {icon_bg};
            border-radius: 8px;
            color: #ffffff;
        """)
        lay.addWidget(icon_container)

        v = QVBoxLayout()
        v.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 9))
        t.setStyleSheet("color: #94a3b8;" if self.theme == "dark" else "color: #64748b;")
        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        val_lbl.setStyleSheet(f"color: {accent};")
        card.lbl_val = val_lbl
        card.lbl_title = t
        v.addWidget(t)
        v.addWidget(val_lbl)
        lay.addLayout(v)
        return card

    def _style_table(self, table: QTableWidget):
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        num_rows = table.rowCount()
        table.horizontalHeader().setFixedHeight(28)
        for r in range(num_rows):
            table.setRowHeight(r, 25)
        table.setFixedHeight(28 + (num_rows * 25) + 4)

        table.setStyleSheet("""
            QTableWidget {
                background: #1a1a20; alternate-background-color: #22222a;
                border: 1px solid #2d2d35; color: #e2e8f0; border-radius: 6px;
            }
            QHeaderView::section {
                background: #272730; color: #94a3b8; padding: 5px;
                border: none; font-size: 10px; font-weight: bold;
            }
        """ if self.theme == "dark" else """
            QTableWidget {
                background: #ffffff; alternate-background-color: #f8fafc;
                border: 1px solid #e2e8f0; color: #0f172a; border-radius: 6px;
            }
            QHeaderView::section {
                background: #f1f5f9; color: #64748b; padding: 5px;
                border: none; font-size: 10px; font-weight: bold;
            }
        """)

    def _init_rows(self, table, labels):
        for i, lbl in enumerate(labels):
            table.setItem(i, 0, QTableWidgetItem(lbl))
            item = QTableWidgetItem("₹0")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, 1, item)

    def set_table_value(self, table, row, col, text, is_bold=False, bg_color=None, fg_color=None):
        item = table.item(row, col)
        if not item:
            item = QTableWidgetItem()
            table.setItem(row, col, item)
        item.setText(text)
        font = QFont("Segoe UI", 10)
        if is_bold:
            font.setBold(True)
        item.setFont(font)
        if bg_color:
            item.setBackground(QColor(bg_color))
        if fg_color:
            item.setForeground(QColor(fg_color))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter if col == 1 else Qt.AlignLeft | Qt.AlignVCenter)

    # ─────────────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────────────────────
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

    def showEvent(self, event):
        super().showEvent(event)
        self.load_employees_list()

    def trigger_realtime_calc(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            return
        qdate = self.date_from.date()
        m, y = qdate.month(), qdate.year()
        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            att = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.month == m,
                Attendance.year == y
            ).first()
            if not emp or not att:
                self.clear_outputs()
                return

            # Update dept/designation
            dept = getattr(emp, "department", None) or "—"
            desig = getattr(emp, "designation", None) or "—"
            self.lbl_emp_info.setText(f"Department: {dept}  |  Designation: {desig}")

            bonus = db.query(func.sum(Bonus.amount)).filter(
                Bonus.employee_id == emp_id,
                Bonus.month == m,
                Bonus.year == y,
                Bonus.status == "Pending"
            ).scalar() or 0.0

            res = PayrollEngine.calculate_realtime(db, emp, att, bonus, 0.0, 0.0, 0.0)

            # Stat cards
            worked = att.full_days or 0
            tot = att.working_days or 30
            self.card_working.lbl_val.setText(f"{worked} / {tot}")
            self.card_overtime.lbl_val.setText(f"{att.overtime_hours or 0.0}")
            self.card_leave.lbl_val.setText(f"{int(res['leave_days'])} Days")
            self.card_weekly_off.lbl_val.setText(f"{att.weekly_off or 0} Days")
            self.card_per_day.lbl_val.setText(f"₹{int(round(res['per_day_salary'])):,}")

            # Earnings table rows:
            # 0: Monthly Salary (CTC)
            # 1: Per Day Salary
            # 2: Half Day Salary
            # 3: Worked Weekly Off
            # 4: Leave Deduction
            # 5: Gross Earnings (A)  [highlighted]

            ctc         = res['monthly_salary']
            per_day     = res['per_day_salary']

            # Half Day Salary: Per Day / 2 if half days taken, else 0
            half_days   = att.half_days or 0
            half_day_val = (per_day / 2) * half_days if half_days > 0 else 0

            # Worked Weekly Off: X days × Per Day
            woff_days   = res['worked_weekly_off_days']
            woff_amt    = res['worked_weekly_off_amount']

            # Leave Deduction: leave days × Per Day
            leave_days  = res['leave_days']
            leave_ded   = res['leave_deduction']

            # Gross Earnings = CTC + half-day pay + weekly-off pay - leave deduction
            gross = ctc + half_day_val + woff_amt - leave_ded

            self.set_table_value(self.tbl_earnings, 0, 1, f"₹{int(round(ctc)):,}")
            self.set_table_value(self.tbl_earnings, 1, 1, f"₹{int(round(per_day)):,}")

            # Half Day row — show count in label
            if half_days > 0:
                self.tbl_earnings.item(2, 0).setText(f"Half Day Salary ({half_days} Days)")
                self.set_table_value(self.tbl_earnings, 2, 1, f"₹{int(round(half_day_val)):,}")
            else:
                self.tbl_earnings.item(2, 0).setText("Half Day Salary")
                self.set_table_value(self.tbl_earnings, 2, 1, "₹0")

            # Worked Weekly Off row
            if woff_days > 0:
                self.tbl_earnings.item(3, 0).setText(f"Worked Weekly Off ({woff_days} Days)")
                self.set_table_value(self.tbl_earnings, 3, 1, f"₹{int(round(woff_amt)):,}")
            else:
                self.tbl_earnings.item(3, 0).setText("Worked Weekly Off")
                self.set_table_value(self.tbl_earnings, 3, 1, "₹0")

            # Leave Deduction row
            if leave_days > 0:
                self.tbl_earnings.item(4, 0).setText(f"Leave Deduction ({int(leave_days)} Days)")
                self.set_table_value(self.tbl_earnings, 4, 1, f"₹{int(round(leave_ded)):,}")
            else:
                self.tbl_earnings.item(4, 0).setText("Leave Deduction")
                self.set_table_value(self.tbl_earnings, 4, 1, "₹0")

            # Gross Earnings (A) — highlighted green
            self.set_table_value(self.tbl_earnings, 5, 0, "Gross Earnings (A)",
                                 is_bold=True,
                                 bg_color="#14532d" if self.theme == "dark" else "#dcfce7",
                                 fg_color="#4ade80" if self.theme == "dark" else "#166534")
            self.set_table_value(self.tbl_earnings, 5, 1, f"₹{int(round(gross)):,}",
                                 is_bold=True,
                                 bg_color="#14532d" if self.theme == "dark" else "#dcfce7",
                                 fg_color="#4ade80" if self.theme == "dark" else "#166534")

            # Deductions table
            ded_total = res['total_deductions']
            self.set_table_value(self.tbl_deductions, 0, 1, f"₹{int(round(res['pf_deduction'])):,}")
            self.set_table_value(self.tbl_deductions, 1, 1, f"₹{int(round(res['esi_deduction'])):,}")
            self.set_table_value(self.tbl_deductions, 2, 1, f"₹{int(round(res['prof_tax_deduction'])):,}")
            self.set_table_value(self.tbl_deductions, 3, 1, f"₹{int(round(res['tds_deduction'])):,}")
            self.set_table_value(self.tbl_deductions, 4, 1, f"₹{int(round(res['late_deduction'])):,}")
            self.set_table_value(self.tbl_deductions, 5, 1, f"₹{int(round(res['advance_recovery'])):,}")
            self.set_table_value(self.tbl_deductions, 6, 0, "Total Deductions (B)",
                                 is_bold=True,
                                 bg_color="#881337" if self.theme == "dark" else "#ffe4e6",
                                 fg_color="#fda4af" if self.theme == "dark" else "#9f1239")
            self.set_table_value(self.tbl_deductions, 6, 1, f"₹{int(round(ded_total)):,}",
                                 is_bold=True,
                                 bg_color="#881337" if self.theme == "dark" else "#ffe4e6",
                                 fg_color="#fda4af" if self.theme == "dark" else "#9f1239")

            # Donut chart
            slices = [
                (res['pf_deduction'],          QColor('#6366f1')),
                (res['esi_deduction'],          QColor('#10b981')),
                (res['prof_tax_deduction'],     QColor('#f59e0b')),
                (res['tds_deduction'],          QColor('#3b82f6')),
                (res['late_deduction'],         QColor('#f43f5e')),
                (res['advance_recovery'],       QColor('#ec4899')),
            ]
            self.donut_chart.setData(ded_total, slices)

            # Legend
            vals = [res['pf_deduction'], res['esi_deduction'], res['prof_tax_deduction'],
                    res['tds_deduction'], res['late_deduction'], res['advance_recovery']]
            for i, v in enumerate(vals):
                pct = int(round((v / ded_total) * 100)) if ded_total > 0 else 0
                self._legend_amt_lbls[i].setText(f"₹{int(round(v)):,}")
                self._legend_pct_lbls[i].setText(f"({pct}%)")

            # Net payable card
            net = res['net_salary']
            self.lbl_net_value.setText(f"₹{int(round(net)):,}")
            self.lbl_net_words.setText(number_to_words(net))
            self.lbl_brk_earnings.setText(f"₹{int(round(gross)):,}")
            self.lbl_brk_deductions.setText(f"(-) ₹{int(round(ded_total)):,}")
            self.lbl_brk_net.setText(f"₹{int(round(net)):,}")

        except Exception as e:
            print(f"[PayrollView] Error: {e}")
        finally:
            db.close()

    def clear_outputs(self):
        self.card_working.lbl_val.setText("0 / 0")
        self.card_overtime.lbl_val.setText("0.0")
        self.card_leave.lbl_val.setText("0 Days")
        self.card_weekly_off.lbl_val.setText("0 Days")
        self.card_per_day.lbl_val.setText("₹0")
        self.lbl_emp_info.setText("Department: —  |  Designation: —")

        for row in range(self.tbl_earnings.rowCount()):
            self.set_table_value(self.tbl_earnings, row, 1, "₹0")
        for row in range(self.tbl_deductions.rowCount()):
            self.set_table_value(self.tbl_deductions, row, 1, "₹0")

        self.donut_chart.setData(0, [])
        for lbl in self._legend_amt_lbls:
            lbl.setText("₹0")
        for lbl in self._legend_pct_lbls:
            lbl.setText("(0%)")

        self.lbl_net_value.setText("₹0")
        self.lbl_net_words.setText("Rupees Zero Only")
        self.lbl_brk_earnings.setText("₹0")
        self.lbl_brk_deductions.setText("(-) ₹0")
        self.lbl_brk_net.setText("₹0")

    def sync_dates_and_load(self):
        from_date = self.date_from.date()
        import calendar
        last_day = calendar.monthrange(from_date.year(), from_date.month())[1]
        self.date_to.blockSignals(True)
        self.date_to.setDate(QDate(from_date.year(), from_date.month(), last_day))
        self.date_to.blockSignals(False)
        self.load_calculations()

    def load_calculations(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            self.lbl_attendance_info.setText("Select an employee first.")
            self.lbl_emp_info.setText("Department: —  |  Designation: —")
            self.clear_outputs()
            return
        qdate = self.date_from.date()
        m, y = qdate.month(), qdate.year()
        db = SessionLocal()
        try:
            att = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.month == m,
                Attendance.year == y
            ).first()
            if not att:
                self.lbl_attendance_info.setText("❌ NO ATTENDANCE ENTERED.")
                self.btn_process.setEnabled(False)
                self.clear_outputs()
            else:
                self.lbl_attendance_info.setText(
                    f"Days Worked: {att.full_days}  |  OT Hours: {att.overtime_hours}  |  Off-Day Work: {att.worked_on_weekly_off}")
                self.btn_process.setEnabled(True)
                self.trigger_realtime_calc()
        finally:
            db.close()

    def process_payroll(self):
        emp_id = self.cmb_employee.currentData()
        if not emp_id:
            return
        qdate = self.date_from.date()
        m, y = qdate.month(), qdate.year()
        db = SessionLocal()
        try:
            bonus = db.query(func.sum(Bonus.amount)).filter(
                Bonus.employee_id == emp_id,
                Bonus.month == m,
                Bonus.year == y,
                Bonus.status == "Pending"
            ).scalar() or 0.0
            pay = PayrollEngine.process_payroll(db, emp_id, m, y, bonus, 0.0, 0.0, 0.0)
            emp_name = self.cmb_employee.currentText()
            AuditLogger.log("Payroll Processed",
                            f"Processed for {emp_name} {m}/{y}. Net: ₹{pay.net_salary:,.2f}")
            QMessageBox.information(self, "Success",
                                    f"Payroll processed!\nNet Salary: ₹{pay.net_salary:,.2f}")
            self.load_calculations()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed: {e}")
        finally:
            db.close()

    def refresh_dashboard(self):
        self.load_employees_list()
        self.load_calculations()

    def update_theme(self, theme):
        self.theme = theme
        
        is_light = (theme == "light")
        is_blueish = (theme == "blueish")
        
        # Banner Period Summary theme style
        if is_light:
            self.banner_period_summary.setStyleSheet("""
                QFrame { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
            self.lbl_attendance_info.setStyleSheet("color: #065f46;")
            self.info_bar.setStyleSheet("""
                QFrame { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
            self.info_text.setStyleSheet("color: #1d4ed8;")
            self.lbl_emp_info.setStyleSheet("color: #64748b;")
        elif is_blueish:
            self.banner_period_summary.setStyleSheet("""
                QFrame { background: #0f2e1b; border: 1px solid #10b981; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
            self.lbl_attendance_info.setStyleSheet("color: #a7f3d0;")
            self.info_bar.setStyleSheet("""
                QFrame { background: #0f1e36; border: 1px solid #1e3a8a; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
            self.info_text.setStyleSheet("color: #93c5fd;")
            self.lbl_emp_info.setStyleSheet("color: #94a3b8;")
        else: # dark
            self.banner_period_summary.setStyleSheet("""
                QFrame { background: #14532d; border: 1px solid #16a34a; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
            self.lbl_attendance_info.setStyleSheet("color: #a7f3d0;")
            self.info_bar.setStyleSheet("""
                QFrame { background: #1e3a5f; border: 1px solid #2563eb; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
            self.info_text.setStyleSheet("color: #93c5fd;")
            self.lbl_emp_info.setStyleSheet("color: #94a3b8;")
