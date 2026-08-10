import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMessageBox, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QAbstractItemView, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from utilities.backup_manager import BackupManager
from utilities.audit_logger import AuditLogger
from datetime import datetime

class BackupView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.refresh_backups()

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

        title_lbl = QLabel("Database Backup & Restore")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_lbl)

        # Actions Card
        actions_card = QFrame()
        actions_card.setProperty("class", "DashboardCard")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(15, 15, 15, 15)
        
        self.btn_backup = QPushButton("💾 Run Manual Backup Now")
        self.btn_backup.setProperty("class", "PrimaryBtn")
        self.btn_backup.clicked.connect(self.run_backup)
        actions_layout.addWidget(self.btn_backup)
        
        actions_layout.addStretch(1)
        layout.addWidget(actions_card)

        # Backups list card
        list_card = QFrame()
        list_card.setProperty("class", "DashboardCard")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(15, 15, 15, 15)
        list_layout.addWidget(QLabel("<b>Backup Files Register</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Backup Date", "Size (KB)", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        list_layout.addWidget(self.table)

        layout.addWidget(list_card)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def refresh_backups(self):
        backups = BackupManager.list_backups()
        self.table.setRowCount(len(backups))
        
        for i, filepath in enumerate(backups):
            filename = os.path.basename(filepath)
            
            # Date
            mtime = os.path.getmtime(filepath)
            backup_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Size
            size_kb = os.path.getsize(filepath) / 1024.0
            
            self.table.setItem(i, 0, QTableWidgetItem(filename))
            self.table.setItem(i, 1, QTableWidgetItem(backup_date))
            self.table.setItem(i, 2, QTableWidgetItem(f"{size_kb:.1f} KB"))
            
            # Action: Restore
            btn_restore = QPushButton("Restore")
            btn_restore.setProperty("class", "SecondaryBtn")
            btn_restore.clicked.connect(lambda checked=False, path=filepath: self.restore_backup(path))
            self.table.setCellWidget(i, 3, btn_restore)

    def run_backup(self):
        try:
            path = BackupManager.create_backup("manual")
            QMessageBox.information(
                self, "Backup Success",
                f"Manual backup executed successfully!\nFile: {os.path.basename(path)}"
            )
            self.refresh_backups()
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", f"Database backup failed:\n{e}")

    def restore_backup(self, filepath):
        reply = QMessageBox.question(
            self, "Confirm Restore", 
            f"Are you sure you want to restore the database from:\n{os.path.basename(filepath)}?\n\n"
            "Warning: All changes made after this backup date will be overwritten.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                BackupManager.restore_backup(filepath)
                QMessageBox.information(
                    self, "Restore Success",
                    "Database restored successfully!\n"
                    "It is recommended to restart the application to reflect the changes correctly."
                )
                self.refresh_backups()
            except Exception as e:
                QMessageBox.critical(self, "Restore Failed", f"Database restore failed:\n{e}")
                
    def update_theme(self, theme):
        self.theme = theme
