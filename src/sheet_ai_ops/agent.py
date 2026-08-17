from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from sheet_ai_ops.query import apply_query, generate_sheet_query
from sheet_ai_ops.sheets import SHEET_NAME
from sheet_ai_ops.sheets import append_row as append_row_impl
from sheet_ai_ops.sheets import get_schema as get_schema_impl
from sheet_ai_ops.sheets import load_sheet
from sheet_ai_ops.sheets import update_row as update_row_impl


@tool
def get_sheet_schema():
    """Return sheet structure without loading all rows.

    Includes headers, row count, a few sample values per column, and 2 preview rows.
    Use this to understand the sheet. Do not use it as a full data dump.
    """
    return get_schema_impl()


@tool
def search_sheet(request: str):
    """Find rows matching a natural-language lookup.

    Pass a self-contained request, e.g. "John" or "John Redcliffe with id 567".
    An internal query step turns that into filters and returns at most 10 rows.
    If results are truncated, ask the user to refine instead of searching the whole sheet.
    """
    schema = get_schema_impl()
    query = generate_sheet_query(schema, request)
    return apply_query(load_sheet(), query)


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
    Search first so the range matches the real row and columns.
    """
    return update_row_impl(a1_range, values)


def create_sheet_agent():
    sheet_name = SHEET_NAME or "Sheet1"
    model = ChatOpenAI(model="gpt-4o-mini")
    return create_agent(
        model,
        tools=[get_sheet_schema, search_sheet, append_row, update_row],
        debug=False,
        system_prompt=(
            f"You are a spreadsheet assistant for '{sheet_name}'. "
            "Never load or invent the full sheet. "
            "For 'what is this sheet' or structure questions, call get_sheet_schema. "
            "For lookups, call search_sheet with the user's request, including any "
            "identifiers they add later. Search returns at most 10 rows. "
            "If truncated or several people share a name, ask the user to refine "
            "(full name, id, email) and search again. "
            "After a write, confirm what changed. When updating, search first, then "
            f"call update_row with an A1 range like '{sheet_name}!A4:C4'."
        ),
        checkpointer=InMemorySaver(),
    )
