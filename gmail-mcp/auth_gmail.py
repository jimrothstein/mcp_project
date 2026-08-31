
# auth_gmail.py
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

BASE = Path(__file__).parent
TOKEN = BASE / "token.json"
CREDENTIALS = BASE / "credentials.json"

creds = None
if TOKEN.exists():
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
        creds = flow.run_local_server(port=0)
    TOKEN.write_text(creds.to_json())

print("Gmail authorization succeeded.")