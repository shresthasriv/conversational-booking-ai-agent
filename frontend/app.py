import streamlit as st
import requests
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Calendar Booking Agent",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "conversation_stage" not in st.session_state:
        st.session_state.conversation_stage = "greeting"

def send_chat_message(message: str) -> Dict:
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "session_id": st.session_state.session_id
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to send message: {str(e)}")
        return None

def get_calendar_events() -> List[Dict]:
    try:
        response = requests.get(f"{API_BASE_URL}/calendar/events", timeout=10)
        response.raise_for_status()
        return response.json().get("events", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch calendar events: {str(e)}")
        return []

def check_availability(date: str) -> List[Dict]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/availability",
            json={"date": date},
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("slots", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to check availability: {str(e)}")
        return []

def main():
    init_session_state()
    
    st.title("📅 Calendar Booking Agent")
    st.markdown("### AI-powered appointment scheduling")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 💬 Chat with the Agent")
        
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        if prompt := st.chat_input("Type your message here..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = send_chat_message(prompt)
                
                if response:
                    assistant_message = response.get("response", "Sorry, I couldn't process that.")
                    st.markdown(assistant_message)
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": assistant_message
                    })
                    
                    st.session_state.session_id = response.get("session_id")
                    st.session_state.conversation_stage = response.get("conversation_stage", "greeting")
    
    with col2:
        st.markdown("#### 📊 Session Info")
        st.info(f"**Stage:** {st.session_state.conversation_stage}")
        if st.session_state.session_id:
            st.success(f"**Session:** {st.session_state.session_id[:8]}...")
        else:
            st.warning("No active session")
        
        if st.button("🔄 New Session"):
            st.session_state.messages = []
            st.session_state.session_id = None
            st.session_state.conversation_stage = "greeting"
            st.rerun()
        
        st.markdown("#### 📅 Quick Actions")
        
        with st.expander("Check Availability"):
            selected_date = st.date_input("Select date")
            if st.button("Check Available Slots"):
                date_str = selected_date.strftime("%Y-%m-%d")
                slots = check_availability(date_str)
                
                if slots:
                    st.success(f"Found {len(slots)} available slots:")
                    for slot in slots[:5]:
                        if slot.get("available", False):
                            start_time = datetime.fromisoformat(slot["start"].replace('Z', '+00:00'))
                            end_time = datetime.fromisoformat(slot["end"].replace('Z', '+00:00'))
                            st.write(f"• {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
                else:
                    st.warning("No available slots found")
        
        with st.expander("Upcoming Events"):
            if st.button("Refresh Events"):
                events = get_calendar_events()
                
                if events:
                    st.success(f"Found {len(events)} upcoming events:")
                    for event in events[:3]:
                        event_time = datetime.fromisoformat(event["start_time"].replace('Z', '+00:00'))
                        st.write(f"**{event['summary']}**")
                        st.write(f"📅 {event_time.strftime('%B %d, %Y at %H:%M')}")
                        st.write("---")
                else:
                    st.info("No upcoming events")
    
    st.markdown("---")
    
    with st.expander("💡 How to use this agent"):
        st.markdown("""
        **Sample conversations:**
        - "I need to schedule a meeting tomorrow at 2 PM"
        - "Book a doctor appointment for next Monday"
        - "Check if I'm free on Friday afternoon"
        - "Schedule a 30-minute call with John next week"
        
        **Features:**
        - Natural language booking
        - Automatic availability checking
        - Calendar integration
        - Smart time suggestions
        """)
    
    with st.expander("🔧 Debug Info"):
        st.json({
            "session_id": st.session_state.session_id,
            "conversation_stage": st.session_state.conversation_stage,
            "message_count": len(st.session_state.messages),
            "api_status": "Connected" if st.session_state.session_id else "Disconnected"
        })

if __name__ == "__main__":
    main() 