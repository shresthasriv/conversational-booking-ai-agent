from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
from backend.agents.langgraph_calendar_agent import LangGraphCalendarAgent
from backend.models.schemas import BookingRequest
from config.settings import settings
import os

app = FastAPI(
    title="TailorTalk Calendar Booking Agent",
    description="AI-powered calendar booking assistant",
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
active_sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_stage: Optional[str] = None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        response = calendar_agent.process_message(
            message=request.message,
            session_id=session_id
        )
        
        return ChatResponse(
            response=response.get("response", "No response"),
            session_id=response.get("session_id", session_id),
            conversation_stage=response.get("conversation_stage")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/calendar/events")
async def get_upcoming_events():
    try:
        start_time = datetime.now()
        end_time = start_time + timedelta(days=30)
        
        events = calendar_agent.calendar_service.get_calendar_events(start_time, end_time)
        
        return {
            "events": events,
            "count": len(events),
            "period": f"{start_time.date()} to {end_time.date()}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")

@app.post("/calendar/book")
async def book_appointment(booking: BookingRequest):
    try:
        session_id = str(uuid.uuid4())
        
        message = f"Book {booking.title} on {booking.date} at {booking.time}"
        if booking.duration:
            message += f" for {booking.duration} minutes"
        if booking.description:
            message += f". {booking.description}"
        
        response = calendar_agent.process_message(
            message=message,
            session_id=session_id
        )
        
        return {
            "booking_id": session_id,
            "status": "processed",
            "response": response.get("response", "Booking processed"),
            "session_id": response.get("session_id", session_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")

@app.get("/calendar/availability/{date}")
async def check_availability(date: str, duration: int = 60):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        slots = calendar_agent.calendar_service.suggest_time_slots(date_obj, duration)
        
        return {
            "date": date,
            "duration": duration,
            "available_slots": slots,
            "count": len(slots)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "TailorTalk Calendar Agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT) 