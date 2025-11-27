import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment variables from .env (3 levels up)
# ------------------------------------------------------------
dotenv_path = Path(__file__).resolve().parents[2] / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=False)
else:
    sys.exit(f"ERROR: .env file not found at {dotenv_path}")

# ------------------------------------------------------------
# Configuration class
# ------------------------------------------------------------
class Config:
    """Holds all environment variables for the Flask backend."""

    REQUIRED_VARS = [
        "CLIENT_ID",
        "CLIENT_SECRET",
        "REDIRECT_URI",
        "SCOPES",
        "PROJECT_ID",
        "TELEGRAM_TOKEN",
        "GEMINI_KEY",
    ]

    def __init__(self):
        # Load Autodesk / API credentials
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.redirect_uri = os.getenv("REDIRECT_URI")
        self.scopes = os.getenv("SCOPES")
        self.project_id = os.getenv("PROJECT_ID")

        self.gemini_key = os.getenv("GEMINI_KEY")

        # Telegram and app-specific settings
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")

        # Validate required environment variables
        self._validate_env()

    def _validate_env(self):
        """Exit early if any required variable is missing."""
        missing = [var for var in self.REQUIRED_VARS if not os.getenv(var)]
        if missing:
            sys.exit(
                f"ERROR: Missing required environment variables in .env: "
                f"{', '.join(missing)}"
            )

# Singleton instance
config = Config()
