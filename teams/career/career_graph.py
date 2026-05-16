from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage
from core.llm_factory import get_llm
from core.db_manager import db
import operator

# Define the State for the Career Team
class CareerState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    job_description: str
    scraped_jobs: Optional[str]
    resume_tailored: Optional[str]
    mentor_feedback: Optional[str]
    confidence_score: Optional[int]

def job_scraper(state: CareerState) -> CareerState:
    """Monitors job boards for relevant roles."""
    print(f"[Job Scraper] Finding jobs matching criteria...")
    mock_jobs = "Found Senior Full Stack role at TechCorp requiring React, Node.js, and System Design."
    return {"scraped_jobs": mock_jobs}

def resume_tailor(state: CareerState) -> CareerState:
    """Auto-aligns CV with JD keywords."""
    print(f"[Resume Tailor] Tailoring resume...")
    # Skip actual LLM call for now to avoid ConnectionRefused if LLM is offline
    return {"resume_tailored": "Tailored resume highlighting React and Node.js."}

def senior_mentor(state: CareerState) -> CareerState:
    """Tracks progress and provides System Design feedback."""
    print(f"[Senior Mentor] Providing feedback...")
    return {"mentor_feedback": "Need to improve System Design for distributed systems."}

def syllabus_tracker(state: CareerState) -> CareerState:
    """Maps JD requirements to a learning Confidence Score."""
    print(f"[Syllabus Tracker] Updating DB with confidence score...")
    
    topic = "System Design"
    confidence_score = 6
    
    try:
        db.execute_query(
            "INSERT INTO skill_matrix (topic, confidence_level) VALUES (?, ?)",
            (topic, confidence_score)
        )
    except Exception:
        db.execute_query(
            "UPDATE skill_matrix SET confidence_level = ? WHERE topic = ?",
            (confidence_score, topic)
        )
        
    return {"confidence_score": confidence_score}

def build_career_graph():
    builder = StateGraph(CareerState)
    
    builder.add_node("job_scraper", job_scraper)
    builder.add_node("resume_tailor", resume_tailor)
    builder.add_node("senior_mentor", senior_mentor)
    builder.add_node("syllabus_tracker", syllabus_tracker)
    
    builder.add_edge(START, "job_scraper")
    builder.add_edge("job_scraper", "resume_tailor")
    builder.add_edge("resume_tailor", "senior_mentor")
    builder.add_edge("senior_mentor", "syllabus_tracker")
    builder.add_edge("syllabus_tracker", END)
    
    return builder.compile()

if __name__ == "__main__":
    graph = build_career_graph()
    initial_state = {"messages": [], "job_description": "Senior Full Stack", "scraped_jobs": None, "resume_tailored": None, "mentor_feedback": None, "confidence_score": None}
    for s in graph.stream(initial_state):
        print(s)
        print("---")
