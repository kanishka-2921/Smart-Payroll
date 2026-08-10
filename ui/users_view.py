from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QDialog, QFormLayout, QDialogButtonBox, QCheckBox, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import User
from services.auth_service import AuthService
from utilities.audit_logger import AuditLogger

class UsersView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.refresh_users()

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

        # Header
        header_layout = QGridLayout()
        header_layout.setSpacing(10)
        title_lbl = QLabel("User Management")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header_layout.addWidget(title_lbl, 0, 0)

        self.btn_new = QPushButton("＋ Create User")
        self.btn_new.setProperty("class", "PrimaryBtn")
        self.btn_new.clicked.connect(self.create_user)
        header_layout.addWidget(self.btn_new, 0, 1)

        self.btn_edit = QPushButton("✏️ Edit User")
        self.btn_edit.setProperty("class", "SecondaryBtn")
        self.btn_edit.clicked.connect(self.edit_user)
        header_layout.addWidget(self.btn_edit, 0, 2)

        self.btn_delete = QPushButton("🗑️ Delete User")
        self.btn_delete.setProperty("class", "DangerBtn")
        self.btn_delete.clicked.connect(self.delete_user)
        header_layout.addWidget(self.btn_delete, 0, 3)

        layout.addLayout(header_layout)

        # Table Panel
        table_frame = QFrame()
        table_frame.setProperty("class", "DashboardCard")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(15, 15, 15, 15)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_layout.addWidget(self.table)

        layout.addWidget(table_frame)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def refresh_users(self):
        db = SessionLocal()
        try:
            users = db.query(User).order_by(User.username).all()
            self.table.setRowCount(len(users))
            for i, u in enumerate(users):
                self.table.setItem(i, 0, QTableWidgetItem(str(u.id)))
                self.table.setItem(i, 1, QTableWidgetItem(u.username))
                self.table.setItem(i, 2, QTableWidgetItem(u.role))
                self.table.setItem(i, 3, QTableWidgetItem("Active" if u.is_active else "Inactive"))
        finally:
            db.close()

    def create_user(self):
        dlg = UserDialog(self, theme=self.theme)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_users()

    def edit_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a user to edit.")
            return

        u_id = int(self.table.item(row, 0).text())
        dlg = UserDialog(self, user_id=u_id, theme=self.theme)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_users()

    def delete_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a user to delete.")
            return

        u_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()

        # Prevent self-deletion
        curr = AuthService.get_current_user()
        if curr and curr.id == u_id:
            QMessageBox.critical(self, "Action Failed", "You cannot delete your own logged-in account.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete user '{username}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            db = SessionLocal()
            try:
                u = db.query(User).filter(User.id == u_id).first()
                if u:
                    db.delete(u)
                    db.commit()
                    AuditLogger.log("User Account Deleted", f"Deleted user login account for '{username}'")
                    QMessageBox.information(self, "Success", "User account deleted.")
                    self.refresh_users()
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to delete user: {e}")
            finally:
                db.close()
                
    def update_theme(self, theme):
        self.theme = theme

class UserDialog(QDialog):
    def __init__(self, parent=None, user_id=None, theme="dark"):
        super().__init__(parent)
        self.user_id = user_id
        self.theme = theme
        self.setWindowTitle("Create New User Account" if not user_id else "Edit User Role")
        self.setFixedSize(350, 250)
        self.init_ui()
        if self.user_id:
            self.load_user()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.txt_username = QLineEdit()
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["Administrator", "HR", "Accountant"])
        
        self.chk_active = QCheckBox("Is Active Account")
        self.chk_active.setChecked(True)

        form_layout.addRow("Username:", self.txt_username)
        form_layout.addRow("Password:", self.txt_password)
        form_layout.addRow("Role / Group:", self.cmb_role)
        form_layout.addRow("", self.chk_active)
        
        layout.addLayout(form_layout)

        # Dialog Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.save_user)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def load_user(self):
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.id == self.user_id).first()
            if u:
                self.txt_username.setText(u.username)
                self.txt_username.setEnabled(False) # lock username edits
                self.txt_password.setPlaceholderText("(Leave blank to keep current)")
                self.cmb_role.setCurrentText(u.role)
                self.chk_active.setChecked(u.is_active)
        finally:
            db.close()

    def save_user(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        if not username:
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return

        db = SessionLocal()
        try:
            if self.user_id:
                u = db.query(User).filter(User.id == self.user_id).first()
                if password: # update password if entered
                    u.password_hash = AuthService.hash_password(password)
                u.role = self.cmb_role.currentText()
                u.is_active = self.chk_active.isChecked()
                action = "User Modified"
            else:
                if not password:
                    QMessageBox.warning(self, "Validation Error", "Password is required for new accounts.")
                    return
                # Check duplicate
                dupe = db.query(User).filter(User.username == username).first()
                if dupe:
                    QMessageBox.critical(self, "Duplicate Error", "Username already exists.")
                    return

                u = User(
                    username=username,
                    password_hash=AuthService.hash_password(password),
                    role=self.cmb_role.currentText(),
                    is_active=self.chk_active.isChecked()
                )
                db.add(u)
                action = "User Created"

            db.commit()
            AuditLogger.log(action, f"Processed account change for user '{username}' (Role: {self.cmb_role.currentText()})")
            QMessageBox.information(self, "Success", "User details saved successfully.")
            self.accept()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save user: {e}")
        finally:
            db.close()
