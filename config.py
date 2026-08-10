import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database configuration
DATABASE_FILE = os.path.join(BASE_DIR, "payroll.db")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")

if SUPABASE_DB_URL:
    DATABASE_URI = SUPABASE_DB_URL
    # Ensure URI uses postgresql+psycopg2 scheme for SQLAlchemy compatibility
    if DATABASE_URI.startswith("postgres://"):
        DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URI.startswith("postgresql://"):
        DATABASE_URI = DATABASE_URI.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URI = f"sqlite:///{DATABASE_FILE}"

# Directories for backups, uploads (photos), reports, and logs
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports_output")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure folders exist
for folder in [BACKUP_DIR, UPLOAD_DIR, REPORTS_DIR, LOGS_DIR]:
    os.makedirs(folder, exist_ok=True)

# User Roles
ROLES = ["Administrator", "HR", "Accountant"]

# Theme definitions
COLORS = {
    "dark": {
        "bg_primary": "#121214",
        "bg_panel": "#1a1a20",
        "bg_card": "#22222a",
        "accent_indigo": "#6366f1",
        "accent_purple": "#8b5cf6",
        "accent_emerald": "#10b981",
        "accent_rose": "#f43f5e",
        "accent_amber": "#f59e0b",
        "text_primary": "#f3f4f6",
        "text_secondary": "#9ca3af",
        "border_color": "#2e2e38"
    },
    "light": {
        "bg_primary": "#f8fafc",
        "bg_panel": "#ffffff",
        "bg_card": "#f1f5f9",
        "accent_indigo": "#4f46e5",
        "accent_purple": "#7c3aed",
        "accent_emerald": "#059669",
        "accent_rose": "#e11d48",
        "accent_amber": "#d97706",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "border_color": "#e2e8f0"
    }
}
