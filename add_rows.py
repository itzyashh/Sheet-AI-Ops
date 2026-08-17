import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from rich.pretty import pprint
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

AUTH_PAGE = Path(__file__).with_name("auth_callback.html")
AUTH_PORT = 8000


class AuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = AUTH_PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def start_auth_server():
    server = ThreadingHTTPServer(("127.0.0.1", AUTH_PORT), AuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server



load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
CLIENT_ID = os.getenv("CLIENT_ID")

def add_spreadsheet_data(rows):
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

    start_auth_server()
    webbrowser.open(auth_url)
    print("After Google sign-in, copy the code from http://localhost:8000")
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

    body = {'values': [rows]}

    all_rows = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME, valueInputOption='RAW', body=body
        ).execute()
    return all_rows

add_spreadsheet_data(['Martin Fowler', 'martin@example', '223'])



