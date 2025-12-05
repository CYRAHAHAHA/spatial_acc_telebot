import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment variables from .env (3 levels up)
# ------------------------------------------------------------
dotenv_path = Path(__file__).resolve().parents[2] / ".env"

# Only require .env file for local development
if not os.getenv("RAILWAY_ENVIRONMENT"):
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)
    else:
        sys.exit(f"ERROR: .env file not found at {dotenv_path}")
else:
    # Railway environment - env vars are injected by Railway
    # Still load .env if present (for backwards compatibility)
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)

# ------------------------------------------------------------
# Configuration class
# ------------------------------------------------------------
class Config:
    """Holds all environment variables for the Flask backend."""

    REQUIRED_VARS = [
        "CLIENT_ID",
        "CLIENT_SECRET",
        "SCOPES",
        "PROJECT_ID",
        "TELEGRAM_TOKEN",
        "OPENAI_API_KEY",
    ]

    def __init__(self):
        # Load Autodesk / API credentials
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.scopes = os.getenv("SCOPES")
        self.project_id = os.getenv("PROJECT_ID")
        self.root_id = os.getenv("ROOT_FOLDER_ID")

        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Telegram and app-specific settings
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        
        # Railway-specific environment variables
        self.railway_environment = os.getenv("RAILWAY_ENVIRONMENT")
        self.railway_public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
        self.railway_static_url = os.getenv("RAILWAY_STATIC_URL")
        self.port = int(os.getenv("PORT", 8080))
        
        # Dynamic redirect URI based on environment
        self.redirect_uri = self._get_redirect_uri()

        # Validate required environment variables
        self._validate_env()
    
    def _get_redirect_uri(self) -> str:
        """
        Get OAuth redirect URI dynamically based on environment.
        Prioritizes manually set REDIRECT_URI, then Railway domains, then localhost.
        """
        # 1. Check if explicitly set (highest priority)
        if os.getenv("REDIRECT_URI"):
            return os.getenv("REDIRECT_URI")
        
        # 2. Use Railway public domain if available
        if self.railway_public_domain:
            return f"https://{self.railway_public_domain}/callback"
        
        # 3. Use Railway static URL if available
        if self.railway_static_url:
            return f"{self.railway_static_url}/callback"
        
        # 4. Fallback to localhost for local development
        return "http://localhost:8080/callback"
    
    def is_railway(self) -> bool:
        """Check if running on Railway"""
        return self.railway_environment is not None

    def _validate_env(self):
        """Exit early if any required variable is missing."""
        missing = [var for var in self.REQUIRED_VARS if not os.getenv(var)]
        if missing:
            sys.exit(
                f"ERROR: Missing required environment variables: "
                f"{', '.join(missing)}\n"
                f"Railway environment: {self.is_railway()}"
            )

# Singleton instance
config = Config()
