from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
from backend.agents.langgraph_calendar_agent import LangGraphCalendarAgent
from backend.services.calendar_service import GoogleCalendarService
from backend.models.schemas import BookingRequest, TimeSlot, ChatMessage
from config.settings import settings
import os

app = FastAPI(
    title="TailorTalk Calendar Booking Agent",
    description="AI-powered calendar booking assistant with natural language processing using LangGraph",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

calendar_agent = LangGraphCalendarAgent()
calendar_service = GoogleCalendarService()
active_sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class AvailabilityRequest(BaseModel):
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: int = 60

class BookingCreateRequest(BaseModel):
    title: str
    date: str
    time: str
    duration: int = 60
    description: str = ""
    attendees: List[str] = []

@app.get("/health")
async def health_check():
    missing_settings = settings.validate_required_settings()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "missing_settings": missing_settings,
        "services": {
            "calendar": "available",
            "agent": "available",
            "deepseek": "available" if settings.DEEPSEEK_API_KEY else "missing_api_key"
        }
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to TailorTalk Calendar Booking Agent API",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = calendar_agent.process_message(
            message=request.message,
            session_id=request.session_id
        )
        
        session_id = response["session_id"]
        active_sessions[session_id] = {
            "last_activity": datetime.now(),
            "conversation_stage": response["conversation_stage"],
            "booking_request": response.get("booking_request")
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.post("/availability")
async def check_availability(request: AvailabilityRequest):
    try:
        if request.start_time and request.end_time:
            is_available = calendar_service.check_availability(
                request.date,
                request.start_time,
                request.duration_minutes
            )
            
            return {
                "date": request.date,
                "available": is_available,
                "checked_time": f"{request.start_time} - {request.end_time}"
            }
        else:
            available_slots = calendar_service.suggest_time_slots(
                request.date,
                request.duration_minutes
            )
            
            return {
                "date": request.date,
                "slots": available_slots,
                "total_slots": len(available_slots)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(e)}")

@app.post("/book")
async def create_booking(request: BookingCreateRequest):
    try:
        event = calendar_service.create_event(
            title=request.title,
            date=request.date,
            time=request.time,
            duration=request.duration,
            description=request.description,
            attendees=request.attendees
        )
        
        return {
            "success": True,
            "event_id": event.get("id"),
            "message": "Event created successfully",
            "event_details": {
                "title": request.title,
                "date": request.date,
                "time": request.time,
                "duration": request.duration
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Booking creation failed: {str(e)}")

@app.get("/calendar/events")
async def get_upcoming_events():
    try:
        start_time = datetime.now()
        end_time = start_time + timedelta(days=30)
        
        events = calendar_service.get_calendar_events(
            start_time.isoformat(),
            end_time.isoformat()
        )
        
        return {
            "events": events,
            "count": len(events),
            "period": f"{start_time.date()} to {end_time.date()}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")

@app.get("/sessions/active")
async def get_active_sessions():
    current_time = datetime.now()
    timeout_minutes = settings.SESSION_TIMEOUT_MINUTES
    
    active_count = 0
    expired_sessions = []
    
    for session_id, session_data in active_sessions.items():
        last_activity = session_data["last_activity"]
        if (current_time - last_activity).total_seconds() > (timeout_minutes * 60):
            expired_sessions.append(session_id)
        else:
            active_count += 1
    
    for session_id in expired_sessions:
        del active_sessions[session_id]
    
    return {
        "active_sessions": active_count,
        "expired_sessions": len(expired_sessions),
        "timeout_minutes": timeout_minutes
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/settings/validate")
async def validate_settings():
    missing = settings.validate_required_settings()
    
    return {
        "valid": len(missing) == 0,
        "missing_settings": missing,
        "google_credentials_exists": os.path.exists(settings.GOOGLE_CREDENTIALS_FILE),
        "deepseek_api_configured": bool(settings.DEEPSEEK_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 