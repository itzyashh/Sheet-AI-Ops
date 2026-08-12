import os
import webbrowser
from dotenv import load_dotenv
from google.oauth2 import service_account
from rich.pretty import pprint
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials



load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
CLIENT_ID = os.getenv("CLIENT_ID")

def get_spreadsheet_data():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/google/callback"
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )

    webbrowser.open(auth_url)



    code = input("Enter the code: ")
    flow.fetch_token(code=code)


    creds = flow.credentials

    creds = Credentials(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds._client_id,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES
    )

    # creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    all_rows = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME).execute()
    return all_rows

data = get_spreadsheet_data()
pprint(data)


