import matplotlib
matplotlib.use('QtAgg')

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QGridLayout, QScrollArea, QPushButton, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from database.connection import SessionLocal
from database.models import Employee, Attendance, Payroll, LeaveMaster, Department
from sqlalchemy import func
from datetime import datetime

class TodoCard(QFrame):
    clicked = Signal()
    def __init__(self, title, subtext, icon_char, theme="dark", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.title_text = title
        self.subtext_text = subtext
        self.icon_char = icon_char
        
        self.setProperty("class", "DashboardCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(70)
        
        self.init_ui()
        self.update_style()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        # Left Badge Icon
        self.badge = QLabel(self.icon_char)
        self.badge.setFixedSize(36, 36)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.badge)
        
        # Text details
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        
        self.title_lbl = QLabel(self.title_text)
        self.title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        self.sub_lbl = QLabel(self.subtext_text)
        self.sub_lbl.setFont(QFont("Segoe UI", 8))
        self.sub_lbl.setWordWrap(True)
        
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.sub_lbl)
        layout.addLayout(text_layout, 1)
        
        # Right Chevron
        chevron = QLabel("›")
        chevron.setFont(QFont("Segoe UI", 16, QFont.Bold))
        chevron.setStyleSheet("color: #64748b;")
        layout.addWidget(chevron)

    def update_style(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                QFrame {
                    background-color: #1a1a20;
                    border: 1px solid #2d2d35;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #3b82f6;
                    background-color: #1e1e24;
                }
            """)
            self.badge.setStyleSheet("background-color: #1e293b; color: #38bdf8; border-radius: 18px;")
            self.title_lbl.setStyleSheet("color: #ffffff; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        elif self.theme == "blueish":
            self.setStyleSheet("""
                QFrame {
                    background-color: #131b2e;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #3b82f6;
                    background-color: #17223b;
                }
            """)
            self.badge.setStyleSheet("background-color: #1e293b; color: #38bdf8; border-radius: 18px;")
            self.title_lbl.setStyleSheet("color: #ffffff; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        else: # light
            self.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #3b82f6;
                    background-color: #f1f5f9;
                }
            """)
            self.badge.setStyleSheet("background-color: #eff6ff; color: #1d4ed8; border-radius: 18px;")
            self.title_lbl.setStyleSheet("color: #0f172a; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #64748b; background: transparent; border: none;")

    def setSubtext(self, text):
        self.sub_lbl.setText(text)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class DashboardView(QWidget):
    tab_redirect_requested = Signal(str)

    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(15)

        # Scroll Area for responsive dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(20)

        # 1. Title & Refresh H-Layout
        header_row = QHBoxLayout()
        title_lbl = QLabel("Executive Dashboard")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title_lbl.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_row.addWidget(self.btn_refresh)

        self.scroll_layout.addLayout(header_row)

        # 2. Grid of metrics cards
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(15)
        self.scroll_layout.addLayout(self.cards_layout)

        # 2.5 Things to do Section
        self.todo_header_lbl = QLabel("📋 Things to do")
        self.todo_header_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.todo_header_lbl.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")
        self.scroll_layout.addWidget(self.todo_header_lbl)

        self.todo_layout = QGridLayout()
        self.todo_layout.setSpacing(15)
        
        self.card_todo_ot = TodoCard("Approve Overtime", "0 pending to review", "🕒", self.theme)
        self.card_todo_fine = TodoCard("Approve Fine", "0 days approval pending", "₹", self.theme)
        self.card_todo_celeb = TodoCard("Celebrations", "No celebrations in upcoming days", "🎉", self.theme)
        self.card_todo_new = TodoCard("New Joinees", "No new joinees in upcoming days", "👤", self.theme)

        self.card_todo_ot.clicked.connect(lambda: self.tab_redirect_requested.emit("attendance"))
        self.card_todo_fine.clicked.connect(lambda: self.tab_redirect_requested.emit("attendance"))
        self.card_todo_new.clicked.connect(lambda: self.tab_redirect_requested.emit("employees"))

        self.todo_layout.addWidget(self.card_todo_ot, 0, 0)
        self.todo_layout.addWidget(self.card_todo_fine, 0, 1)
        self.todo_layout.addWidget(self.card_todo_celeb, 1, 0)
        self.todo_layout.addWidget(self.card_todo_new, 1, 1)
        self.scroll_layout.addLayout(self.todo_layout)

        # 3. Charts container
        self.charts_layout = QHBoxLayout()
        self.charts_layout.setSpacing(15)
        self.scroll_layout.addLayout(self.charts_layout)

        # Initialize chart canvas
        self.canvas_fig = Figure(figsize=(10, 4), dpi=100)
        self.canvas = FigureCanvas(self.canvas_fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumSize(400, 250)
        self.charts_layout.addWidget(self.canvas)

        scroll.setWidget(scroll_content)
        self.main_layout.addWidget(scroll)

    def create_card(self, title: str, value: str, row: int, col: int, accent_color: str):
        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        
        # Explicit styles based on current theme to prevent styling loss upon recreation
        if self.theme == "light":
            card.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                }
            """)
            title_color = "#64748b"
        elif self.theme == "blueish":
            card.setStyleSheet("""
                QFrame {
                    background-color: #131b2e;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                }
            """)
            title_color = "#94a3b8"
        else: # dark
            card.setStyleSheet("""
                QFrame {
                    background-color: #1a1a20;
                    border: 1px solid #2d2d35;
                    border-radius: 8px;
                }
            """)
            title_color = "#9ca3af"

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {title_color}; border: none; background: transparent;")
        
        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        val_lbl.setStyleSheet(f"color: {accent_color}; border: none; background: transparent;")
        
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(val_lbl)
        
        self.cards_layout.addWidget(card, row, col)

    def refresh_data(self):
        # Fetch stats from SQLite
        db = SessionLocal()
        try:
            total_emp = db.query(Employee).filter(Employee.status == "Active").count()
            
            # Retrieve latest month's attendance summaries
            present_count = db.query(func.sum(Attendance.full_days)).scalar() or 0
            half_days = db.query(func.sum(Attendance.half_days)).scalar() or 0
            absent_count = db.query(func.sum(Attendance.absent_days)).scalar() or 0
            leave_count = db.query(func.sum(Attendance.paid_leave)).scalar() or 0
            
            # Payroll figures
            gross_total = db.query(func.sum(Payroll.gross_salary + Payroll.total_allowances)).scalar() or 0.0
            net_total = db.query(func.sum(Payroll.net_salary)).scalar() or 0.0
            pf_total = db.query(func.sum(Payroll.pf_deduction)).scalar() or 0.0
            esi_total = db.query(func.sum(Payroll.esi_deduction)).scalar() or 0.0
            tds_total = db.query(func.sum(Payroll.tds_deduction)).scalar() or 0.0
            
            # 1. Update Things to Do counts
            # Approve Overtime: count of attendance records with overtime_hours > 0
            pending_ot = db.query(Attendance).filter(Attendance.overtime_hours > 0).count()
            if pending_ot > 0:
                self.card_todo_ot.setSubtext(f"{pending_ot} pending to review")
            else:
                self.card_todo_ot.setSubtext("No pending reviews")
                
            # Approve Fine: count of attendance records with late_coming_days > 0
            pending_fines = db.query(Attendance).filter(Attendance.late_coming_days > 0).count()
            if pending_fines > 0:
                self.card_todo_fine.setSubtext(f"{pending_fines} days approval pending")
            else:
                self.card_todo_fine.setSubtext("No pending approvals")
                
            # Celebrations: birthdays in current month
            curr_month = datetime.now().month
            birthdays = 0
            all_emp = db.query(Employee).all()
            for emp in all_emp:
                if emp.dob:
                    try:
                        dob_str = str(emp.dob)
                        if f"-{curr_month:02d}-" in dob_str or dob_str.startswith(f"{curr_month:02d}/"):
                            birthdays += 1
                    except Exception:
                        pass
            if birthdays > 0:
                self.card_todo_celeb.setSubtext(f"{birthdays} birthdays this month")
            else:
                self.card_todo_celeb.setSubtext("No celebrations in upcoming days")
                
            # New Joinees: joined in last 30 days
            new_joinees = 0
            for emp in all_emp:
                if emp.joining_date:
                    try:
                        jd = emp.joining_date
                        if isinstance(jd, str):
                            jd = datetime.strptime(jd, "%Y-%m-%d").date()
                        if (datetime.now().date() - jd).days <= 30:
                            new_joinees += 1
                    except Exception:
                        pass
            if new_joinees > 0:
                self.card_todo_new.setSubtext(f"{new_joinees} new joinees this month")
            else:
                self.card_todo_new.setSubtext("No new joinees in upcoming days")
            
            # Clear grid
            while self.cards_layout.count():
                item = self.cards_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Recreate metric cards
            # Row 1
            self.create_card("Total Employees", str(total_emp), 0, 0, "#6366f1")
            self.create_card("Present Days", f"{present_count + (half_days*0.5):.1f}", 0, 1, "#10b981")
            
            # Row 2
            self.create_card("Absent Days", f"{absent_count:.1f}", 1, 0, "#f43f5e")
            self.create_card("On Paid Leave", f"{leave_count:.1f}", 1, 1, "#f59e0b")
            
            # Row 3
            self.create_card("Total Gross Salary", f"₹{int(round(gross_total)):,}", 2, 0, "#a855f7")
            self.create_card("Total Net Salary", f"₹{int(round(net_total)):,}", 2, 1, "#10b981")
            
            # Row 4
            self.create_card("Total PF / ESI", f"₹{int(round(pf_total + esi_total)):,}", 3, 0, "#3b82f6")
            self.create_card("TDS Deducted", f"₹{int(round(tds_total)):,}", 3, 1, "#ec4899")

            # Draw charts
            self.draw_charts(db)
        finally:
            db.close()

    def draw_charts(self, db):
        self.canvas_fig.clear()
        
        # Style variables
        bg_color = '#1a1a20' if self.theme == "dark" else '#ffffff'
        text_color = '#f3f4f6' if self.theme == "dark" else '#0f172a'
        grid_color = '#2e2e38' if self.theme == "dark" else '#e2e8f0'
        
        self.canvas_fig.patch.set_facecolor(bg_color)
        
        # 1. Monthly Payroll Trend (Line Chart)
        ax1 = self.canvas_fig.add_subplot(131)
        ax1.set_facecolor(bg_color)
        
        payroll_trends = db.query(
            Payroll.year, Payroll.month, func.sum(Payroll.net_salary)
        ).group_by(Payroll.year, Payroll.month).order_by(Payroll.year, Payroll.month).limit(6).all()
        
        months = [f"{m[1]}/{m[0]}" for m in payroll_trends] if payroll_trends else ["Jan", "Feb", "Mar"]
        amounts = [float(m[2]) for m in payroll_trends] if payroll_trends else [0.0, 0.0, 0.0]
        
        ax1.plot(months, amounts, marker='o', color='#6366f1', linewidth=2)
        ax1.set_title("Monthly Payroll Trend", color=text_color, fontsize=10, fontweight='bold')
        ax1.tick_params(colors=text_color, labelsize=8)
        ax1.grid(True, color=grid_color, linestyle='--', alpha=0.5)
        
        # 2. Department-wise Salary Distribution (Pie Chart)
        ax2 = self.canvas_fig.add_subplot(132)
        ax2.set_facecolor(bg_color)
        
        dept_data = db.query(
            Department.name, 
            func.sum(Payroll.net_salary)
        ).join(Employee, Employee.department_id == Department.id)\
         .join(Payroll, Payroll.employee_id == Employee.id)\
         .group_by(Department.name).all()
        
        dept_names = [r[0] for r in dept_data] if dept_data else ["Sales", "Engineering", "HR"]
        dept_salaries = [float(r[1]) for r in dept_data] if dept_data else [10000.0, 20000.0, 5000.0]
        
        wedges, texts, autotexts = ax2.pie(
            dept_salaries, labels=dept_names, autopct='%1.1f%%',
            colors=['#6366f1', '#a855f7', '#10b981', '#f59e0b', '#3b82f6'],
            textprops=dict(color=text_color, size=8)
        )
        for autotext in autotexts:
            autotext.set_color('white')
        ax2.set_title("Dept Salary Distribution", color=text_color, fontsize=10, fontweight='bold')

        # 3. Attendance Summary (Bar Chart)
        ax3 = self.canvas_fig.add_subplot(133)
        ax3.set_facecolor(bg_color)
        
        present = db.query(func.sum(Attendance.full_days)).scalar() or 200
        absent = db.query(func.sum(Attendance.absent_days)).scalar() or 10
        leaves = db.query(func.sum(Attendance.paid_leave)).scalar() or 15
        
        labels = ['Present', 'Absent', 'Leave']
        counts = [float(present), float(absent), float(leaves)]
        
        ax3.bar(labels, counts, color=['#10b981', '#f43f5e', '#f59e0b'], width=0.6)
        ax3.set_title("Attendance Breakdown", color=text_color, fontsize=10, fontweight='bold')
        ax3.tick_params(colors=text_color, labelsize=8)
        ax3.grid(True, color=grid_color, linestyle='--', alpha=0.5, axis='y')

        self.canvas_fig.tight_layout()
        self.canvas.draw()

    def update_theme(self, theme):
        self.theme = theme
        self.todo_header_lbl.setStyleSheet("color: #0f172a;" if self.theme == "light" else "color: #f8fafc;")
        self.card_todo_ot.theme = theme
        self.card_todo_ot.update_style()
        self.card_todo_fine.theme = theme
        self.card_todo_fine.update_style()
        self.card_todo_celeb.theme = theme
        self.card_todo_celeb.update_style()
        self.card_todo_new.theme = theme
        self.card_todo_new.update_style()
        self.refresh_data()
