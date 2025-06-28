import os
from typing import Optional

class Settings:
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    FRONTEND_HOST: str = os.getenv("FRONTEND_HOST", "0.0.0.0")
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))
    
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_TOKEN_FILE: str = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    GOOGLE_SCOPES: list = ["https://www.googleapis.com/auth/calendar"]
    
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    MAX_CONVERSATION_TURNS: int = int(os.getenv("MAX_CONVERSATION_TURNS", "50"))
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    
    DEFAULT_EVENT_DURATION: int = int(os.getenv("DEFAULT_EVENT_DURATION", "60"))
    WORKING_HOURS_START: str = os.getenv("WORKING_HOURS_START", "09:00")
    WORKING_HOURS_END: str = os.getenv("WORKING_HOURS_END", "17:00")
    CALENDAR_ID: str = os.getenv("CALENDAR_ID", "primary")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate_required_settings(cls) -> list:
        missing = []
        if not cls.DEEPSEEK_API_KEY:
            missing.append("DEEPSEEK_API_KEY")
        if not os.path.exists(cls.GOOGLE_CREDENTIALS_FILE):
            missing.append(f"Google credentials file: {cls.GOOGLE_CREDENTIALS_FILE}")
        return missing

settings = Settings() 