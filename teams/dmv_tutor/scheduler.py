import os
import schedule
import time
import requests
import threading

def send_daily_ping():
    """Sends the daily 11:00 AM ping via Telegram."""
    print("[Scheduler] Triggering daily DMV Tutor ping...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id, 
            "text": "🚗 Good morning! It's 11:00 AM. Are you ready for your daily DMV 4-Wheeler practice quiz? Reply 'ready' to begin!"
        }
        try:
            requests.post(url, json=payload)
            print("[Scheduler] Message dispatched to API.")
        except Exception as e:
            print(f"[Scheduler] Failed to send: {e}")
    else:
        print("[Scheduler] TELEGRAM credentials missing. Printing to console instead:")
        print(">>> 🚗 Good morning! It's 11:00 AM. Are you ready for your daily DMV 4-Wheeler practice quiz? Reply 'ready' to begin!")

def start_scheduler():
    """Starts the background scheduler thread."""
    schedule.every().day.at("11:00").do(send_daily_ping)
    
    # Also for testing purposes, we can trigger it every 1 minute if an env var is set
    if os.getenv("TEST_SCHEDULER") == "true":
        schedule.every(1).minutes.do(send_daily_ping)
        
    def run_loop():
        print("[Scheduler] Background thread started.")
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("Testing scheduler execution...")
    send_daily_ping()
