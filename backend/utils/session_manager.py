import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta
from backend.agents.calendar_agent import AgentState
from backend.models.schemas import ConversationState

class SessionManager:
    def __init__(self, session_timeout_minutes: int = 30):
        self._sessions: Dict[str, AgentState] = {}
        self._session_timestamps: Dict[str, datetime] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "messages": [],
            "conversation_state": ConversationState.GREETING,
            "booking_request": None,
            "suggested_slots": [],
            "user_preferences": {},
            "needs_user_input": True
        }
        self._session_timestamps[session_id] = datetime.now()
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AgentState]:
        if session_id not in self._sessions:
            return None
        
        if self._is_session_expired(session_id):
            self.cleanup_session(session_id)
            return None
        
        self._session_timestamps[session_id] = datetime.now()
        return self._sessions[session_id]
    
    def update_session(self, session_id: str, state: AgentState) -> bool:
        if session_id not in self._sessions:
            return False
        
        self._sessions[session_id] = state
        self._session_timestamps[session_id] = datetime.now()
        return True
    
    def cleanup_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._session_timestamps[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        current_time = datetime.now()
        expired_sessions = [
            session_id for session_id, timestamp in self._session_timestamps.items()
            if current_time - timestamp > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            self.cleanup_session(session_id)
        
        return len(expired_sessions)
    
    def _is_session_expired(self, session_id: str) -> bool:
        if session_id not in self._session_timestamps:
            return True
        
        return datetime.now() - self._session_timestamps[session_id] > self.session_timeout
    
    def get_active_sessions_count(self) -> int:
        self.cleanup_expired_sessions()
        return len(self._sessions)

session_manager = SessionManager() 