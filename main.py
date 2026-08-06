
import os
import smtplib
from googleapiclient.discovery import build
from rich.pretty import pprint
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = os.getenv('SHEET_NAME')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
RECIPENT_EMAIL = os.getenv('RECIPENT_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

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
    headers = all_rows[0]
    return all_rows, new_rows, headers

def summarize_with_ai(text, headers):
    system_prompt = """
    You are a helpful assistant that summarizes spreadsheet data.
    You will receive new rows that were added to a Google Spreadsheet.
    Please provide a clear, concise summary of this data
    """
    model = init_chat_model(model="gpt-4o-mini", model_provider='openai')
    message = [{"role": "system", "content": system_prompt }, 
    {"role": "user", "content": f"""
    Here are the headers of the spreadsheet: \n {headers}
    Here are the new rows from the spreadsheet \n {text}
    """}]
    response = model.invoke(message).content
    return response

def send_email(subject, body):
    """Send email with the summary"""
    pprint("Email running")
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()

all_rows, new_rows, headers = get_spreadsheet_data()
with open('last_row.txt', 'w') as file:
    file.write(str(len(all_rows)))


summary = summarize_with_ai(new_rows, headers)
send_email("Sheet Summary Report", summary)
pprint(summary)

# pprint((all_rows, new_rows))
# pprint(open('last_row.txt').read())
