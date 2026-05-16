import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse
import sys

# Add parent dir to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from main import run_system, start_scheduler

app = FastAPI(title="Life-OS WhatsApp Webhook")

# Start scheduler when server boots
@app.on_event("startup")
def startup_event():
    print("[FastAPI] Starting background scheduler...")
    start_scheduler()

# Mount the dmv_images directory so Twilio can fetch the images
# The URL will be like http://your-ngrok-url/images/page_12_img_0.png
images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "dmv_images")
os.makedirs(images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_dir), name="images")

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, Body: str = Form(...), From: str = Form(...)):
    """
    Twilio hits this endpoint when a WhatsApp message is received.
    """
    print(f"[WhatsApp] Received message from {From}: {Body}")
    
    # Process through Life-OS supervisor router
    # We use the sender's phone number as the thread_id
    response_data = run_system(Body, thread_id=From)
    
    text = response_data.get("text", "Error.")
    image_path = response_data.get("image_path")
    
    # Format Twilio XML Response
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(text)
    
    if image_path:
        # Twilio needs a public URL. We construct it assuming ngrok is pointing to the root.
        # e.g., https://xyz.ngrok.app/images/filename.png
        # In a production setup, we'd grab the host from the request headers
        host = request.headers.get("host", "localhost:8000")
        scheme = request.headers.get("x-forwarded-proto", "http") 
        filename = os.path.basename(image_path)
        media_url = f"{scheme}://{host}/images/{filename}"
        print(f"[WhatsApp] Attaching image: {media_url}")
        msg.media(media_url)
        
    return Response(content=str(resp), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    # Run server locally
    uvicorn.run("whatsapp_listener:app", host="0.0.0.0", port=8000, reload=True)
