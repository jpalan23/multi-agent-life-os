import os
import json
from pypdf import PdfReader
from langchain_core.messages import HumanMessage
from core.llm_factory import get_deep_llm
from core.db_manager import db

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a given PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def generate_questions_from_text(text_chunk: str, num_questions: int = 5):
    """Uses LLM to generate multiple choice questions from a text chunk."""
    llm = get_deep_llm(temperature=0.2)
    prompt = f"""
    Based on the following excerpt from the CA DMV Handbook, generate {num_questions} multiple-choice questions for a driving written test.
    Categorize each question (e.g., 'Road Signs', 'Right of Way', 'Speed Limits').
    
    Output the response STRICTLY as a JSON array of objects, with no other text or markdown formatting. 
    Each object must have:
    - "category": string
    - "question_text": string
    - "options": list of 4 strings (A, B, C, D)
    - "correct_answer": string (exactly matching one of the options)
    
    Excerpt:
    {text_chunk}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    
    # Clean up potential markdown formatting from LLM
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
        
    try:
        questions = json.loads(content)
        return questions
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM output as JSON: {e}")
        return []

def populate_db_with_pdf(pdf_path: str):
    """Parses a PDF and populates the DB with generated questions."""
    print(f"Reading PDF from {pdf_path}...")
    full_text = extract_text_from_pdf(pdf_path)
    
    # Chunking strategy: process in chunks of 4000 characters to avoid context limits
    chunk_size = 4000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    print(f"Extracted {len(full_text)} characters. Processing {len(chunks)} chunks...")
    
    total_added = 0
    # Process only the first few chunks for demonstration, or all if preferred
    for i, chunk in enumerate(chunks[:5]): # Limiting to 5 chunks to save time/tokens during setup
        print(f"Generating questions for chunk {i+1}...")
        questions = generate_questions_from_text(chunk, num_questions=3)
        
        for q in questions:
            try:
                options_json = json.dumps(q['options'])
                db.execute_query(
                    """
                    INSERT INTO dmv_questions (category, question_text, options, correct_answer) 
                    VALUES (?, ?, ?, ?)
                    """,
                    (q['category'], q['question_text'], options_json, q['correct_answer'])
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
