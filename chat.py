"""Terminal REPL for the demo sheets agent.

Setup:
1. Put the service account JSON in service_account/ (gitignored)
2. Set SERVICE_ACCOUNT_FILE in .env to that path
3. Share the demo spreadsheet with the service account client_email as Editor

The agent uses sheet schema + a capped search (max 10 rows). It does not
send the full sheet to the model.

Run:
    uv run python chat.py
"""

from dotenv import load_dotenv
from rich.pretty import pprint

from sheet_ai_ops.agent import create_sheet_agent

load_dotenv()

THREAD_ID = "demo"


def main() -> None:
    agent = create_sheet_agent()
    print("Sheets agent ready. Type a question, or 'exit' to quit.")

    while True:
        try:
            input_message = input("Enter your message: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if input_message.strip().lower() in {"exit", "quit"}:
            break
        if not input_message.strip():
            continue

        response = agent.invoke(
            {"messages": [{"role": "user", "content": input_message}]},
            {"configurable": {"thread_id": THREAD_ID}},
        )
        pprint(response["messages"][-1].content)


if __name__ == "__main__":
    main()
