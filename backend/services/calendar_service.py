import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.settings import settings
from backend.models.schemas import CalendarEvent
import pytz

class GoogleCalendarService:
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()

    def _authenticate(self):
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
                credentials_info = dict(st.secrets['google_credentials'])
            else:
                with open('conversational-booking-agent-3f3e50ef4ec1.json', 'r') as f:
                    credentials_info = json.load(f)
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=settings.GOOGLE_SCOPES
            )
            
            self.service = build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            raise Exception(f"Failed to authenticate with service account: {str(e)}")

    def get_calendar_events(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        try:
            user_tz = pytz.timezone(settings.TIMEZONE)
            
            if start_time.tzinfo is None:
                start_time_local = user_tz.localize(start_time)
                end_time_local = user_tz.localize(end_time)
            else:
                start_time_local = start_time
                end_time_local = end_time

            start_time_utc = start_time_local.astimezone(pytz.UTC)
            end_time_utc = end_time_local.astimezone(pytz.UTC)
            
            print(f"API call: searching from {start_time_utc} to {end_time_utc}")
            
            events_result = self.service.events().list(
                calendarId="shresthas04.ms@gmail.com",
                timeMin=start_time_utc.isoformat(),
                timeMax=end_time_utc.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"API returned {len(events)} events")
            return events
        except Exception as e:
            print(f"Error in get_calendar_events: {e}")
            return []

    def check_availability(self, start_time: datetime, end_time: datetime) -> bool:
        print(f"Checking availability for: {start_time} to {end_time}")

        user_tz = pytz.timezone(settings.TIMEZONE)
        
        if start_time.tzinfo is None:
            start_time_local = user_tz.localize(start_time)
            end_time_local = user_tz.localize(end_time)
        else:
            start_time_local = start_time.astimezone(user_tz)
            end_time_local = end_time.astimezone(user_tz)
        
        print(f"Local IST times: {start_time_local} to {end_time_local}")
        
        events = self.get_calendar_events(start_time_local.replace(tzinfo=None), end_time_local.replace(tzinfo=None))
        print(f"Found {len(events)} events in time range")

        for event in events:
            event_start = event.get('start', {})
            event_end = event.get('end', {})
            
            print(f"Checking event: {event.get('summary', 'No title')}")
            print(f"Event start: {event_start}")
            print(f"Event end: {event_end}")
            
            if 'dateTime' in event_start and 'dateTime' in event_end:
                try:
                    event_start_str = event_start['dateTime']
                    event_end_str = event_end['dateTime']

                    event_start_dt = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                    event_end_dt = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))

                    event_start_local = event_start_dt.astimezone(user_tz)
                    event_end_local = event_end_dt.astimezone(user_tz)
                    
                    print(f"Event times in IST: {event_start_local} to {event_end_local}")
                    print(f"Requested times in IST: {start_time_local} to {end_time_local}")
                    
                    if (start_time_local < event_end_local and end_time_local > event_start_local):
                        print(f"CONFLICT DETECTED with event: {event.get('summary', 'No title')}")
                        return False
                        
                except Exception as e:
                    print(f"Error parsing event times: {e}")
                    continue
        
        print("No conflicts found - time slot is available")
        return True

    def create_event(self, title: str, start_time: datetime, end_time: datetime, description: str = "") -> str:
        try:
            if start_time.tzinfo is None:
                start_iso = start_time.isoformat()
                end_iso = end_time.isoformat()
            else:
                start_iso = start_time.replace(tzinfo=None).isoformat()
                end_iso = end_time.replace(tzinfo=None).isoformat()
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': settings.TIMEZONE,
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': settings.TIMEZONE,
                },
            }
            
            created_event = self.service.events().insert(calendarId="shresthas04.ms@gmail.com", body=event).execute()
            return created_event.get('id')
            
        except Exception as e:
            raise Exception(f"Failed to create calendar event: {str(e)}")

    def suggest_time_slots(self, date: datetime, duration_minutes: int = 60, 
                          working_hours: tuple = (9, 17)) -> List[Dict[str, datetime]]:
        start_hour, end_hour = working_hours
        suggestions = []
        
        start_of_day = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        slot_duration = timedelta(minutes=duration_minutes)
        current_time = start_of_day
        
        while current_time + slot_duration <= end_of_day:
            slot_end = current_time + slot_duration
            
            if self.check_availability(current_time, slot_end):
                suggestions.append({
                    'start': current_time,
                    'end': slot_end
                })
            
            current_time += timedelta(minutes=30)
        
        return suggestions[:5]

    def get_upcoming_events(self, max_results: int = 10) -> List[CalendarEvent]:
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId="shresthas04.ms@gmail.com",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            calendar_events = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    
                    calendar_events.append(CalendarEvent(
                        summary=event.get('summary', 'No Title'),
                        start_time=start_dt,
                        end_time=end_dt,
                        description=event.get('description', ''),
                        attendees=[attendee.get('email') for attendee in event.get('attendees', [])]
                    ))
            
            return calendar_events
            
        except HttpError as error:
            return []
