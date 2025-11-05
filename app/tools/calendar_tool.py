import json
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field  # Correct Pydantic v2 import
from typing import Type, List

from .auth import get_google_creds

class CalendarEventArgs(BaseModel):
    """Input schema for the CreateCalendarEventTool."""
    summary: str = Field(..., description="The title or summary of the event.")
    start_time: str = Field(..., description="Event start time in ISO 8601 format. E.g., '2025-11-10T09:00:00Z'")
    end_time: str = Field(..., description="Event end time in ISO 8601 format. E.g., '2025-11-10T10:00:00Z'")
    attendees: List[str] = Field(..., description="A list of attendee email addresses.")
    location: str = Field("Google Meet", description="The location or conference details.")

class CreateCalendarEventTool(BaseTool):
    """
    A tool for creating events on the user's Google Calendar.
    """
    name: str = "create_calendar_event"
    description: str = (
        "Use this tool to create a Google Calendar event. "
        "Input is 'summary', 'start_time', 'end_time', and 'attendees'. "
        "Times must be in ISO 8601 format."
    )
    args_schema: Type[BaseModel] = CalendarEventArgs

    def _run(self, summary: str, start_time: str, end_time: str, attendees: List[str], location: str = "Google Meet") -> str:
        """Use the tool."""
        creds = get_google_creds()
        if not creds:
            return json.dumps({"error": "Could not get Google credentials."}) # Return JSON

        try:
            service = build("calendar", "v3", credentials=creds)
            
            # Ensure times are in UTC format if no timezone is specified
            start_dt = datetime.fromisoformat(start_time)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            end_dt = datetime.fromisoformat(end_time)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            
            event = {
                "summary": summary,
                "location": location,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
                "attendees": [{"email": email} for email in attendees],
                "conferenceData": {
                    "createRequest": {"requestId": "sample123", "conferenceSolutionKey": {"type": "hangoutsMeet"}}
                },
            }
            
            event = (
                service.events()
                .insert(
                    calendarId="primary", 
                    body=event,
                    conferenceDataVersion=1
                )
                .execute()
            )
            
            # Return a JSON string with all the links
            result = {
                "status": "Event created successfully!",
                "html_link": event.get('htmlLink'),
                "meet_link": event.get('hangoutLink')
            }
            return json.dumps(result)

        except HttpError as error:
            return json.dumps({"error": f"An error occurred: {error}"})
        except Exception as e:
            return json.dumps({"error": f"An unexpected error occurred: {e}"})

# --- This is for testing the tool directly ---
if __name__ == "__main__":
    
    # Get times for a test event (e.g., 1 hour from now)
    now = datetime.now(timezone.utc)
    start_test = (now + timedelta(hours=1)).isoformat()
    end_test = (now + timedelta(hours=2)).isoformat()

    print("Testing CreateCalendarEventTool...")
    tool = CreateCalendarEventTool()
    result_json = tool.invoke({
        "summary": "AI Agent Test Interview (Pydantic v2)",
        "start_time": start_test,
        "end_time": end_test,
        "attendees": ["parvagarwal73@gmail.com"] # <-- PUT YOUR OWN EMAIL HERE
    })
    
    print("--- TEST RESULT (JSON) ---")
    print(result_json)
    
    print("\n--- PARSED RESULT ---")
    print(json.loads(result_json))