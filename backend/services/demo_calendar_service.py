import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import uuid
from backend.models.schemas import TimeSlot, CalendarEvent
import pytz

class DemoCalendarService:
    """
    Demo Calendar Service that simulates Google Calendar functionality
    Perfect for demonstrations and portfolio projects
    """
    
    def __init__(self):
        self.service = "demo"
        self.credentials = "demo_mode"
        self.timezone = pytz.timezone("UTC")
        
        # Simulate some existing events for realism
        self._demo_events = self._generate_demo_events()
        self._booked_events = []  # Track events created during demo
    
    def _generate_demo_events(self) -> List[Dict[str, Any]]:
        """Generate realistic demo events for the next 30 days"""
        events = []
        base_time = datetime.now()
        
        # Create some realistic recurring meetings
        demo_meetings = [
            {"title": "Team Standup", "duration": 30, "recurring": "daily"},
            {"title": "Product Review", "duration": 60, "recurring": "weekly"},
            {"title": "Client Call", "duration": 45, "recurring": None},
            {"title": "Project Planning", "duration": 90, "recurring": "weekly"},
            {"title": "1:1 with Manager", "duration": 30, "recurring": "weekly"},
        ]
        
        for i in range(15):  # Generate events for next 15 days
            day = base_time + timedelta(days=i)
            
            # Skip weekends for work meetings
            if day.weekday() >= 5:
                continue
                
            # Add 1-3 random meetings per day
            daily_meetings = random.randint(1, 3)
            used_times = set()
            
            for _ in range(daily_meetings):
                meeting = random.choice(demo_meetings)
                
                # Random time between 9 AM and 5 PM
                hour = random.randint(9, 16)
                minute = random.choice([0, 30])
                
                start_time = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Avoid conflicts
                if start_time.hour in used_times:
                    continue
                
                used_times.add(start_time.hour)
                end_time = start_time + timedelta(minutes=meeting["duration"])
                
                events.append({
                    "id": str(uuid.uuid4()),
                    "summary": meeting["title"],
                    "description": f"Demo event - {meeting['title']}",
                    "start": {"dateTime": start_time.isoformat() + "Z"},
                    "end": {"dateTime": end_time.isoformat() + "Z"},
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "attendees": [{"email": "demo@example.com"}]
                })
        
        return events

    def get_calendar_events(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """Get demo calendar events within the specified time range"""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            filtered_events = []
            all_events = self._demo_events + self._booked_events
            
            for event in all_events:
                event_start = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                
                if start_dt <= event_start <= end_dt:
                    filtered_events.append(event)
            
            return sorted(filtered_events, key=lambda x: x["start"]["dateTime"])
            
        except Exception as e:
            print(f"Demo calendar error: {e}")
            return []

    def check_availability(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if the time slot is available (no conflicts with existing events)"""
        try:
            # Convert to UTC for comparison
            if start_time.tzinfo is None:
                start_time = self.timezone.localize(start_time)
                end_time = self.timezone.localize(end_time)
            
            all_events = self._demo_events + self._booked_events
            
            for event in all_events:
                event_start = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event["end"]["dateTime"].replace('Z', '+00:00'))
                
                # Check for overlap
                if (start_time < event_end and end_time > event_start):
                    return False
            
            return True
            
        except Exception as e:
            print(f"Availability check error: {e}")
            return True  # Default to available if error

    def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                    description: str = "", attendees: List[str] = []) -> str:
        """Create a new demo event"""
        try:
            event_id = str(uuid.uuid4())
            
            # Convert times to ISO format
            if start_time.tzinfo is None:
                start_iso = start_time.isoformat() + "Z"
                end_iso = end_time.isoformat() + "Z"
            else:
                start_iso = start_time.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
                end_iso = end_time.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
            
            new_event = {
                "id": event_id,
                "summary": title,
                "description": description or f"Booked via TailorTalk Calendar Agent",
                "start": {"dateTime": start_iso},
                "end": {"dateTime": end_iso},
                "start_time": start_iso,
                "end_time": end_iso,
                "attendees": [{"email": email} for email in attendees],
                "created_by": "demo_user"
            }
            
            # Add to our demo events list
            self._booked_events.append(new_event)
            
            print(f"✅ Demo event created: {title} at {start_time}")
            return event_id
            
        except Exception as e:
            print(f"Error creating demo event: {e}")
            raise Exception(f"Failed to create event: {str(e)}")

    def suggest_time_slots(self, date: datetime, duration_minutes: int = 60, 
                          working_hours: tuple = (9, 17)) -> List[Dict[str, Any]]:
        """Suggest available time slots for the given date"""
        try:
            start_hour, end_hour = working_hours
            suggestions = []
            
            # If date is a string, convert it
            if isinstance(date, str):
                date = datetime.fromisoformat(date).date()
                date = datetime.combine(date, datetime.min.time())
            
            start_of_day = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            slot_duration = timedelta(minutes=duration_minutes)
            current_time = start_of_day
            
            while current_time + slot_duration <= end_of_day:
                slot_end = current_time + slot_duration
                
                if self.check_availability(current_time, slot_end):
                    suggestions.append({
                        "start": current_time.isoformat() + "Z",
                        "end": slot_end.isoformat() + "Z",
                        "available": True,
                        "duration_minutes": duration_minutes
                    })
                
                # Move to next 30-minute slot
                current_time += timedelta(minutes=30)
                
                # Limit to 10 suggestions
                if len(suggestions) >= 10:
                    break
            
            return suggestions
            
        except Exception as e:
            print(f"Error suggesting time slots: {e}")
            return []

    def get_upcoming_events(self, max_results: int = 10) -> List[CalendarEvent]:
        """Get upcoming demo events"""
        try:
            now = datetime.now(pytz.UTC)
            upcoming_events = []
            
            all_events = self._demo_events + self._booked_events
            
            for event in all_events:
                event_start = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                
                if event_start > now:
                    upcoming_events.append(CalendarEvent(
                        summary=event.get('summary', 'Demo Event'),
                        start_time=event_start,
                        end_time=datetime.fromisoformat(event["end"]["dateTime"].replace('Z', '+00:00')),
                        description=event.get('description', ''),
                        attendees=[attendee.get('email', '') for attendee in event.get('attendees', [])]
                    ))
            
            # Sort by start time and limit results
            upcoming_events.sort(key=lambda x: x.start_time)
            return upcoming_events[:max_results]
            
        except Exception as e:
            print(f"Error getting upcoming events: {e}")
            return []

    def get_demo_stats(self) -> Dict[str, Any]:
        """Get statistics about the demo calendar"""
        return {
            "total_demo_events": len(self._demo_events),
            "events_created_in_session": len(self._booked_events),
            "mode": "demo",
            "calendar_type": "Simulated Calendar",
            "timezone": str(self.timezone)
        } 