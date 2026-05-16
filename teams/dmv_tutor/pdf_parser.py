import os
import json
import base64
import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage
from core.llm_factory import get_deep_llm, get_vision_llm
from core.db_manager import db

def extract_pages(pdf_path: str):
    """Extracts text and images from a given PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    
    # PDF pages are 0-indexed. 
    target_indices = list(range(8, 58)) + list(range(69, 73))
    
    pages_data = []
    
    image_dir = os.path.join(os.path.dirname(pdf_path), "dmv_images")
    os.makedirs(image_dir, exist_ok=True)
    
    for i in target_indices:
        if i < len(doc):
            page = doc.load_page(i)
            text = page.get_text()
            
            # Extract images
            images_on_page = []
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_filename = f"page_{i+1}_img_{img_index}.{image_ext}"
                image_path = os.path.join(image_dir, image_filename)
                
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                    
                images_on_page.append(image_path)
                
            pages_data.append({
                "page_num": i+1,
                "text": text,
                "images": images_on_page
            })
            
    return pages_data

def generate_questions_from_page(page_data: dict, num_questions: int = 3):
    """Uses LLM/Vision LLM to generate multiple choice questions from a page."""
    
    prompt_text = f"""
    Based on the following excerpt from the CA DMV Handbook (Page {page_data['page_num']}), generate {num_questions} multiple-choice questions for a driving written test.
    Categorize each question (e.g., 'Road Signs', 'Right of Way', 'Speed Limits').
    
    Output the response STRICTLY as a JSON array of objects, with no other text or markdown formatting. 
    Each object must have:
    - "category": string
    - "question_text": string
    - "options": list of 4 strings (A, B, C, D)
    - "correct_answer": string (exactly matching one of the options)
    
    Excerpt:
    {page_data['text']}
    """
    
    content_list = [{"type": "text", "text": prompt_text}]
    has_images = len(page_data['images']) > 0
    
    if has_images:
        llm = get_vision_llm(temperature=0.2)
        # We'll attach the first image on the page for context
        img_path = page_data['images'][0]
        with open(img_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        content_list.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    else:
        llm = get_deep_llm(temperature=0.2)
        
    response = llm.invoke([HumanMessage(content=content_list)])
    content = response.content.strip()
    
    # Clean up potential markdown formatting from LLM
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
        
    try:
        questions = json.loads(content)
        # If an image was used, append the image path to the question
        if has_images:
            for q in questions:
                q['image_path'] = page_data['images'][0]
        return questions
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM output as JSON: {e}")
        return []

def populate_db_with_pdf(pdf_path: str):
    """Parses a PDF and populates the DB with generated questions."""
    print(f"Reading PDF from {pdf_path}...")
    pages_data = extract_pages(pdf_path)
    
    print(f"Extracted {len(pages_data)} pages. Generating questions...")
    
    total_added = 0
    # Process a few pages for demonstration to save time
    for page in pages_data[:5]: 
        print(f"Generating questions for page {page['page_num']}...")
        questions = generate_questions_from_page(page, num_questions=2)
        
        for q in questions:
            try:
                options_json = json.dumps(q['options'])
                img_path = q.get('image_path', None)
                
                db.execute_query(
                    """
                    INSERT INTO dmv_questions (category, question_text, options, correct_answer, image_path) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (q['category'], q['question_text'], options_json, q['correct_answer'], img_path)
                )
                total_added += 1
            except Exception as e:
                print(f"Error inserting question into DB: {e}")
                
    print(f"Successfully generated and inserted {total_added} questions into the database.")

def download_dmv_pdf(output_path: str):
    """Downloads the CA DMV handbook automatically if it doesn't exist."""
    import requests
    print(f"PDF not found. Attempting to download the CA DMV handbook to {output_path}...")
    
    # Official CA DMV Handbook URL (might redirect or update based on year)
    url = "https://www.dmv.ca.gov/portal/file/california-driver-handbook-pdf/"
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Use headers to pretend to be a browser, DMV site might block raw python requests
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download successful!")
        return True
    except Exception as e:
        print(f"Failed to download PDF automatically: {e}")
        print("Please manually download the handbook and place it at: " + output_path)
        return False

if __name__ == "__main__":
    import sys
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "data/dmv.pdf"
    
    if not os.path.exists(pdf_file):
        downloaded = download_dmv_pdf(pdf_file)
        if not downloaded:
            sys.exit(1)
            
    populate_db_with_pdf(pdf_file)
