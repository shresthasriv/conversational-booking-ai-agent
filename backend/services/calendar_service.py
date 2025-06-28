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
            if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
                credentials_info = dict(st.secrets['google_service_account'])
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
            events_result = self.service.events().list(
                calendarId="shresthas04.ms@gmail.com",
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return events
        except Exception as e:
            return []

    def check_availability(self, start_time: datetime, end_time: datetime) -> bool:
        user_tz = pytz.timezone(settings.TIMEZONE)
        
        if start_time.tzinfo is None:
            start_time = user_tz.localize(start_time).astimezone(pytz.UTC)
            end_time = user_tz.localize(end_time).astimezone(pytz.UTC)
        else:
            start_time = start_time.astimezone(pytz.UTC)
            end_time = end_time.astimezone(pytz.UTC)
        
        events = self.get_calendar_events(start_time, end_time)
        
        for event in events:
            event_start = event.get('start', {})
            event_end = event.get('end', {})
            
            if 'dateTime' in event_start and 'dateTime' in event_end:
                event_start_dt = datetime.fromisoformat(event_start['dateTime'].replace('Z', '+00:00'))
                event_end_dt = datetime.fromisoformat(event_end['dateTime'].replace('Z', '+00:00'))

                if (start_time < event_end_dt and end_time > event_start_dt):
                    return False
        
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
