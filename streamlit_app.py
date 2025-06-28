#!/usr/bin/env python3
import streamlit as st
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.agents.langgraph_calendar_agent import LangGraphCalendarAgent
    from backend.services.calendar_service import GoogleCalendarService
    from config.settings import settings
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(
    page_title="TailorTalk Calendar Booking Agent",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_calendar_agent():
    try:
        # Check for service account credentials in secrets
        if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
            credentials_info = dict(st.secrets['google_credentials'])
            return LangGraphCalendarAgent(credentials_info=credentials_info)
        # For local development
        elif os.path.exists('credentials.json'):
            return LangGraphCalendarAgent()
        else:
            st.error("⚠️ **Google Calendar Setup Required for Agent**")
            return None
    except Exception as e:
        st.error(f"Failed to initialize calendar agent: {e}")
        return None

@st.cache_resource
def get_calendar_service():
    try:
        # For Streamlit Cloud, check for service account credentials in secrets
        if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
            credentials_info = dict(st.secrets['google_credentials'])
            return GoogleCalendarService(credentials_info=credentials_info)
        # For local development, try credentials.json file
        elif os.path.exists('credentials.json'):
            return GoogleCalendarService()
        else:
            st.error("⚠️ **Google Calendar Setup Required**")
            st.markdown("""
            **For Streamlit Cloud:**
            1. Add your Google service account credentials to Streamlit secrets
            2. Go to your app settings → Secrets
            3. Add the service account JSON data under `[google_credentials]`
            
            **For Local Development:**
            - Place your `credentials.json` file in the project root
            - This file should NOT be committed to Git
            """)
            return None
    except Exception as e:
        st.error(f"Failed to initialize Google calendar service: {e}")
        if "service account" in str(e).lower():
            st.error("💡 Make sure you've shared your Google Calendar with the service account email!")
        return None

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "conversation_stage" not in st.session_state:
        st.session_state.conversation_stage = "greeting"
    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False

def process_message(message: str, agent) -> Dict:
    try:
        if agent:
            response = agent.process_message(
                message=message,
                session_id=st.session_state.session_id
            )
            return response
        else:
            return {
                "response": "Sorry, the calendar agent is not available right now. Please check your configuration.",
                "session_id": st.session_state.session_id,
                "conversation_stage": "error"
            }
    except Exception as e:
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "session_id": st.session_state.session_id,
            "conversation_stage": "error"
        }

def get_calendar_events(calendar_service) -> List[Dict]:
    try:
        if calendar_service:
            start_time = datetime.now()
            end_time = start_time + timedelta(days=30)
            
            events = calendar_service.get_calendar_events(
                start_time.isoformat(),
                end_time.isoformat()
            )
            return events
        return []
    except Exception as e:
        st.error(f"Failed to fetch calendar events: {str(e)}")
        return []

def check_availability(date: str, calendar_service) -> List[Dict]:
    try:
        if calendar_service:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            available_slots = calendar_service.suggest_time_slots(date_obj, 60)
            return available_slots
        return []
    except Exception as e:
        st.error(f"Failed to check availability: {str(e)}")
        return []

