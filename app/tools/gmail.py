import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field  # <-- Correct, direct Pydantic v2 import
from typing import Type

from .auth import get_google_creds

class GmailSendArgs(BaseModel):
    """Input schema for the SendGmailTool."""
    to: str = Field(..., description="The recipient's email address.")
    subject: str = Field(..., description="The subject line of the email.")
    body: str = Field(..., description="The plain text body of the email.")

class SendGmailTool(BaseTool):
    """
    A tool for sending emails using the Gmail API.
    """
    name: str = "send_gmail"
    description: str = (
        "Use this tool to send an email. "
        "The input is 'to', 'subject', and 'body'."
    )
    args_schema: Type[BaseModel] = GmailSendArgs  # <-- Assign the v2 model directly

    def _run(self, to: str, subject: str, body: str) -> str:
        """Use the tool."""
        creds = get_google_creds()
        if not creds:
            return "Error: Could not get Google credentials. Run get_token.py."

        try:
            service = build("gmail", "v1", credentials=creds)
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            create_message = {
                "raw": base64.urlsafe_b64encode(message.as_bytes()).decode()
            }
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            return f"Email sent successfully! Message ID: {send_message['id']}"
        except HttpError as error:
            return f"An error occurred: {error}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

# --- This is for testing the tool directly ---
if __name__ == "__main__":
    print("Testing SendGmailTool...")
    tool = SendGmailTool()
    result = tool.invoke({
        "to": "your-email@gmail.com", # <-- PUT YOUR OWN EMAIL HERE FOR A TEST
        "subject": "Test from AI Agent (Pydantic v2)",
        "body": "This is a test email from the Phase 3 tool build."
    })
    print(result)