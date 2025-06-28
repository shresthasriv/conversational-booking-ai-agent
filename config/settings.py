import os
from typing import Optional

class Settings:
    def __init__(self):
        try:
            import streamlit as st
            if hasattr(st, 'secrets'):
                self.DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY"))
                self.CALENDAR_ID = st.secrets.get("CALENDAR_ID", os.getenv("CALENDAR_ID", "primary"))
                self.TIMEZONE = st.secrets.get("TIMEZONE", os.getenv("TIMEZONE", "Asia/Kolkata"))
            else:
                raise ImportError("No secrets available")
        except (ImportError, Exception):
            self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
            self.CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")
            self.TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

        self.API_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        self.FRONTEND_HOST = os.getenv("FRONTEND_HOST", "0.0.0.0")
        self.FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8501"))
        
        self.GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
        
        self.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        self.MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "50"))
        self.SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        
        self.DEFAULT_EVENT_DURATION = int(os.getenv("DEFAULT_EVENT_DURATION", "60"))
        self.WORKING_HOURS_START = os.getenv("WORKING_HOURS_START", "09:00")
        self.WORKING_HOURS_END = os.getenv("WORKING_HOURS_END", "17:00")
        
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    def validate_required_settings(self) -> list:
        missing = []
        if not self.DEEPSEEK_API_KEY:
            missing.append("DEEPSEEK_API_KEY")
        return missing

settings = Settings() 