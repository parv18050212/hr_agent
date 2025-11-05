from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List
from datetime import datetime, timedelta, timezone

from .auth import get_google_creds

class CalendarSearchArgs(BaseModel):
    """Input schema for the FindFreeSlotsTool."""
    start_time: str = Field(..., description="The earliest time to search from, in ISO 8601 format. E.g., '2025-11-10T09:00:00Z'")
    duration_minutes: int = Field(60, description="The duration of the meeting in minutes.")

class FindFreeSlotsTool(BaseTool):
    """
    A tool for finding the next available free slot on the user's primary Google Calendar.
    Searches for the next 7 days.
    """
    name: str = "find_free_calendar_slot"
    description: str = (
        "Use this tool to find the next available free time slot on the calendar. "
        "Input is 'start_time' (ISO 8601) and 'duration_minutes'. "
        "It searches business hours (9am-5pm) for the next 7 days."
    )
    args_schema: Type[BaseModel] = CalendarSearchArgs

    def _run(self, start_time: str, duration_minutes: int) -> dict:
        """Use the tool."""
        creds = get_google_creds()
        if not creds:
            return {"error": "Could not get Google credentials."}

        try:
            service = build("calendar", "v3", credentials=creds)
            
            # Parse start time and find end of search window (7 days)
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
                
            end_dt = start_dt + timedelta(days=7)

            # Body for the free/busy query
            body = {
                "timeMin": start_dt.isoformat(),
                "timeMax": end_dt.isoformat(),
                "items": [{"id": "primary"}], # Check the primary calendar
                "timeZone": "UTC",
            }

            events_result = service.freebusy().query(body=body).execute()
            busy_slots = events_result.get("calendars", {}).get("primary", {}).get("busy", [])

            # --- Simple Slot Finding Logic ---
            # (A real-world version would be more complex, handling work hours)
            
            current_time = start_dt
            search_end = start_dt + timedelta(days=7)
            duration = timedelta(minutes=duration_minutes)

            while current_time < search_end:
                # Only check 9am-5pm UTC (simple example)
                if 9 <= current_time.hour < 17:
                    potential_end_time = current_time + duration
                    
                    # Check if this slot overlaps with any busy slot
                    is_free = True
                    for slot in busy_slots:
                        slot_start = datetime.fromisoformat(slot["start"])
                        slot_end = datetime.fromisoformat(slot["end"])
                        
                        # Check for overlap
                        if (current_time < slot_end and potential_end_time > slot_start):
                            is_free = False
                            current_time = slot_end # Jump to end of busy slot
                            break
                    
                    if is_free:
                        # Found a free slot!
                        return {
                            "start_time": current_time.isoformat(),
                            "end_time": potential_end_time.isoformat()
                        }
                
                # Increment time (e.g., jump to next day's start)
                if current_time.hour >= 17:
                    current_time = (current_time + timedelta(days=1)).replace(hour=9, minute=0, second=0)
                else:
                    # Increment by duration to find next slot
                    current_time += duration 

            return {"error": "No free slots found in the next 7 days."}

        except HttpError as error:
            return {"error": f"An error occurred: {error}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}
        
if __name__ == "__main__":
    from datetime import datetime, timezone

    print("Testing FindFreeSlotsTool...")
    
    # Set a start time for the search (e.g., now)
    start_search = datetime.now(timezone.utc).isoformat()
    
    print(f"Searching for a 60-min slot starting from: {start_search}")
    
    tool = FindFreeSlotsTool()
    result = tool.invoke({
        "start_time": start_search,
        "duration_minutes": 60
    })
    
    print("\n--- TEST RESULT ---")
    print(result)