def main():
    init_session_state()

    st.title("📅 TailorTalk Calendar Booking Agent")
    st.markdown("### AI-powered appointment scheduling with natural language")
    
    # Google Calendar integration notice
    st.info("🔗 **Real Google Calendar Integration**: This app connects to your actual Google Calendar using service account authentication.")

    # Initialize services
    calendar_agent = get_calendar_agent()
    calendar_service = get_calendar_service()
    
    if not calendar_agent:
        st.error("❌ Calendar agent failed to initialize. Please check your configuration.")
        
        # Show debug info for troubleshooting
        with st.expander("🔧 Debug Info"):
            try:
                missing_settings = settings.validate_required_settings()
                st.write("Missing settings:", missing_settings)
                st.write("Available secrets:", list(st.secrets.keys()) if hasattr(st, 'secrets') else "No secrets")
                if hasattr(st, 'secrets'):
                    st.write("DEEPSEEK_API_KEY in secrets:", "DEEPSEEK_API_KEY" in st.secrets)
            except Exception as e:
                st.write("Debug error:", str(e))
        
        st.stop()
    
    if not calendar_service:
        st.error("❌ Google calendar service failed to initialize.")
        st.stop()

    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 💬 Chat with the Agent")

        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Type your message here... (e.g., 'I need to schedule a meeting tomorrow at 2 PM')"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = process_message(prompt, calendar_agent)
                
                assistant_message = response.get("response", "Sorry, I couldn't process that.")
                st.markdown(assistant_message)
                
                # Update session state
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": assistant_message
                })
                
                st.session_state.session_id = response.get("session_id", st.session_state.session_id)
                st.session_state.conversation_stage = response.get("conversation_stage", "greeting")
    
    with col2:
        st.markdown("#### 📊 Session Info")
        st.info(f"**Stage:** {st.session_state.conversation_stage}")
        st.success(f"**Session:** {st.session_state.session_id[:8]}...")
        
        if st.button("🔄 New Session"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.conversation_stage = "greeting"
            st.rerun()

        st.markdown("#### 📅 Quick Actions")
        
        with st.expander("Check Availability"):
            selected_date = st.date_input("Select date")
            if st.button("Check Available Slots"):
                date_str = selected_date.strftime("%Y-%m-%d")
                slots = check_availability(date_str, calendar_service)
                
                if slots:
                    st.success(f"Found {len(slots)} available slots:")
                    for slot in slots[:5]:
                        if slot.get("available", False):
                            try:
                                start_time = datetime.fromisoformat(slot["start"].replace('Z', '+00:00'))
                                end_time = datetime.fromisoformat(slot["end"].replace('Z', '+00:00'))
                                st.write(f"• {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
                            except:
                                st.write(f"• {slot}")
                else:
                    st.warning("No available slots found")
        
        with st.expander("Upcoming Events"):
            if st.button("Refresh Events"):
                events = get_calendar_events(calendar_service)
                
                if events:
                    st.success(f"Found {len(events)} upcoming events:")
                    for event in events[:3]:
                        try:
                            event_time = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                            st.write(f"**{event['summary']}**")
                            st.write(f"📅 {event_time.strftime('%B %d, %Y at %H:%M')}")
                            st.write("---")
                        except:
                            st.write(f"**{event.get('summary', 'Event')}**")
                            st.write("---")
                else:
                    st.info("No upcoming events")
        
        # Demo stats
        with st.expander("📈 Calendar Statistics"):
            if calendar_service:
                try:
                    # Get some basic calendar info instead of demo stats
                    st.write("**Calendar Service Status:** ✅ Connected")
                    st.write("**Service Type:** Google Calendar (Real)")
                    st.write("**Authentication:** Service Account")
                except Exception as e:
                    st.write(f"**Status:** ❌ Error - {str(e)}")
            else:
                st.write("**Status:** ❌ Not Connected")

    st.markdown("---")
    
    with st.expander("💡 How to use this agent"):
        st.markdown("""
        **Sample conversations:**
        - "I need to schedule a meeting tomorrow at 2 PM"
        - "Book a doctor appointment for next Monday"
        - "Check if I'm free on Friday afternoon"
        - "Schedule a 30-minute call with John next week"
        
        **Features:**
        - Natural language understanding
        - **Real Google Calendar integration** - creates actual events in your calendar!
        - Automatic availability checking against your real calendar
        - Smart time suggestions based on your schedule
        - Conversational booking flow
        
        **Google Calendar Integration:**
        - Service account authentication (no OAuth popup needed)
        - Real-time availability checking
        - Actual event creation in your Google Calendar
        - Secure server-to-server communication
        """)

if __name__ == "__main__":
    main() 