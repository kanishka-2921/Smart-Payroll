from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from services.auth_service import AuthService
from utilities.audit_logger import AuditLogger

class LoginView(QDialog):
    login_success = Signal()

    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.setWindowTitle("Smart Payroll System - Login")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.init_ui()

    def init_ui(self):
        # Master Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Brand Header Card
        card = QFrame()
        card.setObjectName("LoginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # Title & Subtitle
        title = QLabel("Smart Payroll")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #6366f1;" if self.theme == "dark" else "color: #4f46e5;")
        
        subtitle = QLabel("Sign in to your workplace account")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #9ca3af;" if self.theme == "dark" else "color: #64748b;")

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)

        # Inputs
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumHeight(40)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("LoginBtn")
        self.login_btn.setProperty("class", "PrimaryBtn")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.clicked.connect(self.handle_login)

        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.login_btn)

        layout.addWidget(card)

        # Add visual shadow to the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        
        # Shortcuts
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please fill in all credentials.")
            return

        # Attempt Authentication
        success = AuthService.authenticate(username, password)
        if success:
            user = AuthService.get_current_user()
            AuditLogger.log("User Logged In", f"User logged in successfully with role {user.role}", username)
            self.login_success.emit()
            self.accept()
        else:
            AuditLogger.log("Login Failed", f"Failed login attempt for username '{username}'", username)
            QMessageBox.critical(self, "Authentication Failed", "Invalid username or password.")
            self.password_input.clear()
            self.password_input.setFocus()
