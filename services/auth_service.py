import hashlib
from database.connection import SessionLocal
from database.models import User

class AuthService:
    _current_user = None

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        # Simple salt to prevent basic rainbow table attacks
        salt = "smart_payroll_salt_2026"
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @classmethod
    def authenticate(cls, username, password) -> bool:
        """Authenticate a user and store session if valid."""
        db = SessionLocal()
        try:
            hashed = cls.hash_password(password)
            user = db.query(User).filter(User.username == username, User.is_active == True).first()
            if user and user.password_hash == hashed:
                cls._current_user = user
                return True
            return False
        finally:
            db.close()

    @classmethod
    def logout(cls):
        """Clear current session."""
        cls._current_user = None

    @classmethod
    def get_current_user(cls) -> User:
        """Get currently logged in user."""
        return cls._current_user

    @classmethod
    def has_role(cls, required_roles) -> bool:
        """Check if logged in user has one of the required roles."""
        if not cls._current_user:
            return False
        if isinstance(required_roles, str):
            return cls._current_user.role == required_roles
        return cls._current_user.role in required_roles
