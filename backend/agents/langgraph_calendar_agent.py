import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from backend.services.calendar_service import GoogleCalendarService
from config.settings import settings
import uuid
import re
import pytz

class ConversationState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    user_intent: str
    booking_details: Optional[Dict[str, Any]]
    available_slots: List[Dict[str, Any]]
    current_step: str
    need_confirmation: bool
    error_message: Optional[str]

class LangGraphCalendarAgent:
    def __init__(self):
        self.llm = ChatDeepSeek(
            api_key=settings.DEEPSEEK_API_KEY,
            model=settings.DEEPSEEK_MODEL,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.calendar_service = GoogleCalendarService()
        self.graph = self._build_graph()
        self.session_states = {}
        self.timezone = pytz.timezone(settings.TIMEZONE)
        
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ConversationState)
        
        workflow.add_node("understand_intent", self.understand_intent)
        workflow.add_node("extract_booking_details", self.extract_booking_details)
        workflow.add_node("check_availability", self.check_availability)
        workflow.add_node("suggest_alternatives", self.suggest_alternatives)
        workflow.add_node("confirm_booking", self.confirm_booking)
        workflow.add_node("create_booking", self.create_booking)
        workflow.add_node("handle_error", self.handle_error)
        workflow.add_node("general_response", self.general_response)
        
        workflow.add_edge(START, "understand_intent")
        
        workflow.add_conditional_edges(
            "understand_intent",
            self.route_based_on_intent,
            {
                "booking_request": "extract_booking_details",
                "availability_check": "check_availability", 
                "general_query": "general_response",
                "confirmation": "create_booking",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "extract_booking_details",
            self.route_after_extraction,
            {
                "check_availability": "check_availability",
                "need_more_info": "general_response",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "check_availability", 
            self.route_after_availability,
            {
                "available": "confirm_booking",
                "unavailable": "suggest_alternatives",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("suggest_alternatives", END)
        
        workflow.add_edge("confirm_booking", END)
        
        workflow.add_edge("create_booking", END)
        workflow.add_edge("general_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def _parse_datetime_with_timezone(self, date_str: str, time_str: str) -> datetime:
        try:
            time_formats = [
                "%H:%M",    
                "%I:%M %p",  
                "%I %p",   
                "%H"         
            ]
            
            parsed_time = None
            for fmt in time_formats:
                try:
                    parsed_time = datetime.strptime(time_str, fmt).time()
                    break
                except ValueError:
                    continue
            
            if not parsed_time:
                time_match = re.search(r'(\d{1,2})\s*(pm|am)', time_str.lower())
                if time_match:
                    hour = int(time_match.group(1))
                    is_pm = time_match.group(2) == 'pm'
                    if is_pm and hour != 12:
                        hour += 12
                    elif not is_pm and hour == 12:
                        hour = 0
                    parsed_time = datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
                else:
                    try:
                        hour = int(time_str.split(':')[0])
                        minute = int(time_str.split(':')[1]) if ':' in time_str else 0
                        parsed_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
                    except:
                        raise ValueError(f"Could not parse time: {time_str}")

            date_formats = ["%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y"]
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not parsed_date:
                raise ValueError(f"Could not parse date: {date_str}")

            naive_dt = datetime.combine(parsed_date, parsed_time)

            return naive_dt
            
        except Exception as e:
            raise ValueError(f"Could not parse datetime '{date_str} {time_str}': {str(e)}")
    
    def understand_intent(self, state: ConversationState) -> ConversationState:
        last_message = state["messages"][-1].content if state["messages"] else ""
        current_step = state.get("current_step", "")

        if current_step == "awaiting_confirmation" or state.get("need_confirmation"):
            confirmation_words = ["yes", "confirm", "go ahead", "create", "book it", "do it", "sure", "okay", "ok", "yep", "yeah"]
            if any(word in last_message.lower() for word in confirmation_words):
                state["user_intent"] = "confirmation"
                state["current_step"] = "intent_understood"
                return state
        
        intent_prompt = f"""
        Analyze this user message and determine their intent:
        Message: "{last_message}"
        
        Possible intents:
        - booking_request: User wants to schedule/book something
        - availability_check: User wants to check if a time is free
        - confirmation: User is confirming/accepting a previous suggestion
        - general_query: General question or greeting
        
        Respond with just the intent name.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=intent_prompt)])
            intent = response.content.strip().lower()

            if any(word in last_message.lower() for word in ["book", "schedule", "meeting", "appointment"]):
                intent = "booking_request"
            elif any(word in last_message.lower() for word in ["available", "free", "check"]):
                intent = "availability_check"
            
            state["user_intent"] = intent
            state["current_step"] = "intent_understood"
            
        except Exception as e:
            state["user_intent"] = "error"
            state["error_message"] = f"Intent analysis failed: {str(e)}"
            
        return state
    
    def extract_booking_details(self, state: ConversationState) -> ConversationState:
        last_message = state["messages"][-1].content if state["messages"] else ""
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        extraction_prompt = f"""
        Extract booking details from this message:
        "{last_message}"
        
        Current date: {current_date}, Current time: {current_time}
        Tomorrow's date: {tomorrow}
        
        Extract and return JSON with these fields:
        {{
            "title": "meeting title or description (default: 'Meeting')",
            "date": "YYYY-MM-DD format",
            "time": "HH:MM format (24-hour)", 
            "duration": minutes as integer (default: 60),
            "attendees": ["email1", "email2"],
            "description": "additional details"
        }}
        
        For relative dates:
        - today = {current_date}
        - tomorrow = {tomorrow}
        
        For times like "2pm", "4pm" convert to 24-hour format (14:00, 16:00).
        
        If information is missing, set fields to null except title and duration which have defaults.
        Return only valid JSON.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=extraction_prompt)])
            
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                booking_details = json.loads(json_match.group())

                if not booking_details.get("title"):
                    booking_details["title"] = "Meeting"
                if not booking_details.get("duration"):
                    booking_details["duration"] = 60
                
                state["booking_details"] = booking_details
                state["current_step"] = "details_extracted"
            else:
                state["current_step"] = "extraction_failed"
                state["error_message"] = "Could not extract booking details"
                
        except Exception as e:
            state["current_step"] = "extraction_failed"
            state["error_message"] = f"Detail extraction failed: {str(e)}"
            
        return state
    
    def check_availability(self, state: ConversationState) -> ConversationState:
        booking_details = state.get("booking_details", {})
        
        if not booking_details or not booking_details.get("date") or not booking_details.get("time"):
            state["current_step"] = "availability_check_failed"
            state["error_message"] = "Missing date or time information"
            return state
        
        try:
            date_str = booking_details["date"]
            time_str = booking_details["time"]
            duration = booking_details.get("duration", 60)
            
            if duration is None or not isinstance(duration, (int, float)):
                duration = 60
            duration = int(duration)
            
            start_datetime = self._parse_datetime_with_timezone(date_str, time_str)
            end_datetime = start_datetime + timedelta(minutes=duration)
            
            is_available = self.calendar_service.check_availability(start_datetime, end_datetime)
            
            if is_available:
                state["current_step"] = "time_available"
            else:
                state["current_step"] = "time_unavailable"
                alternative_slots = self.calendar_service.suggest_time_slots(
                    start_datetime, duration
                )
                state["available_slots"] = alternative_slots[:3]
                
        except Exception as e:
            state["current_step"] = "availability_check_failed"
            state["error_message"] = f"Availability check failed: {str(e)}"
            
        return state
    
    def suggest_alternatives(self, state: ConversationState) -> ConversationState:
        available_slots = state.get("available_slots", [])
        
        if available_slots:
            slot_suggestions = []
            for i, slot in enumerate(available_slots, 1):
                start_time = slot['start'].strftime('%I:%M %p')
                end_time = slot['end'].strftime('%I:%M %p')
                slot_suggestions.append(f"{i}. {start_time} - {end_time}")
            
            response_text = f"That time isn't available. Here are some alternatives:\n\n" + "\n".join(slot_suggestions) + "\n\nWhich option works for you?"
        else:
            response_text = "Unfortunately, I couldn't find any available slots. Could you suggest a different day or time?"
        
        ai_message = AIMessage(content=response_text)
        state["messages"].append(ai_message)
        state["current_step"] = "alternatives_suggested"
        
        return state
    
    def confirm_booking(self, state: ConversationState) -> ConversationState:
        booking_details = state.get("booking_details", {})
        
        if not booking_details:
            state["current_step"] = "confirmation_failed"
            return state
        
        title = booking_details.get("title", "Meeting")
        date = booking_details.get("date", "")
        time = booking_details.get("time", "")
        duration = booking_details.get("duration", 60)
        
        try:
            start_datetime = self._parse_datetime_with_timezone(date, time)
            end_datetime = start_datetime + timedelta(minutes=duration)
            
            formatted_date = start_datetime.strftime("%A, %B %d, %Y")
            formatted_start_time = start_datetime.strftime("%I:%M %p")
            formatted_end_time = end_datetime.strftime("%I:%M %p")
        except Exception as e:
            try:
                formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                formatted_start_time = datetime.strptime(time, "%H:%M").strftime("%I:%M %p")
                formatted_end_time = f"({duration} minutes)"
            except:
                formatted_date = date
                formatted_start_time = time
                formatted_end_time = f"({duration} minutes)"
        
        confirmation_text = f"""I can schedule this for you:

📅 **{title}**
🗓️ {formatted_date}
🕐 {formatted_start_time} - {formatted_end_time}

Should I go ahead and create this event? (Type 'yes' to confirm)"""
        
        ai_message = AIMessage(content=confirmation_text)
        state["messages"].append(ai_message)
        state["need_confirmation"] = True
        state["current_step"] = "awaiting_confirmation"
        
        return state
    
    def create_booking(self, state: ConversationState) -> ConversationState:
        booking_details = state.get("booking_details", {})
        
        if not booking_details:
            state["current_step"] = "booking_failed"
            state["error_message"] = "No booking details available"
            return state
        
        try:
            date_str = booking_details.get("date")
            time_str = booking_details.get("time")
            duration = booking_details.get("duration", 60)
            title = booking_details.get("title", "New Meeting")
            description = booking_details.get("description", "")
            attendees = booking_details.get("attendees", [])
            
            if not date_str or not time_str:
                state["current_step"] = "booking_failed"
                state["error_message"] = "Missing date or time information"
                return state
            
            if duration is None or not isinstance(duration, (int, float)):
                duration = 60
            duration = int(duration)
            
            start_datetime = self._parse_datetime_with_timezone(date_str, time_str)
            end_datetime = start_datetime + timedelta(minutes=duration)

            is_available = self.calendar_service.check_availability(start_datetime, end_datetime)
            
            if not is_available:
                existing_events = self.calendar_service.get_calendar_events(start_datetime, end_datetime)
                conflict_info = ""
                if existing_events:
                    event = existing_events[0]
                    event_title = event.get('summary', 'Untitled Event')
                    conflict_info = f" There's already an event '{event_title}' scheduled at this time."
                
                error_text = f"""❌ **Cannot Create Event**

The requested time slot is no longer available.{conflict_info}

📅 **Requested:** {title}
🗓️ {start_datetime.strftime('%A, %B %d, %Y')}
🕐 {start_datetime.strftime('%I:%M %p')} - {end_datetime.strftime('%I:%M %p')}

Would you like me to suggest alternative times?"""
                
                ai_message = AIMessage(content=error_text)
                state["messages"].append(ai_message)
                state["current_step"] = "booking_failed_conflict"
                state["need_confirmation"] = False
                return state
            
            event_id = self.calendar_service.create_event(
                title=title,
                start_time=start_datetime,
                end_time=end_datetime,
                description=description
            )
            
            if event_id:
                success_text = f"""✅ **Event Created Successfully!**

📅 **{title}**
🗓️ {start_datetime.strftime('%A, %B %d, %Y')}
🕐 {start_datetime.strftime('%I:%M %p')} - {end_datetime.strftime('%I:%M %p')}
🆔 Event ID: {event_id}

Your calendar has been updated!"""
                
                ai_message = AIMessage(content=success_text)
                state["messages"].append(ai_message)
                state["current_step"] = "booking_complete"
                state["need_confirmation"] = False
            else:
                raise Exception("Event creation failed - no event ID returned")
                
        except Exception as e:
            state["current_step"] = "booking_failed"
            state["error_message"] = f"Failed to create event: {str(e)}"
            
        return state
    
    def general_response(self, state: ConversationState) -> ConversationState:
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        general_prompt = f"""
        You are a helpful calendar booking assistant. Respond naturally to this message:
        "{last_message}"
        
        Keep responses conversational and helpful. If they seem to want to book something,
        ask for the details you need (what, when, how long).
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=general_prompt)])
            ai_message = AIMessage(content=response.content)
            state["messages"].append(ai_message)
            state["current_step"] = "general_response_complete"
            
        except Exception as e:
            state["current_step"] = "general_response_failed"
            state["error_message"] = f"General response failed: {str(e)}"
            
        return state
    
    def handle_error(self, state: ConversationState) -> ConversationState:
        error_msg = state.get("error_message", "An unknown error occurred")
        
        error_response = f"I'm sorry, I encountered an issue: {error_msg}. Let's try again. What would you like to schedule?"
        
        ai_message = AIMessage(content=error_response)
        state["messages"].append(ai_message)
        state["current_step"] = "error_handled"
        
        return state
    
    def route_based_on_intent(self, state: ConversationState) -> str:
        intent = state.get("user_intent", "general_query")
        if intent in ["booking_request", "availability_check", "general_query", "confirmation"]:
            return intent
        return "error"
    
    def route_after_extraction(self, state: ConversationState) -> str:
        current_step = state.get("current_step", "")
        if current_step == "details_extracted":
            booking_details = state.get("booking_details", {})
            if booking_details.get("date") and booking_details.get("time"):
                return "check_availability"
            else:
                return "need_more_info"
        return "error"
    
    def route_after_availability(self, state: ConversationState) -> str:
        current_step = state.get("current_step", "")
        if current_step == "time_available":
            return "available"
        elif current_step == "time_unavailable":
            return "unavailable"
        return "error"
    
    def process_message(self, message: str, session_id: str = None) -> Dict[str, Any]:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if session_id in self.session_states:
            current_state = self.session_states[session_id].copy()
            current_state["messages"].append(HumanMessage(content=message))
        else:
            current_state = ConversationState(
                messages=[HumanMessage(content=message)],
                session_id=session_id,
                user_intent="",
                booking_details=None,
                available_slots=[],
                current_step="start",
                need_confirmation=False,
                error_message=None
            )
        
        try:
            final_state = self.graph.invoke(current_state)
            
            self.session_states[session_id] = final_state
            
            ai_messages = [msg for msg in final_state["messages"] if isinstance(msg, AIMessage)]
            response_text = ai_messages[-1].content if ai_messages else "I'm here to help you schedule appointments. What would you like to book?"
            
            return {
                "response": response_text,
                "session_id": session_id,
                "conversation_stage": final_state.get("current_step", "unknown"),
                "suggested_slots": final_state.get("available_slots", []),
                "need_user_input": final_state.get("need_confirmation", True),
                "booking_request": final_state.get("booking_details")
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error processing your request: {str(e)}. Please try again.",
                "session_id": session_id,
                "conversation_stage": "error",
                "suggested_slots": [],
                "need_user_input": True,
                "booking_request": None
            } 