from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QStackedWidget, QFrame, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from ui.stylesheets import get_stylesheet
from services.auth_service import AuthService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = "dark"
        self.setWindowTitle("Smart Payroll System")
        self.resize(1200, 800)
        
        # Tracks buttons for stylesheet state
        self.nav_buttons = {}
        
        # Init UI structure
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        # Master Widget & Layout
        master_widget = QWidget()
        self.setCentralWidget(master_widget)
        master_layout = QHBoxLayout(master_widget)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        # 1. Sidebar Frame
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 15)
        sidebar_layout.setSpacing(8)

        # Header/Brand Label
        brand_label = QLabel("Payroll Hub")
        brand_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        brand_label.setStyleSheet("color: #6366f1; margin-bottom: 20px;")
        brand_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(brand_label)

        # Profile/Role indicator
        user = AuthService.get_current_user()
        username = user.username if user else "guest"
        role = user.role if user else "Guest"
        
        profile_frame = QFrame()
        profile_frame.setStyleSheet("background-color: #2b2b35; border-radius: 6px; margin-bottom: 15px;" if self.theme == "dark" else "background-color: #f1f5f9; border-radius: 6px; margin-bottom: 15px;")
        profile_layout = QVBoxLayout(profile_frame)
        profile_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_username = QLabel(f"👤 {username.capitalize()}")
        lbl_username.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_role = QLabel(f"Role: {role}")
        lbl_role.setFont(QFont("Segoe UI", 9))
        lbl_role.setStyleSheet("color: #9ca3af;" if self.theme == "dark" else "color: #475569;")
        
        profile_layout.addWidget(lbl_username)
        profile_layout.addWidget(lbl_role)
        sidebar_layout.addWidget(profile_frame)

        # Scroll area for navigation links
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.nav_layout = QVBoxLayout(scroll_content)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(4)
        
        # Navigation tabs list (Role Permissions mapping)
        # TabName: (Index, AllowedRoles)
        self.tabs_meta = {
            "Dashboard": (0, ["Administrator", "HR", "Accountant"]),
            "Employee Master": (1, ["Administrator", "HR"]),
            "Attendance": (2, ["Administrator", "HR"]),
            "Payroll": (3, ["Administrator", "HR", "Accountant"]),
            "Leave": (4, ["Administrator", "HR"]),
            "Bonus": (5, ["Administrator", "HR"]),
            "Advance": (6, ["Administrator", "Accountant"]),
            "Reports": (8, ["Administrator", "Accountant"]),
            "Salary Slip": (9, ["Administrator", "Accountant"]),
            "Payroll Register": (10, ["Administrator", "Accountant"]),
            "Settings": (11, ["Administrator", "HR"]),
            "Backup": (12, ["Administrator", "HR"]),
            "Users": (13, ["Administrator"])
        }

        # Build Sidebar Navigation Buttons
        for name, (idx, allowed_roles) in self.tabs_meta.items():
            if role in allowed_roles:
                btn = QPushButton(name)
                btn.setCheckable(True)
                btn.setProperty("class", "NavButton")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked=False, index=idx, button=btn: self.switch_view(index, button))
                self.nav_layout.addWidget(btn)
                self.nav_buttons[idx] = btn

        self.nav_layout.addStretch()
        scroll.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll)

        # Theme toggle and Logout Buttons
        sidebar_layout.addSpacing(10)
        
        self.theme_btn = QPushButton("🌓 Toggle Theme")
        self.theme_btn.setProperty("class", "SecondaryBtn")
        self.theme_btn.setMinimumHeight(42)
        self.theme_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        self.logout_btn = QPushButton("🚪 Logout")
        self.logout_btn.setObjectName("LogoutBtn")
        self.logout_btn.setProperty("class", "DangerBtn")
        self.logout_btn.setMinimumHeight(42)
        self.logout_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.logout_btn)

        master_layout.addWidget(sidebar)

        # 2. Content Stack
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentFrame")
        
        # Import all views
        from ui.dashboard_view import DashboardView
        from ui.employee_view import EmployeeView
        from ui.attendance_view import AttendanceView
        from ui.payroll_view import PayrollView
        from ui.leave_view import LeaveView
        from ui.bonus_view import BonusView
        from ui.advance_view import AdvanceView
        from ui.loan_view import LoanView
        from ui.report_view import ReportView
        from ui.salary_slip_view import SalarySlipView
        from ui.register_view import RegisterView
        from ui.settings_view import SettingsView
        from ui.backup_view import BackupView
        from ui.users_view import UsersView

        # Create dict of view classes by index
        views_map = {
            0: DashboardView,
            1: EmployeeView,
            2: AttendanceView,
            3: PayrollView,
            4: LeaveView,
            5: BonusView,
            6: AdvanceView,
            7: LoanView,
            8: ReportView,
            9: SalarySlipView,
            10: RegisterView,
            11: SettingsView,
            12: BackupView,
            13: UsersView
        }
        
        # Instantiate and add to stack in order
        for idx in range(14):
            view_class = views_map[idx]
            view_widget = view_class(theme=self.theme)
            if idx == 0:
                view_widget.tab_redirect_requested.connect(self.handle_dashboard_redirect)
            self.content_stack.addWidget(view_widget)
        
        # Add a wrapper padding widget around Content Stack for clean spacing
        content_wrapper = QWidget()
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(20, 20, 20, 20)
        content_wrapper_layout.addWidget(self.content_stack)
        
        master_layout.addWidget(content_wrapper, 1)

        # Select first available view
        if self.nav_buttons:
            first_idx = min(self.nav_buttons.keys())
            self.switch_view(first_idx, self.nav_buttons[first_idx])

    def switch_view(self, index, active_btn):
        # Update styling
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        active_btn.setChecked(True)
        
        # Set stack page index
        self.content_stack.setCurrentIndex(index)
        
        # Auto refresh active view data
        widget = self.content_stack.widget(index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

    def toggle_theme(self):
        if self.theme == "dark":
            self.theme = "light"
            self.theme_btn.setText("☀️ Light Theme")
        elif self.theme == "light":
            self.theme = "blueish"
            self.theme_btn.setText("🌊 Blueish Theme")
        else:
            self.theme = "dark"
            self.theme_btn.setText("🌓 Dark Theme")
        self.apply_theme()

    def apply_theme(self):
        sheet = get_stylesheet(self.theme)
        self.setStyleSheet(sheet)
        # Notify views if necessary
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if hasattr(widget, "update_theme"):
                widget.update_theme(self.theme)

    def handle_dashboard_redirect(self, target):
        if target == "attendance" and 2 in self.nav_buttons:
            self.switch_view(2, self.nav_buttons[2])
        elif target == "employees" and 1 in self.nav_buttons:
            self.switch_view(1, self.nav_buttons[1])

    def handle_logout(self):
        AuthService.logout()
        self.close()
