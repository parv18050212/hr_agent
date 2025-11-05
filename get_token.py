import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the scopes (permissions) we need
# These MUST match what you set in the Google Cloud console
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar"
]

def main():
    """
    Shows basic usage of the Gmail & Calendar APIs.
    Generates token.json from credentials.json.
    """
    creds = None
    
    # The file token.json stores the user's access and refresh tokens.
    # It is created automatically when the authorization flow completes
    # for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            # This line will open a browser window for you to log in
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
    print("="*30)
    print("SUCCESS! 'token.json' has been created.")
    print("You can now close this script.")
    print("="*30)

if __name__ == "__main__":
    main()