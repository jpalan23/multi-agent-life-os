import os
import json
import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage
from core.llm_factory import get_deep_llm
from core.db_manager import db
from core.vector_store import vector_db

def init_vector_memory():
    """Loads existing SQLite questions into ChromaDB to ensure we don't duplicate them."""
    print("[Advanced Parser] Initializing Vector Memory from SQLite...")
    existing = db.execute_query("SELECT id, question_text FROM dmv_questions")
    for row in existing:
        vector_db.add_dmv_question(row['question_text'], str(row['id']))
    print(f"[Advanced Parser] Loaded {len(existing)} existing questions into Vector Memory.")

def insert_question_if_unique(category: str, q_text: str, options: list, answer: str, img_path: str = None) -> bool:
    """Checks VectorDB for duplicates. If unique, inserts into SQLite and VectorDB."""
    
    # 1. Semantic Check
    if vector_db.is_duplicate_question(q_text, distance_threshold=0.8):
        print(f"  -> [DUPLICATE BLOCKED] {q_text[:60]}...")
        return False
        
    # 2. Insert into SQLite
    try:
        options_json = json.dumps(options)
        db.execute_query(
            "INSERT INTO dmv_questions (category, question_text, options, correct_answer, image_path) VALUES (?, ?, ?, ?, ?)",
            (category, q_text, options_json, answer, img_path)
        )
        
        # We need the inserted ID to add to VectorDB. SQLite returns it via last_insert_rowid()
        # Since db.execute_query doesn't return last row id right now, we can query it or just use the text as ID.
        # For ChromaDB, ID just needs to be unique. Using a hash of the text is fine.
        import hashlib
        q_id = hashlib.md5(q_text.encode()).hexdigest()
        
        # 3. Add to VectorDB
        vector_db.add_dmv_question(q_text, q_id)
        
        print(f"  -> [ADDED] {q_text[:60]}...")
        return True
    except Exception as e:
        print(f"  -> [ERROR] Failed to insert: {e}")
        return False

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from an entire PDF."""
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return ""
        
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 3000) -> list:
    """Splits text into chunks to feed into the LLM safely."""
    words = text.split()
    chunks = []
    current_chunk = []
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def ask_llm_for_questions(context: str, instruction: str) -> list:
    """Asks the deep LLM to extract questions based on the context and instructions."""
    llm = get_deep_llm(temperature=0.2, keep_alive="5m")
    
    prompt = f"""
    {instruction}
    
    Context:
    {context}
    
    Output the response STRICTLY as a JSON array of objects. Do not wrap it in markdown block quotes (```json). 
    Just output the raw JSON array `[...]`.
    
    Each object must have:
    - "category": string
    - "question_text": string
    - "options": list of 4 strings (A, B, C, D)
    - "correct_answer": string (exactly matching one of the options)
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Clean markdown
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
            
        if content.endswith("```"):
            content = content[:-3]
            
        questions = json.loads(content)
        return questions if isinstance(questions, list) else []
    except Exception as e:
        print(f"LLM parsing failed: {e}")
        return []

def run_phase_1():
    """Phase 1: Parse the two practice exams."""
    print("\n=== PHASE 1: PRACTICE EXAMS ===")
    exams = [
        "data/ab60-practice-exam-final-en.pdf",
        "data/DL-5S-R4-2014-AS-WWW.pdf"
    ]
    
    instruction = "Extract all multiple-choice driving test questions found in the following practice exam text. Ignore everything else."
    
    for exam in exams:
        print(f"\nProcessing {exam}...")
        text = extract_text_from_pdf(exam)
        if not text: continue
        
        chunks = chunk_text(text, 2000)
        for i, chunk in enumerate(chunks):
            print(f"  Scanning chunk {i+1}/{len(chunks)}...")
            questions = ask_llm_for_questions(chunk, instruction)
            for q in questions:
                insert_question_if_unique(q.get("category", "Practice Exam"), q.get("question_text", ""), q.get("options", []), q.get("correct_answer", ""))

def run_phase_2():
    """Phase 2: Targeted extraction for 5 tricky topics from the main DMV handbook."""
    print("\n=== PHASE 2: TRICKY TOPICS ===")
    text = extract_text_from_pdf("data/dmv.pdf")
    if not text: return
    
    topics = [
        "Right-of-Way (Determining who goes first at an uncontrolled intersection)",
        "Curb Colors (Memorizing what white, green, yellow, blue, and red painted curbs signify)",
        "Speed Limits (Understanding limits for school zones and blind railroad crossings)",
        "Under-21 BAC Limits (California’s strict zero-tolerance Blood Alcohol Concentration laws)",
        "Light-Rail Vehicles (Safe driving practices when sharing the road with streetcars or trolleys)"
    ]
    
    chunks = chunk_text(text, 4000)
    for topic in topics:
        print(f"\nTargeting Topic: {topic}")
        instruction = f"Search the following text for information related to '{topic}'. Generate 3 highly tricky and specific multiple choice questions about this rule."
        
        # We only pass chunks that might contain the words to speed it up
        keywords = topic.split()[0].lower().replace("-", " ")
        
        for i, chunk in enumerate(chunks):
            if keywords in chunk.lower() or "speed" in chunk.lower() or "curb" in chunk.lower() or "rail" in chunk.lower() or "bac " in chunk.lower() or "alcohol" in chunk.lower() or "right of way" in chunk.lower() or "intersection" in chunk.lower():
                questions = ask_llm_for_questions(chunk, instruction)
                for q in questions:
                    insert_question_if_unique("Tricky Topics", q.get("question_text", ""), q.get("options", []), q.get("correct_answer", ""))

def run_phase_3():
    """Phase 3: Full sweep of the handbook."""
    print("\n=== PHASE 3: FULL SWEEP ===")
    text = extract_text_from_pdf("data/dmv.pdf")
    if not text: return
    
    instruction = "Generate 3 multiple-choice questions from the following DMV handbook excerpt. Avoid basic questions, focus on specific rules."
    
    chunks = chunk_text(text, 2500)
    for i, chunk in enumerate(chunks):
        print(f"  Scanning handbook chunk {i+1}/{len(chunks)}...")
        questions = ask_llm_for_questions(chunk, instruction)
        for q in questions:
            insert_question_if_unique("General Rules", q.get("question_text", ""), q.get("options", []), q.get("correct_answer", ""))

if __name__ == "__main__":
    init_vector_memory()
    run_phase_1()
    run_phase_2()
    run_phase_3()
    print("\n[Advanced Parser] Pipeline Complete!")
