import os
import sqlite3
import json
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, List, Dict, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from core.llm_factory import get_quick_llm
from core.db_manager import db

class TutorState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_questions: List[Dict]
    current_question_index: int
    user_answers: List[str]
    session_score: int
    quiz_completed: bool

def fetch_questions(state: TutorState) -> TutorState:
    """Fetches 10 questions from the DB, prioritizing failed ones and mixing categories."""
    if state.get("session_questions"):
        return {} # Already fetched
        
    print("[Tutor] Fetching daily questions...")
    # Fetch failed questions first
    query = """
        SELECT * FROM dmv_questions 
        ORDER BY times_failed DESC, last_asked ASC 
        LIMIT 10
    """
    results = db.execute_query(query)
    
    questions = []
    for r in results:
        q = dict(r)
        q['options'] = json.loads(q['options'])
        questions.append(q)
        
    return {
        "session_questions": questions,
        "current_question_index": 0,
        "user_answers": [],
        "session_score": 0,
        "quiz_completed": False
    }

def ask_question(state: TutorState) -> TutorState:
    """Formats and sends the current question to the user."""
    idx = state.get("current_question_index", 0)
    questions = state.get("session_questions", [])
    
    if idx >= len(questions):
        return {"quiz_completed": True}
        
    q = questions[idx]
    
    msg_text = f"Question {idx + 1}/{len(questions)}: [{q['category']}]\n\n{q['question_text']}\n"
    for opt in q['options']:
        msg_text += f"{opt}\n"
        
    msg_text += "\nReply with the letter of your answer (e.g., 'A')."
    
    print(f"[Tutor] Asking question {idx+1}")
    
    kwargs = {}
    if q.get('image_path'):
        kwargs["image_path"] = q['image_path']
        print(f"[Tutor] Including image: {q['image_path']}")
        
    return {"messages": [AIMessage(content=msg_text, additional_kwargs=kwargs)]}

def grade_answer(state: TutorState) -> TutorState:
    """Grades the user's latest response."""
    last_message = state['messages'][-1].content.strip().upper()
    
    idx = state.get("current_question_index", 0)
    questions = state.get("session_questions", [])
    
    if idx >= len(questions):
        return {}
        
    q = questions[idx]
    correct_ans = q['correct_answer']
    
    # Simple check if the user's message starts with the correct letter
    # Extract the correct letter from the option, e.g. "A) Red" -> "A"
    correct_letter = correct_ans[0].upper() if correct_ans else ""
    
    is_correct = last_message.startswith(correct_letter)
    
    # Update DB
    db.execute_query(
        "UPDATE dmv_questions SET times_asked = times_asked + 1, last_asked = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), q['id'])
    )
    if not is_correct:
        db.execute_query(
            "UPDATE dmv_questions SET times_failed = times_failed + 1 WHERE id = ?",
            (q['id'],)
        )
        
    new_score = state.get("session_score", 0) + (1 if is_correct else 0)
    user_answers = list(state.get("user_answers", []))
    user_answers.append(last_message)
    
    feedback = f"Correct! ✅" if is_correct else f"Incorrect. ❌ The correct answer was {correct_ans}."
    
    return {
        "current_question_index": idx + 1,
        "session_score": new_score,
        "user_answers": user_answers,
        "messages": [AIMessage(content=feedback)]
    }

def generate_summary(state: TutorState) -> TutorState:
    """Generates a summary of the quiz using the LLM."""
    print("[Tutor] Generating summary...")
    questions = state.get("session_questions", [])
    user_answers = state.get("user_answers", [])
    score = state.get("session_score", 0)
    
    llm = get_quick_llm(temperature=0.2)
    
    # Find wrong answers to explain
    wrong_context = ""
    for idx, q in enumerate(questions):
        # We assume lengths match up to score
        if idx < len(user_answers):
            correct_letter = q['correct_answer'][0].upper() if q['correct_answer'] else ""
            if not user_answers[idx].startswith(correct_letter):
                wrong_context += f"- Question: {q['question_text']}\n  She answered: {user_answers[idx]}\n  Correct: {q['correct_answer']}\n\n"
                
    prompt = f"""
    You are a friendly driving instructor. Your student just finished a 10-question DMV practice quiz.
    She scored {score}/10.
    
    Here are the questions she got wrong:
    {wrong_context if wrong_context else "None! Perfect score!"}
    
    Provide a brief, encouraging summary and explain the concepts she missed in a simple, easy-to-understand way.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    summary_msg = f"Quiz Complete! Your score: {score}/10\n\n{response.content}"
    
    return {"quiz_completed": True, "messages": [AIMessage(content=summary_msg)]}

def tutor_router(state: TutorState) -> Literal["grade_answer", "fetch_questions", "generate_summary"]:
    """Routes based on whether questions are fetched and quiz is complete."""
    if not state.get("session_questions"):
        return "fetch_questions"
        
    if state.get("quiz_completed"):
        return "generate_summary"
        
    return "grade_answer"

def grade_router(state: TutorState) -> Literal["ask_question", "generate_summary"]:
    idx = state.get("current_question_index", 0)
    questions = state.get("session_questions", [])
    if idx >= len(questions) or len(questions) == 0:
        return "generate_summary"
    return "ask_question"

def build_tutor_graph():
    builder = StateGraph(TutorState)
    
    builder.add_node("fetch_questions", fetch_questions)
    builder.add_node("ask_question", ask_question)
    builder.add_node("grade_answer", grade_answer)
    builder.add_node("generate_summary", generate_summary)
    
    builder.add_conditional_edges(START, tutor_router)
    
    builder.add_edge("fetch_questions", "ask_question")
    builder.add_edge("ask_question", END) # End graph to wait for user input
    
    builder.add_conditional_edges("grade_answer", grade_router)
    builder.add_edge("generate_summary", END)
    
    # Setup Checkpointer (SqliteSaver)
    db_path = os.path.join("data", "tutor_checkpoints.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    
    return builder.compile(checkpointer=memory)

# Basic testing function
def run_tutor_test():
    graph = build_tutor_graph()
    config = {"configurable": {"thread_id": "test_tutor_thread"}}
    
    print("--- Starting Tutor ---")
    
    # Initial trigger
    for s in graph.stream({"messages": [HumanMessage(content="ready")]}, config=config):
        for node, state in s.items():
            if 'messages' in state:
                print(state['messages'][-1].content)
                
    # Loop for user input
    while True:
        try:
            user_input = input("Your answer: ")
            if user_input.lower() in ["quit", "exit"]:
                break
                
            for s in graph.stream({"messages": [HumanMessage(content=user_input)]}, config=config):
                for node, state in s.items():
                    if 'messages' in state:
                        print(state['messages'][-1].content)
                        
            # If quiz completed, break
            curr_state = graph.get_state(config).values
            if curr_state.get("quiz_completed"):
                break
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    run_tutor_test()
