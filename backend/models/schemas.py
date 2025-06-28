from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ConversationState(str, Enum):
    GREETING = "greeting"
    UNDERSTANDING_INTENT = "understanding_intent"
    GATHERING_INFO = "gathering_info"
    CHECKING_AVAILABILITY = "checking_availability"
    SUGGESTING_TIMES = "suggesting_times"
    CONFIRMING_BOOKING = "confirming_booking"
    BOOKING_COMPLETE = "booking_complete"
    ERROR = "error"


class HealthResponse(BaseModel):
    status: str
    message: str

class ChatMessage(BaseModel):
    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_stage: str

class CalendarEvent(BaseModel):
    id: Optional[str] = None
    summary: str
    description: Optional[str] = ""
    start_time: datetime
    end_time: datetime
    attendees: List[str] = Field(default_factory=list)
    status: BookingStatus = BookingStatus.PENDING

class AvailabilityRequest(BaseModel):
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = 60

class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    available: bool = True

class AvailabilityResponse(BaseModel):
    date: str
    slots: List[TimeSlot]

class BookingRequest(BaseModel):
    title: str
    date: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[int] = 60
    description: Optional[str] = ""
    attendees: List[str] = Field(default_factory=list)

class BookingResponse(BaseModel):
    success: bool
    event_id: Optional[str] = None
    message: str

class ConversationContext(BaseModel):
    state: ConversationState = ConversationState.GREETING
    booking_request: Optional[BookingRequest] = None
    suggested_slots: List[TimeSlot] = Field(default_factory=list)
    messages: List[ChatMessage] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    
class AgentResponse(BaseModel):
    message: str
    state: ConversationState
    suggested_slots: Optional[List[Dict[str, Any]]] = None
    booking_confirmed: bool = False
    needs_user_input: bool = True 