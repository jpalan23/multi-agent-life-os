from core.db_manager import db
import os

try:
    print("Testing DB Manager initialization...")
    print(f"Database path: {db.db_path}")
    
    # Test inserting and reading
    print("Testing basic operations...")
    db.execute_query("INSERT INTO skill_matrix (topic, confidence_level) VALUES (?, ?)", ("Python", 8))
    results = db.execute_query("SELECT * FROM skill_matrix")
    
    for row in results:
        print(f"Skill: {row['topic']}, Confidence: {row['confidence_level']}")
        
    # Clean up test
    db.execute_query("DELETE FROM skill_matrix WHERE topic = ?", ("Python",))
    
    print("DB Manager test successful!")
except Exception as e:
    print(f"Error during DB test: {e}")
