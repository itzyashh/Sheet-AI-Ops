from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

MAX_RESULT_ROWS = 10

FilterOp = Literal[
    "eq",
    "ne",
    "contains",
    "startswith",
    "endswith",
    "gt",
    "gte",
    "lt",
    "lte",
]


class ColumnFilter(BaseModel):
    column: str = Field(description="Exact header name from the sheet schema")
    op: FilterOp = Field(description="Comparison to apply")
    value: str = Field(description="Value to compare against")


class SheetQuery(BaseModel):
    text: str | None = Field(
        default=None,
        description="Keyword to search across every column when the user did not name a field",
    )
    filters: list[ColumnFilter] = Field(
        default_factory=list,
        description="AND-ed column filters. Use when the user names a field or id.",
    )
    limit: int = Field(
        default=MAX_RESULT_ROWS,
        ge=1,
        le=MAX_RESULT_ROWS,
        description="Max rows to return. Keep at 10 unless looking up one record.",
    )


def generate_sheet_query(schema: dict, request: str) -> SheetQuery:
    model = ChatOpenAI(model="gpt-4o-mini").with_structured_output(SheetQuery)
    headers = schema.get("headers") or []
    samples = schema.get("column_samples") or {}
    query = model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "Convert a user request into a spreadsheet lookup. "
                    "Use only header names from the schema. "
                    "If the user gives a keyword without a column (e.g. 'John'), set text. "
                    "If they name a field (id 567, email X), use a column filter. "
                    "AND text and filters when both help. "
                    f"Never invent headers. Available headers: {headers}. "
                    f"Sample values: {samples}."
                ),
            },
            {"role": "user", "content": request},
        ]
    )
    if not query.text and not query.filters:
        query.text = request
    return query


def _resolve_column(headers: list[str], name: str) -> str | None:
    needle = name.strip().lower()
    for header in headers:
        if header.lower() == needle:
            return header
    partial = [
        header
        for header in headers
        if needle in header.lower() or header.lower() in needle
    ]
    if len(partial) == 1:
        return partial[0]
    return None


def _compare(cell: str, op: FilterOp, value: str) -> bool:
    left = cell.strip()
    right = str(value).strip()
    if op in {"gt", "gte", "lt", "lte"}:
        try:
            left_n = float(left)
            right_n = float(right)
        except ValueError:
            return False
        if op == "gt":
            return left_n > right_n
        if op == "gte":
            return left_n >= right_n
        if op == "lt":
            return left_n < right_n
        return left_n <= right_n

    a, b = left.lower(), right.lower()
    if op == "eq":
        return a == b
    if op == "ne":
        return a != b
    if op == "contains":
        return b in a
    if op == "startswith":
        return a.startswith(b)
    if op == "endswith":
        return a.endswith(b)
    return False


def _row_matches(row: dict, headers: list[str], query: SheetQuery) -> bool:
    for item in query.filters:
        column = _resolve_column(headers, item.column)
        if column is None:
            return False
        if not _compare(str(row.get(column, "")), item.op, item.value):
            return False
    if query.text:
        needle = query.text.strip().lower()
        if not needle:
            return True
        return any(needle in str(row.get(header, "")).lower() for header in headers)
    return True


def apply_query(data: dict, query: SheetQuery) -> dict:
    headers = data.get("headers") or []
    rows = data.get("rows") or []
    matched = [row for row in rows if _row_matches(row, headers, query)]
    limit = min(max(query.limit, 1), MAX_RESULT_ROWS)
    returned = matched[:limit]
    total = len(matched)
    result = {
        "query": query.model_dump(),
        "total_matches": total,
        "returned": len(returned),
        "truncated": total > len(returned),
        "headers": headers,
        "rows": returned,
    }
    if result["truncated"]:
        result["hint"] = (
            "Multiple matches. Ask the user to refine with a unique field "
            "(full name, id, email)."
        )
    return result
