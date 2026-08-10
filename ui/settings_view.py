from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QDateEdit, QAbstractItemView, QCheckBox, QScrollArea)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from database.connection import SessionLocal
from database.models import Setting, HolidayCalendar
from utilities.audit_logger import AuditLogger
from datetime import datetime, date

class SettingsView(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.init_ui()
        self.load_settings()
        self.refresh_holiday_table()

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

        title_lbl = QLabel("System Settings & Policies")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_lbl)

        # Tab Widget for organizational structure
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Rates and Constants Form
        self.tab_rates = QWidget()
        rates_layout = QVBoxLayout(self.tab_rates)
        
        rates_form_frame = QFrame()
        rates_form_frame.setProperty("class", "DashboardCard")
        rates_form_layout = QFormLayout(rates_form_frame)
        rates_form_layout.setSpacing(12)
        
        self.txt_pf_rate = QLineEdit()
        self.txt_esi_rate = QLineEdit()
        self.txt_pt = QLineEdit()
        self.txt_ot_mult = QLineEdit()
        self.txt_off_day_mult = QLineEdit()
        self.txt_half_day_rule = QLineEdit()
        self.txt_late_ded = QLineEdit()
        self.txt_late_thresh = QLineEdit()
        self.txt_working_days = QLineEdit()
        
        rates_form_layout.addRow("Employee Provident Fund (PF) %:", self.txt_pf_rate)
        rates_form_layout.addRow("Employee State Insurance (ESI) %:", self.txt_esi_rate)
        rates_form_layout.addRow("Professional Tax (PT) Flat Payout (INR):", self.txt_pt)
        rates_form_layout.addRow("Overtime Hour Wage Multiplier (e.g. 1.5):", self.txt_ot_mult)
        rates_form_layout.addRow("Off-Day Work Wage Multiplier (e.g. 2.0):", self.txt_off_day_mult)
        rates_form_layout.addRow("Half-day Deduction Weight (e.g. 0.5):", self.txt_half_day_rule)
        rates_form_layout.addRow("Late Coming Penalty (INR per day):", self.txt_late_ded)
        rates_form_layout.addRow("Allowed Late Days Threshold:", self.txt_late_thresh)
        rates_form_layout.addRow("Standard Monthly Working Days (T):", self.txt_working_days)

        rates_layout.addWidget(rates_form_frame)

        self.btn_save_rates = QPushButton("💾 Save Calculation Configurations")
        self.btn_save_rates.setProperty("class", "PrimaryBtn")
        self.btn_save_rates.clicked.connect(self.save_rates_settings)
        rates_layout.addWidget(self.btn_save_rates)
        
        self.tabs.addTab(self.tab_rates, "Calculation Configs")

        # Tab 2: Leave Balance Master Settings
        self.tab_leaves = QWidget()
        leaves_layout = QVBoxLayout(self.tab_leaves)
        
        leaves_frame = QFrame()
        leaves_frame.setProperty("class", "DashboardCard")
        leaves_form_layout = QFormLayout(leaves_frame)
        leaves_form_layout.setSpacing(12)
        
        self.txt_cl = QLineEdit()
        self.txt_sl = QLineEdit()
        self.txt_el = QLineEdit()
        
        leaves_form_layout.addRow("Annual Casual Leave (CL) Balance:", self.txt_cl)
        leaves_form_layout.addRow("Annual Sick Leave (SL) Balance:", self.txt_sl)
        leaves_form_layout.addRow("Annual Earned Leave (EL) Balance:", self.txt_el)
        leaves_layout.addWidget(leaves_frame)

        self.btn_save_leaves = QPushButton("💾 Save Leave Policies")
        self.btn_save_leaves.setProperty("class", "PrimaryBtn")
        self.btn_save_leaves.clicked.connect(self.save_leave_settings)
        leaves_layout.addWidget(self.btn_save_leaves)

        self.tabs.addTab(self.tab_leaves, "Leave Policies")

        # Tab 3: Holiday Calendar
        self.tab_calendar = QWidget()
        cal_layout = QHBoxLayout(self.tab_calendar)
        cal_layout.setSpacing(15)

        # Left List
        list_card = QFrame()
        list_card.setProperty("class", "DashboardCard")
        list_card_layout = QVBoxLayout(list_card)
        list_card_layout.addWidget(QLabel("<b>Holiday Register</b>"))
        
        self.tbl_holidays = QTableWidget()
        self.tbl_holidays.setColumnCount(4)
        self.tbl_holidays.setHorizontalHeaderLabels(["ID", "Date", "Name", "Paid Holiday"])
        self.tbl_holidays.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_holidays.verticalHeader().setDefaultSectionSize(36)
        self.tbl_holidays.verticalHeader().setVisible(False)
        self.tbl_holidays.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_holidays.setEditTriggers(QAbstractItemView.NoEditTriggers)
        list_card_layout.addWidget(self.tbl_holidays)

        self.btn_delete_holiday = QPushButton("🗑️ Remove Holiday")
        self.btn_delete_holiday.setProperty("class", "DangerBtn")
        self.btn_delete_holiday.clicked.connect(self.delete_holiday)
        list_card_layout.addWidget(self.btn_delete_holiday)

        cal_layout.addWidget(list_card, 3)

        # Right Form
        add_card = QFrame()
        add_card.setProperty("class", "DashboardCard")
        add_form_layout = QFormLayout(add_card)
        add_form_layout.setSpacing(10)
        
        add_form_layout.addRow(QLabel("<b>Add New Holiday</b>"))
        
        self.date_holiday = QDateEdit()
        self.date_holiday.setCalendarPopup(True)
        self.date_holiday.setDate(QDate.currentDate())
        add_form_layout.addRow("Holiday Date:", self.date_holiday)

        self.txt_holiday_name = QLineEdit()
        add_form_layout.addRow("Holiday Title:", self.txt_holiday_name)

        self.chk_paid_holiday = QCheckBox("Is Paid Off Day")
        self.chk_paid_holiday.setChecked(True)
        add_form_layout.addRow("", self.chk_paid_holiday)

        self.btn_add_holiday = QPushButton("＋ Add to Calendar")
        self.btn_add_holiday.setProperty("class", "PrimaryBtn")
        self.btn_add_holiday.clicked.connect(self.add_holiday)
        add_form_layout.addRow("", self.btn_add_holiday)

        cal_layout.addWidget(add_card, 2)
        self.tabs.addTab(self.tab_calendar, "Holiday Calendar")
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def load_settings(self):
        db = SessionLocal()
        try:
            settings = {s.setting_key: s.setting_value for s in db.query(Setting).all()}
            
            # Fill inputs
            self.txt_pf_rate.setText(settings.get("pf_rate", "12.0"))
            self.txt_esi_rate.setText(settings.get("esi_rate", "0.75"))
            self.txt_pt.setText(settings.get("prof_tax", "200.0"))
            self.txt_ot_mult.setText(settings.get("overtime_rate_mult", "1.5"))
            self.txt_off_day_mult.setText(settings.get("off_day_rule_mult", "2.0"))
            self.txt_half_day_rule.setText(settings.get("half_day_rule", "0.5"))
            self.txt_late_ded.setText(settings.get("late_coming_deduction", "50.0"))
            self.txt_late_thresh.setText(settings.get("late_coming_threshold", "3"))
            self.txt_working_days.setText(settings.get("working_days", "26"))
            
            # Leave Balances
            self.txt_cl.setText(settings.get("cl_balance", "12"))
            self.txt_sl.setText(settings.get("sl_balance", "10"))
            self.txt_el.setText(settings.get("el_balance", "15"))
        finally:
            db.close()

    def update_setting_key(self, db, key, value):
        s = db.query(Setting).filter(Setting.setting_key == key).first()
        if not s:
            s = Setting(setting_key=key)
            db.add(s)
        s.setting_value = str(value)

    def save_rates_settings(self):
        db = SessionLocal()
        try:
            self.update_setting_key(db, "pf_rate", self.txt_pf_rate.text().strip())
            self.update_setting_key(db, "esi_rate", self.txt_esi_rate.text().strip())
            self.update_setting_key(db, "prof_tax", self.txt_pt.text().strip())
            self.update_setting_key(db, "overtime_rate_mult", self.txt_ot_mult.text().strip())
            self.update_setting_key(db, "off_day_rule_mult", self.txt_off_day_mult.text().strip())
            self.update_setting_key(db, "half_day_rule", self.txt_half_day_rule.text().strip())
            self.update_setting_key(db, "late_coming_deduction", self.txt_late_ded.text().strip())
            self.update_setting_key(db, "late_coming_threshold", self.txt_late_thresh.text().strip())
            self.update_setting_key(db, "working_days", self.txt_working_days.text().strip())
            
            db.commit()
            AuditLogger.log("Calculation Configs Changed", "Updated payroll calculations engine parameter limits.")
            QMessageBox.information(self, "Success", "Calculation configurations updated successfully.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save settings: {e}")
        finally:
            db.close()

    def save_leave_settings(self):
        db = SessionLocal()
        try:
            self.update_setting_key(db, "cl_balance", self.txt_cl.text().strip())
            self.update_setting_key(db, "sl_balance", self.txt_sl.text().strip())
            self.update_setting_key(db, "el_balance", self.txt_el.text().strip())
            
            db.commit()
            AuditLogger.log("Leave Policies Changed", "Modified standard opening balances for leaves.")
            QMessageBox.information(self, "Success", "Leave policies saved successfully.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save leave limits: {e}")
        finally:
            db.close()

    def refresh_holiday_table(self):
        db = SessionLocal()
        try:
            holidays = db.query(HolidayCalendar).order_by(HolidayCalendar.holiday_date).all()
            self.tbl_holidays.setRowCount(len(holidays))
            for i, h in enumerate(holidays):
                self.tbl_holidays.setItem(i, 0, QTableWidgetItem(str(h.id)))
                self.tbl_holidays.setItem(i, 1, QTableWidgetItem(str(h.holiday_date)))
                self.tbl_holidays.setItem(i, 2, QTableWidgetItem(h.name))
                self.tbl_holidays.setItem(i, 3, QTableWidgetItem("Yes" if h.is_paid else "No"))
        finally:
            db.close()

    def add_holiday(self):
        name = self.txt_holiday_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Holiday Title is required.")
            return

        h_date = self.date_holiday.date().toPython()
        is_paid = self.chk_paid_holiday.isChecked()

        db = SessionLocal()
        try:
            # Check date unique
            exists = db.query(HolidayCalendar).filter(HolidayCalendar.holiday_date == h_date).first()
            if exists:
                QMessageBox.critical(self, "Error", "A holiday on this date already exists.")
                return

            holiday = HolidayCalendar(
                holiday_date=h_date,
                name=name,
                is_paid=is_paid
            )
            db.add(holiday)
            db.commit()
            
            AuditLogger.log("Holiday Added", f"Added holiday '{name}' on {h_date}")
            QMessageBox.information(self, "Success", "Holiday added successfully.")
            self.txt_holiday_name.clear()
            self.refresh_holiday_table()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save holiday: {e}")
        finally:
            db.close()

    def delete_holiday(self):
        row = self.tbl_holidays.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a holiday to delete.")
            return

        h_id = int(self.tbl_holidays.item(row, 0).text())
        h_name = self.tbl_holidays.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to remove the holiday '{h_name}' from calendar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            db = SessionLocal()
            try:
                h = db.query(HolidayCalendar).filter(HolidayCalendar.id == h_id).first()
                if h:
                    db.delete(h)
                    db.commit()
                    AuditLogger.log("Holiday Removed", f"Deleted holiday '{h_name}'")
                    QMessageBox.information(self, "Success", "Holiday deleted successfully.")
                    self.refresh_holiday_table()
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to delete: {e}")
            finally:
                db.close()
            self.refresh_holiday_table()
    
    def update_theme(self, theme):
        self.theme = theme
