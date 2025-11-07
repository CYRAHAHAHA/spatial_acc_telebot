import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Ensure .env is discovered even when running from nested folders
dotenv_path = find_dotenv(usecwd=True)
if not dotenv_path:
    # Fallback to repo root (two levels up from this file)
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=dotenv_path, override=False)

class Config:
    """Holds all user-specific environment variables."""
    def __init__(self, user="YR"):
        self.user = user
        self.client_id = os.getenv(f"{user}_CLIENT_ID")
        self.client_secret = os.getenv(f"{user}_CLIENT_SECRET")
        self.redirect_uri = os.getenv(f"{user}_REDIRECT_URI")
        self.scopes = os.getenv(f"{user}_SCOPES")
        self.project_id = os.getenv(f"{user}_PROJECT_ID")

    def switch_user(self, user):
        """Switch to a different user's credentials."""
        self.__init__(user)

# Singleton instance
config = Config()
