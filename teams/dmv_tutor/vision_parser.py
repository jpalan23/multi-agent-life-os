import os
import json
import base64
from langchain_core.messages import HumanMessage
from core.llm_factory import get_vision_llm
from core.db_manager import db

def ask_vision_llm_for_question(image_path: str) -> dict:
    """Passes the image to the Vision LLM to generate a question."""
    llm = get_vision_llm(temperature=0.2, keep_alive="5m")
    
    prompt = """
    Identify the road sign, road marking, or driving scenario shown in this image.
    Generate exactly ONE highly tricky multiple-choice question testing the user's knowledge of this specific image.
    
    Output the response STRICTLY as a raw JSON object. Do not wrap it in markdown block quotes (```json).
    The object must have:
    - "category": "Road Signs & Scenarios"
    - "question_text": string (must reference 'this image' or 'the sign shown')
    - "options": list of 4 strings (A, B, C, D)
    - "correct_answer": string (exactly matching one of the options)
    """
    
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
    content_list = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    ]
    
    try:
        response = llm.invoke([HumanMessage(content=content_list)])
        content = response.content.strip()
        
        # Clean markdown
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
            
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content)
    except Exception as e:
        print(f"Vision LLM failed for {image_path}: {e}")
        return None

def process_images(image_dir: str = "data/dmv_images", size_threshold_kb: int = 5):
    """Scans the image directory, filters out small junk files, and processes the rest."""
    if not os.path.exists(image_dir):
        print(f"[Vision Parser] Error: {image_dir} not found.")
        return
        
    all_files = os.listdir(image_dir)
    valid_files = []
    
    for f in all_files:
        path = os.path.join(image_dir, f)
        size_kb = os.path.getsize(path) / 1024
        if size_kb >= size_threshold_kb:
            valid_files.append(path)
            
    print(f"\n[Vision Parser] Found {len(all_files)} total images.")
    print(f"[Vision Parser] Filtered down to {len(valid_files)} valid images (>{size_threshold_kb}KB).")
    
    total_added = 0
    for i, img_path in enumerate(valid_files):
        print(f"  Processing image {i+1}/{len(valid_files)}: {os.path.basename(img_path)}...")
        
        q = ask_vision_llm_for_question(img_path)
        if q:
            try:
                options_json = json.dumps(q.get("options", []))
                # Insert directly into SQLite. We intentionally bypass ChromaDB to avoid blocking duplicate question texts like "What does this sign mean?"
                db.execute_query(
                    "INSERT INTO dmv_questions (category, question_text, options, correct_answer, image_path) VALUES (?, ?, ?, ?, ?)",
                    (q.get("category", "Road Signs"), q.get("question_text", ""), options_json, q.get("correct_answer", ""), img_path)
                )
                print(f"  -> [ADDED] {q.get('question_text', '')[:60]}...")
                total_added += 1
            except Exception as e:
                print(f"  -> [ERROR] Failed to insert: {e}")
                
    print(f"\n[Vision Parser] Complete! Successfully added {total_added} visual questions to the database.")

if __name__ == "__main__":
    process_images()
