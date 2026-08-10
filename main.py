import sys
from PySide6.QtWidgets import QApplication
from database.connection import init_db
from database.seeder import seed_db
from ui.login_view import LoginView
from ui.main_window import MainWindow

def main():
    # 1. Initialize and Seed Database
    init_db()
    seed_db()

    # 2. Launch Qt App
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 3. Secure Login Loop
    login = LoginView()
    if login.exec() == LoginView.Accepted:
        # User is authenticated
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    else:
        # User canceled login
        sys.exit(0)

if __name__ == "__main__":
    main()
