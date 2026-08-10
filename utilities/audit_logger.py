class AuditLogger:
    @staticmethod
    def log(action, details, username):
        print(f"AUDIT LOG: {username} - {action}: {details}")
