import requests
from typing import Dict, List, Optional, Any
import streamlit as st

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 30
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url, timeout=self.timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to the backend server. Please ensure it's running on localhost:8000")
            return None
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. The server might be overloaded.")
            return None
        except requests.exceptions.HTTPError as e:
            st.error(f"🚫 Server error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            st.error(f"🔥 Unexpected error: {str(e)}")
            return None
    
    def health_check(self) -> bool:
        response = self._make_request("GET", "/health")
        return response is not None and response.get("status") == "healthy"
    
    def send_chat_message(self, message: str, session_id: Optional[str] = None) -> Optional[Dict]:
        data = {"message": message}
        if session_id:
            data["session_id"] = session_id
        
        return self._make_request("POST", "/chat", data)
    
    def check_availability(self, date: str, start_time: Optional[str] = None, 
                          end_time: Optional[str] = None, duration_minutes: int = 60) -> Optional[Dict]:
        data = {
            "date": date,
            "duration_minutes": duration_minutes
        }
        
        if start_time:
            data["start_time"] = start_time
        if end_time:
            data["end_time"] = end_time
        
        return self._make_request("POST", "/availability", data)
    
    def book_appointment(self, title: str, date: str, time: str, duration: int = 60,
                        description: str = "", attendees: List[str] = None) -> Optional[Dict]:
        data = {
            "title": title,
            "date": date,
            "time": time,
            "duration": duration,
            "description": description,
            "attendees": attendees or []
        }
        
        return self._make_request("POST", "/book", data)
    
    def get_upcoming_events(self) -> Optional[List[Dict]]:
        response = self._make_request("GET", "/calendar/events")
        return response.get("events", []) if response else None
    
    def get_active_sessions(self) -> Optional[int]:
        response = self._make_request("GET", "/sessions/active")
        return response.get("active_sessions") if response else None
    
    def delete_session(self, session_id: str) -> bool:
        response = self._make_request("DELETE", f"/sessions/{session_id}")
        return response is not None
    
    def test_connection(self) -> Dict[str, Any]:
        health = self.health_check()
        
        result = {
            "server_reachable": health,
            "api_version": "1.0.0",
            "endpoints_tested": 0,
            "endpoints_working": 0
        }
        
        if health:
            endpoints_to_test = [
                ("GET", "/"),
                ("GET", "/sessions/active"),
            ]
            
            for method, endpoint in endpoints_to_test:
                result["endpoints_tested"] += 1
                if self._make_request(method, endpoint):
                    result["endpoints_working"] += 1
        
        result["connection_health"] = (
            "🟢 Excellent" if result["endpoints_working"] == result["endpoints_tested"] and health
            else "🟡 Partial" if result["endpoints_working"] > 0
            else "🔴 Failed"
        )
        
        return result 