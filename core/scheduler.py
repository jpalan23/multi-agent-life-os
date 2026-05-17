import os
import json
import time
import schedule
import threading
from dotenv import load_dotenv

def dispatch_notification(user_id: str, text: str, image_path: str = None):
    """Dispatches the notification to the user via Twilio (WhatsApp) or Telegram/Console fallback."""
    load_dotenv()
    
    # Attempt Twilio WhatsApp Push
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER") # e.g. whatsapp:+14155238886
    
    if twilio_sid and twilio_token and twilio_from:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            
            # Format user_id properly if it's a phone number. For now we assume user_id is the exact recipient string.
            # E.g. user_id = "whatsapp:+1234567890"
            if not user_id.startswith("whatsapp:"):
                print(f"[Scheduler] Warning: {user_id} does not start with 'whatsapp:'. Falling back to console.")
                print(f">>> To {user_id}: {text}")
                return
                
            msg_args = {
                "from_": twilio_from,
                "body": text,
                "to": user_id
            }
            
            if image_path:
                # We need the public ngrok URL to send an image. If not available, we skip the image.
                ngrok_url = os.getenv("NGROK_URL")
                if ngrok_url:
                    filename = os.path.basename(image_path)
                    msg_args["media_url"] = [f"{ngrok_url.rstrip('/')}/images/{filename}"]
            
            client.messages.create(**msg_args)
            print(f"[Scheduler] Twilio WhatsApp message pushed to {user_id}.")
            return
        except Exception as e:
            print(f"[Scheduler] Twilio push failed: {e}")
            
    # Fallback to Telegram
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
        print(f"[Scheduler] Telegram message pushed.")
        return
        
    # Final Fallback to Console
    print(f"[Scheduler] Credentials missing. Printing to console instead:")
    print(f">>> To {user_id}: {text}")

def execute_job(action: str, user_id: str):
    """Executes the natural language action via the main system router."""
    print(f"\n[Scheduler] Executing scheduled job for {user_id}: '{action}'")
    
    # We must import run_system inside the function to avoid circular imports
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from main import run_system
    
    try:
        response_data = run_system(action, thread_id=user_id)
        text = response_data.get("text", "Task completed.")
        image_path = response_data.get("image_path")
        
        # Dispatch the result back to the user
        dispatch_notification(user_id, text, image_path)
        
    except Exception as e:
        print(f"[Scheduler] Error executing job: {e}")

def load_schedule_from_json():
    """Reads the JSON config and maps jobs to the schedule library."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "schedule.json")
    
    schedule.clear()
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            
        jobs = config.get("jobs", [])
        for job in jobs:
            time_str = job["time"]
            action = job["action"]
            user_id = job["user_id"]
            
            schedule.every().day.at(time_str).do(execute_job, action=action, user_id=user_id)
            print(f"[Scheduler] Loaded job at {time_str} -> '{action}'")
            
    except Exception as e:
        print(f"[Scheduler] Error loading config: {e}")

def start_scheduler():
    """Starts the background scheduler thread."""
    load_schedule_from_json()
    
    def run_loop():
        print("[Scheduler] Background daemon started.")
        while True:
            # We can optionally hot-reload the schedule here by checking file modification time
            # For simplicity, we just run the pending jobs. To reload, restart the service.
            schedule.run_pending()
            time.sleep(1)
            
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    load_dotenv()
    print("Testing dynamic scheduler execution...")
    load_schedule_from_json()
    schedule.run_all()
