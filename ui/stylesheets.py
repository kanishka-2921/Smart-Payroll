def get_stylesheet(theme="dark"):
    """
    Returns the QSS stylesheet for the application.
    Modern HRMS theme with rounded cards, smooth hover states, and clear fonts.
    """
    if theme == "dark":
        return """
            /* Dark Mode Theme */
            QMainWindow, QDialog {
                background-color: #121214;
            }
            
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            
            /* Sidebar navigation styling */
            QFrame#SidebarFrame {
                background-color: #1e1e24;
                border-right: 1px solid #2d2d34;
            }
            
            QFrame#ContentFrame {
                background-color: #121214;
            }
            
            /* Base Buttons (e.g. Dialog Buttons) */
            QPushButton {
                background-color: #2a2a35;
                border: 1px solid #3e3e4a;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #353545;
            }

            /* Navigation Buttons */
            QPushButton.NavButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #9ca3af;
                padding: 10px 15px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
            }
            
            QPushButton.NavButton:hover {
                background-color: #2b2b35;
                color: #f3f4f6;
            }
            
            QPushButton.NavButton:checked {
                background-color: #6366f1;
                color: #ffffff;
            }
            
            /* Premium Dashboard Cards */
            QFrame.DashboardCard {
                background-color: #1a1a20;
                border: 1px solid #2d2d35;
                border-radius: 10px;
            }
            
            QFrame.DashboardCard:hover {
                border-color: #6366f1;
                background-color: #202028;
            }
            
            /* Input Widgets */
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #1a1a20;
                border: 1px solid #2e2e38;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f3f4f6;
            }
            
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #6366f1;
                background-color: #202028;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #e2e8f0;
                selection-color: #000000;
            }
            QComboBox::item {
                color: #000000;
            }
            QComboBox::item:selected {
                background-color: #e2e8f0;
                color: #000000;
            }
            
            /* Tables */
            QTableWidget {
                background-color: #1a1a20;
                border: 1px solid #2e2e38;
                border-radius: 8px;
                gridline-color: #2e2e38;
                alternate-background-color: #1f1f26;
                selection-background-color: #2b2b36;
                selection-color: #ffffff;
            }
            
            QTableWidget::item {
                padding: 4px 10px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #2b2b36;
                color: #ffffff;
            }
            
            QHeaderView::section {
                background-color: #22222a;
                color: #cbd5e1;
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid #2e2e38;
                font-weight: bold;
                text-align: center;
            }
            
            /* Dialog Buttons */
            QPushButton.PrimaryBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.PrimaryBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
            }
            
            QPushButton.PrimaryBtn:pressed {
                background-color: #4338ca;
            }
            
            QPushButton.SecondaryBtn {
                background-color: #2a2a35;
                border: 1px solid #3e3e4a;
                border-radius: 6px;
                color: #e2e8f0;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.SecondaryBtn:hover {
                background-color: #353545;
            }
            
            QPushButton.DangerBtn {
                background-color: #ef4444;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.DangerBtn:hover {
                background-color: #dc2626;
            }
            
            /* Tabs */
            QTabBar::tab {
                background-color: #1e1e24;
                color: #9ca3af;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #121214;
                color: #f3f4f6;
                border-bottom: 2px solid #6366f1;
            }
            
            /* Scrollbars */
            QScrollBar:vertical {
                border: none;
                background-color: #1a1a20;
                width: 10px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #2e2e38;
                min-height: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #4f46e5;
            }
        """
    elif theme == "blueish":
        # Blueish Mode Theme
        return """
            QMainWindow, QDialog {
                background-color: #090d16;
            }
            
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            
            /* Sidebar navigation styling */
            QFrame#SidebarFrame {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
            
            QFrame#ContentFrame {
                background-color: #090d16;
            }
            
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #93c5fd;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }

            QPushButton.NavButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #94a3b8;
                padding: 10px 15px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
            }
            
            QPushButton.NavButton:hover {
                background-color: #1e293b;
                color: #f8fafc;
            }
            
            QPushButton.NavButton:checked {
                background-color: #2563eb;
                color: #ffffff;
            }
            
            QFrame.DashboardCard {
                background-color: #131b2e;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            
            QFrame.DashboardCard:hover {
                border-color: #3b82f6;
                background-color: #18223f;
            }
            
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f8fafc;
            }
            
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #3b82f6;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #e2e8f0;
                selection-color: #000000;
            }
            QComboBox::item {
                color: #000000;
            }
            QComboBox::item:selected {
                background-color: #e2e8f0;
                color: #000000;
            }
            
            QTableWidget {
                background-color: #131b2e;
                border: 1px solid #1e293b;
                border-radius: 8px;
                gridline-color: #1e293b;
                alternate-background-color: #0f172a;
                selection-background-color: #1e3a8a;
                selection-color: #ffffff;
            }
            
            QTableWidget::item {
                padding: 6px;
            }
            
            QTableWidget::item:selected {
                background-color: #1e3a8a;
                color: #ffffff;
            }
            
            QHeaderView::section {
                background-color: #1e293b;
                color: #93c5fd;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #1e293b;
                font-weight: bold;
            }
            
            QPushButton.PrimaryBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.PrimaryBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #1e3a8a);
            }
            
            QPushButton.SecondaryBtn {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #93c5fd;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.SecondaryBtn:hover {
                background-color: #334155;
            }
            
            QPushButton.DangerBtn {
                background-color: #ef4444;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.DangerBtn:hover {
                background-color: #dc2626;
            }
            
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #131b2e;
                color: #3b82f6;
                border-bottom: 2px solid #3b82f6;
            }
            
            QScrollBar:vertical {
                border: none;
                background-color: #0f172a;
                width: 10px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #334155;
                min-height: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #3b82f6;
            }
        """
    else:
        # Light Mode Theme
        return """
            QMainWindow, QDialog {
                background-color: #f8fafc;
            }
            
            QWidget {
                color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            
            QFrame#SidebarFrame {
                background-color: #ffffff;
                border-right: 1px solid #e2e8f0;
            }
            
            QFrame#ContentFrame {
                background-color: #f8fafc;
            }
            
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                color: #334155;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }

            QPushButton.NavButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #64748b;
                padding: 10px 15px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
            }
            
            QPushButton.NavButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
            }
            
            QPushButton.NavButton:checked {
                background-color: #4f46e5;
                color: #ffffff;
            }
            
            QFrame.DashboardCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            
            QFrame.DashboardCard:hover {
                border-color: #4f46e5;
                background-color: #fafafa;
            }
            
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 12px;
                color: #0f172a;
            }
            
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #4f46e5;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #e2e8f0;
                selection-color: #000000;
            }
            QComboBox::item {
                color: #000000;
            }
            QComboBox::item:selected {
                background-color: #e2e8f0;
                color: #000000;
            }
            
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #e2e8f0;
                alternate-background-color: #f8fafc;
                selection-background-color: #e0e7ff;
                selection-color: #1e293b;
            }
            
            QTableWidget::item {
                padding: 6px;
            }
            
            QTableWidget::item:selected {
                background-color: #e0e7ff;
                color: #1e293b;
            }
            
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #475569;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: bold;
            }
            
            QPushButton.PrimaryBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.PrimaryBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3730a3, stop:1 #6d28d9);
            }
            
            QPushButton.SecondaryBtn {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                color: #334155;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.SecondaryBtn:hover {
                background-color: #e2e8f0;
            }
            
            QPushButton.DangerBtn {
                background-color: #ef4444;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton.DangerBtn:hover {
                background-color: #dc2626;
            }
            
            QTabBar::tab {
                background-color: #e2e8f0;
                color: #475569;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #f8fafc;
                color: #0f172a;
                border-bottom: 2px solid #4f46e5;
            }
        """
