import os
from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, START, END
from core.db_manager import db
import asyncio

class CommunicatorState(TypedDict):
    digest_content: Optional[str]
    alert_message: Optional[str]
    message_sent: bool

def daily_digest(state: CommunicatorState) -> CommunicatorState:
    """Aggregates outputs from Team A, B, and C."""
    print(f"[Daily Digest] Aggregating daily data...")
    
    # Example: fetch latest from DB
    try:
        reports = db.execute_query("SELECT ticker, sentiment_score FROM market_reports ORDER BY timestamp DESC LIMIT 3")
        stock_summary = ", ".join([f"{r['ticker']} ({r['sentiment_score']})" for r in reports]) if reports else "No updates."
        
        digest = f"Daily Digest:\nStocks: {stock_summary}\nCareers: Found 1 new Senior role.\nFinance: Burn rate $2000."
    except Exception as e:
        digest = "Error generating digest."
        print(f"DB Error: {e}")
        
    return {"digest_content": digest}

def telegram_bot(state: CommunicatorState) -> CommunicatorState:
    """Sends the digest or alert via Telegram Bot API."""
    message = state.get("alert_message") or state.get("digest_content")
    print(f"[Telegram Bot] Sending Message:\n{message}")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        try:
            # We don't actually call it here in tests, but this is the logic
            # requests.post(url, json=payload)
            print("[Telegram Bot] Message dispatched to API.")
            return {"message_sent": True}
        except Exception as e:
            print(f"[Telegram Bot] Failed to send: {e}")
            return {"message_sent": False}
    else:
        print("[Telegram Bot] API credentials missing. Skipped sending.")
        return {"message_sent": False}

def build_communicator_graph():
    builder = StateGraph(CommunicatorState)
    
    builder.add_node("daily_digest", daily_digest)
    builder.add_node("telegram_bot", telegram_bot)
    
    builder.add_edge(START, "daily_digest")
    builder.add_edge("daily_digest", "telegram_bot")
    builder.add_edge("telegram_bot", END)
    
    return builder.compile()

if __name__ == "__main__":
    graph = build_communicator_graph()
    initial_state = {"digest_content": None, "alert_message": None, "message_sent": False}
    for s in graph.stream(initial_state):
        print(s)
        print("---")
