import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.services.databases import Databases
from dotenv import load_dotenv
from googleapiclient.discovery import build
from langchain.chat_models import init_chat_model

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Appwrite DB used to persist the sheet cursor across executions
DATABASE_ID = os.getenv("APPWRITE_DATABASE_ID")
COLLECTION_ID = os.getenv("APPWRITE_COLLECTION_ID")
CURSOR_DOCUMENT_ID = os.getenv("APPWRITE_CURSOR_DOCUMENT_ID", "sheet_cursor")
APPWRITE_ENDPOINT = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")


def get_databases(context) -> Databases:
    """Build an Appwrite Databases client using the function's dynamic API key."""
    project_id = os.environ.get("APPWRITE_FUNCTION_PROJECT_ID")
    api_key = context.req.headers.get("x-appwrite-key") or os.getenv("APPWRITE_API_KEY")

    if not project_id:
        raise RuntimeError("APPWRITE_FUNCTION_PROJECT_ID is not set")
    if not api_key:
        raise RuntimeError(
            "No Appwrite API key found. Enable a dynamic API key on the function "
            "or set APPWRITE_API_KEY."
        )
    if not DATABASE_ID or not COLLECTION_ID:
        raise RuntimeError(
            "Set APPWRITE_DATABASE_ID and APPWRITE_COLLECTION_ID env vars"
        )

    client = (
        Client()
        .set_endpoint(APPWRITE_ENDPOINT)
        .set_project(project_id)
        .set_key(api_key)
    )
    return Databases(client)


def get_last_row(databases: Databases) -> int | None:
    """Return the stored row cursor, or None if it has not been initialized."""
    try:
        document = databases.get_document(
            DATABASE_ID, COLLECTION_ID, CURSOR_DOCUMENT_ID
        )
        return int(document.data["last_row"])
    except AppwriteException as exc:
        if getattr(exc, "code", None) == 404:
            return None
        raise


def save_last_row(databases: Databases, last_row: int, exists: bool) -> None:
    """Create or update the cursor document."""
    data = {"last_row": last_row}
    if exists:
        databases.update_document(
            DATABASE_ID, COLLECTION_ID, CURSOR_DOCUMENT_ID, data
        )
    else:
        databases.create_document(
            DATABASE_ID, COLLECTION_ID, CURSOR_DOCUMENT_ID, data
        )


def get_spreadsheet_data(last_row: int | None):
    """Fetch spreadsheet data and return rows added since last_row."""
    service = build("sheets", "v4", developerKey=GOOGLE_API_KEY)
    all_rows = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME)
        .execute()
        .get("values", [])
    )

    if not all_rows:
        return [], [], []

    headers = all_rows[0]

    # First run: initialize cursor only — do not summarize the full history.
    if last_row is None:
        return all_rows, [], headers

    new_rows = all_rows[last_row:]
    return all_rows, new_rows, headers


def summarize_with_ai(text, headers):
    system_prompt = """
    You are a helpful assistant that summarizes spreadsheet data.
    You will receive new rows that were added to a Google Spreadsheet.
    Please provide a clear, concise summary of this data
    """
    model = init_chat_model(model="gpt-4o-mini", model_provider="openai")
    message = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""
    Here are the headers of the spreadsheet: \n {headers}
    Here are the new rows from the spreadsheet \n {text}
    """,
        },
    ]
    return model.invoke(message).content


def send_email(subject, body):
    """Send email with the summary."""
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()


def main(context):
    """Appwrite Functions entrypoint."""
    try:
        required = [
            "GOOGLE_API_KEY",
            "SPREADSHEET_ID",
            "SHEET_NAME",
            "SENDER_EMAIL",
            "RECIPIENT_EMAIL",
            "SENDER_PASSWORD",
            "OPENAI_API_KEY",
        ]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

        databases = get_databases(context)
        last_row = get_last_row(databases)
        cursor_exists = last_row is not None

        all_rows, new_rows, headers = get_spreadsheet_data(last_row)
        save_last_row(databases, len(all_rows), exists=cursor_exists)

        if last_row is None:
            context.log(
                f"Initialized cursor at row {len(all_rows)}; no summary on first run"
            )
            return context.res.json(
                {
                    "message": "Cursor initialized",
                    "row_count": len(all_rows),
                }
            )

        if not new_rows:
            context.log("No new rows since last run")
            return context.res.json({"message": "No new rows", "row_count": len(all_rows)})

        context.log(f"Summarizing {len(new_rows)} new row(s)")
        summary = summarize_with_ai(new_rows, headers)
        send_email("Sheet Summary Report", summary)
        context.log("Email sent")

        return context.res.json(
            {
                "message": "Summary emailed",
                "new_rows": len(new_rows),
                "row_count": len(all_rows),
                "summary": summary,
            }
        )
    except Exception as exc:
        context.error(str(exc))
        return context.res.json({"error": str(exc)}, 500)
