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
    page_title="TailorTalk Calendar Agent",
    page_icon="📅",
    layout="wide"
)

@st.cache_resource
def get_calendar_agent():
    try:
        return LangGraphCalendarAgent()
    except Exception as e:
        st.error(f"Failed to initialize calendar agent: {e}")
        return None

@st.cache_resource
def get_calendar_service():
    try:
        return GoogleCalendarService()
    except Exception as e:
        st.error(f"Failed to initialize calendar service: {e}")
        return None

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

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
                "response": "Calendar agent is not available.",
                "session_id": st.session_state.session_id
            }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "session_id": st.session_state.session_id
        }

def get_calendar_events(calendar_service) -> List[Dict]:
    try:
        if calendar_service:
            start_time = datetime.now()
            end_time = start_time + timedelta(days=30)
            events = calendar_service.get_calendar_events(start_time, end_time)
            return events
        return []
    except Exception as e:
        st.error(f"Failed to fetch calendar events: {str(e)}")
        return []

def main():
    init_session_state()

    st.title("📅 TailorTalk Calendar Agent")
    
    calendar_agent = get_calendar_agent()
    calendar_service = get_calendar_service()
    
    if not calendar_agent:
        st.error("Calendar agent failed to initialize.")
        st.stop()
    
    if not calendar_service:
        st.error("Calendar service failed to initialize.")
        st.stop()

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Chat")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Type your message..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    response = process_message(prompt, calendar_agent)
                
                assistant_message = response.get("response", "No response")
                st.markdown(assistant_message)
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": assistant_message
                })
                
                st.session_state.session_id = response.get("session_id", st.session_state.session_id)
    
    with col2:
        st.markdown("#### Session")
        st.info(f"ID: {st.session_state.session_id[:8]}...")
        
        if st.button("New Session"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        st.markdown("#### Upcoming Events")
        if st.button("Refresh Events"):
            events = get_calendar_events(calendar_service)
            
            if events:
                st.success(f"Found {len(events)} events")
                for event in events[:5]:
                    try:
                        event_time = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                        st.write(f"**{event['summary']}**")
                        st.write(f"{event_time.strftime('%B %d, %Y at %H:%M')}")
                        st.write("---")
                    except:
                        st.write(f"**{event.get('summary', 'Event')}**")
                        st.write("---")
            else:
                st.info("No upcoming events")

if __name__ == "__main__":
    main() 