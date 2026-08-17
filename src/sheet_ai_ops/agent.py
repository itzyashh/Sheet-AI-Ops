from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from sheet_ai_ops.sheets import SHEET_NAME
from sheet_ai_ops.sheets import append_row as append_row_impl
from sheet_ai_ops.sheets import read_sheet as read_sheet_impl
from sheet_ai_ops.sheets import update_row as update_row_impl


@tool
def read_sheet():
    """Read the demo spreadsheet. Returns headers and all data rows.

    Each row includes `_row`, the 1-based Google Sheets row number.
    Use that number when building an A1 range for updates.
    """
    return read_sheet_impl()


@tool
def append_row(values: list[str]):
    """Append one row to the demo spreadsheet.

    Pass cell values in header order, e.g. ["Jane Doe", "jane@example.com", "100"].
    """
    return append_row_impl(values)


@tool
def update_row(a1_range: str, values: list[str]):
    """Update cells in the demo spreadsheet using A1 notation.

    Example: a1_range="Sheet1!A4:C4", values=["Yash Jhav", "yash@example.com", "223"].
    Read the sheet first so the range matches the real row and columns.
    """
    return update_row_impl(a1_range, values)


def create_sheet_agent():
    sheet_name = SHEET_NAME or "Sheet1"
    model = ChatOpenAI(model="gpt-4o-mini")
    return create_agent(
        model,
        tools=[read_sheet, append_row, update_row],
        debug=False,
        system_prompt=(
            f"You are a spreadsheet assistant for the demo Google Sheet tab "
            f"'{sheet_name}'. Always use tools to read or change data — never "
            "invent rows. After a write, confirm what changed. When updating, "
            f"read first, then call update_row with an A1 range like "
            f"'{sheet_name}!A4:C4'."
        ),
        checkpointer=InMemorySaver(),
    )
