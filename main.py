
import os
from googleapiclient.discovery import build
from rich.pretty import pprint
from dotenv import load_dotenv


load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = os.getenv('SHEET_NAME')

def get_spreadsheet_data():
    """Fetch spreadsheet data"""
    service = build('sheets', 'v4', developerKey=GOOGLE_API_KEY)
    all_rows = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME).execute()['values']

    # return all_rows
    if not os.path.exists('last_row.txt'):
        return all_rows, []
    with open('last_row.txt') as file:
        last_row = int(file.read())
    new_rows = all_rows[last_row:]
    return all_rows, new_rows


all_rows, new_rows = get_spreadsheet_data()
with open('last_row.txt', 'w') as file:
    file.write(str(len(all_rows)))

pprint((all_rows, new_rows))
pprint(open('last_row.txt').read())
