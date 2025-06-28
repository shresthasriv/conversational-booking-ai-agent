import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

class ChatInterface:
    def __init__(self, api_client):
        self.api_client = api_client
    
    def render_message_history(self, messages: List[Dict]):
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(f"🕐 {message['timestamp']}")
    
    def render_conversation_status(self, stage: str, session_id: Optional[str]):
        status_colors = {
            "greeting": "🟢",
            "understanding_intent": "🟡", 
            "gathering_info": "🟠",
            "checking_availability": "🔵",
            "suggesting_times": "🟣",
            "confirming_booking": "🟤",
            "booking_complete": "✅",
            "error": "🔴"
        }
        
        status_icon = status_colors.get(stage, "⚪")
        st.markdown(f"**Status:** {status_icon} {stage.replace('_', ' ').title()}")
        
        if session_id:
            st.markdown(f"**Session:** `{session_id[:8]}...`")
    
    def render_suggested_responses(self, stage: str):
        suggestions = {
            "greeting": [
                "I need to schedule a meeting",
                "Check my availability for tomorrow",
                "Book an appointment next week"
            ],
            "gathering_info": [
                "Tomorrow at 2 PM",
                "Next Monday morning", 
                "Friday afternoon for 1 hour"
            ],
            "suggesting_times": [
                "The first option looks good",
                "Can we try a different time?",
                "What about later in the day?"
            ],
            "confirming_booking": [
                "Yes, please book it",
                "Actually, let me reschedule",
                "Looks perfect!"
            ]
        }
        
        if stage in suggestions:
            st.markdown("**Quick replies:**")
            cols = st.columns(len(suggestions[stage]))
            
            for i, suggestion in enumerate(suggestions[stage]):
                with cols[i]:
                    if st.button(suggestion, key=f"suggestion_{i}"):
                        return suggestion
        
        return None
    
    def render_typing_indicator(self):
        with st.empty():
            st.markdown("💭 Agent is typing...")
    
    def render_conversation_summary(self, messages: List[Dict]):
        if len(messages) > 2:
            with st.expander("📝 Conversation Summary"):
                user_messages = [msg for msg in messages if msg["role"] == "user"]
                assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
                
                st.markdown(f"**Messages exchanged:** {len(messages)}")
                st.markdown(f"**Your messages:** {len(user_messages)}")
                st.markdown(f"**Agent responses:** {len(assistant_messages)}")
                
                if messages:
                    first_message_time = messages[0].get("timestamp")
                    if first_message_time:
                        st.markdown(f"**Started:** {first_message_time}")
    
    def render_chat_controls(self):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Clear Chat"):
                return "clear"
        
        with col2:
            if st.button("📋 Copy Session"):
                return "copy"
        
        with col3:
            if st.button("💾 Save Chat"):
                return "save"
        
        return None
    
    def export_conversation(self, messages: List[Dict], session_id: str):
        conversation_text = f"Calendar Booking Agent - Session {session_id}\n"
        conversation_text += f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        conversation_text += "=" * 50 + "\n\n"
        
        for message in messages:
            role = "You" if message["role"] == "user" else "Agent"
            timestamp = message.get("timestamp", "")
            conversation_text += f"[{timestamp}] {role}: {message['content']}\n\n"
        
        return conversation_text
    
    def render_voice_input(self):
        st.markdown("**🎤 Voice Input** (Feature coming soon)")
        if st.button("Start Recording", disabled=True):
            st.info("Voice input will be available in future updates")
    
    def render_quick_booking_form(self):
        with st.expander("⚡ Quick Book"):
            with st.form("quick_booking"):
                title = st.text_input("Meeting Title")
                col1, col2 = st.columns(2)
                
                with col1:
                    date = st.date_input("Date")
                with col2:
                    time = st.time_input("Time")
                
                duration = st.selectbox("Duration", [30, 45, 60, 90, 120], index=2)
                attendees = st.text_input("Attendees (email addresses, comma separated)")
                description = st.text_area("Description (optional)")
                
                if st.form_submit_button("📅 Quick Book"):
                    booking_request = {
                        "title": title,
                        "date": date.strftime("%Y-%m-%d"),
                        "time": time.strftime("%H:%M"),
                        "duration": duration,
                        "attendees": [email.strip() for email in attendees.split(",") if email.strip()],
                        "description": description
                    }
                    
                    return booking_request
        
        return None 