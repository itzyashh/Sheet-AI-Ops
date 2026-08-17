import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

_sheet_cache: dict | None = None
SCHEMA_SAMPLE_VALUES = 5
SCHEMA_PREVIEW_ROWS = 2


def _require_env(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def _service_account_path() -> Path:
    raw = _require_env("SERVICE_ACCOUNT_FILE", SERVICE_ACCOUNT_FILE)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.is_file():
        raise RuntimeError(
            f"Service account file not found: {path}. "
            "Place the JSON in the project folder and set SERVICE_ACCOUNT_FILE."
        )
    return path


def get_sheets_service():
    creds = Credentials.from_service_account_file(
        str(_service_account_path()),
        scopes=SCOPES,
    )
    return build("sheets", "v4", credentials=creds)


def read_sheet() -> dict:
    spreadsheet_id = _require_env("SPREADSHEET_ID", SPREADSHEET_ID)
    sheet_name = _require_env("SHEET_NAME", SHEET_NAME)
    service = get_sheets_service()
    values = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
        .get("values", [])
    )

    if not values:
        return {"sheet": sheet_name, "headers": [], "rows": []}

    headers = [str(h) for h in values[0]]
    rows = []
    for index, raw_row in enumerate(values[1:], start=2):
        record = {
            headers[i]: (str(raw_row[i]) if i < len(raw_row) else "")
            for i in range(len(headers))
        }
        record["_row"] = index
        rows.append(record)

    return {"sheet": sheet_name, "headers": headers, "rows": rows}


def _clear_sheet_cache() -> None:
    global _sheet_cache
    _sheet_cache = None


def load_sheet(*, force: bool = False) -> dict:
    global _sheet_cache
    if _sheet_cache is None or force:
        _sheet_cache = read_sheet()
    return _sheet_cache


def get_schema() -> dict:
    data = load_sheet()
    headers = data["headers"]
    rows = data["rows"]
    column_samples: dict[str, list[str]] = {}
    for header in headers:
        seen: list[str] = []
        for row in rows:
            value = str(row.get(header, "")).strip()
            if value and value not in seen:
                seen.append(value)
            if len(seen) >= SCHEMA_SAMPLE_VALUES:
                break
        column_samples[header] = seen
    return {
        "sheet": data["sheet"],
        "headers": headers,
        "row_count": len(rows),
        "column_samples": column_samples,
        "preview_rows": rows[:SCHEMA_PREVIEW_ROWS],
    }


def append_row(values: list[str]) -> dict:
    spreadsheet_id = _require_env("SPREADSHEET_ID", SPREADSHEET_ID)
    sheet_name = _require_env("SHEET_NAME", SHEET_NAME)
    service = get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption="RAW",
            body={"values": [values]},
        )
        .execute()
    )
    _clear_sheet_cache()
    return {
        "updated_range": result.get("updates", {}).get("updatedRange"),
        "updated_rows": result.get("updates", {}).get("updatedRows"),
        "values": values,
    }


def update_row(a1_range: str, values: list[str]) -> dict:
    spreadsheet_id = _require_env("SPREADSHEET_ID", SPREADSHEET_ID)
    service = get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=a1_range,
            valueInputOption="RAW",
            body={"values": [values]},
        )
        .execute()
    )
    _clear_sheet_cache()
    return {
        "updated_range": result.get("updatedRange"),
        "updated_rows": result.get("updatedRows"),
        "values": values,
    }
