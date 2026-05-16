from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, HumanMessage
from core.llm_factory import get_llm
from teams.quant.trading_graph import build_quant_graph
from teams.career.career_graph import build_career_graph
from teams.finance.finance_graph import build_finance_graph

class SupervisorState(TypedDict):
    messages: Sequence[BaseMessage]
    query: str
    route: Optional[str]
    final_response: Optional[str]

def supervisor_router(query: str) -> str:
    """Uses LLM to determine the appropriate team for the query."""
    llm = get_llm(temperature=0.0)
    prompt = f"""
    You are the Central Supervisor for a Multi-Agent Life-OS.
    Route the following query to one of the specific teams:
    - Quant: For stock market, trading, fundamentals, and finance news.
    - Career: For job searching, resume tailoring, and interview prep.
    - Finance: For personal finance, statements, burn rate, and budgets.
    - Unknown: If it doesn't fit the above.
    
    Query: "{query}"
    
    Reply with ONLY the team name (Quant, Career, Finance, or Unknown).
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    route = response.content.strip().replace(".", "").replace('"', '')
    return route

def run_system(query: str):
    """Entry point to process a user query."""
    print(f"[Supervisor] Received Query: {query}")
    route = supervisor_router(query)
    print(f"[Supervisor] Routing to: {route} Team")
    
    # We use mock data for the specific team states since it's just routing test
    if "Quant" in route:
        graph = build_quant_graph()
        # In a real app we'd extract the ticker from the query
        state = {"messages": [], "ticker": "AAPL", "fundamental_data": None, "sentiment_data": None, "final_report": None}
        print("--- Executing Quant Graph ---")
        for s in graph.stream(state):
            print(list(s.keys())[0], "completed.")
            
    elif "Career" in route:
        graph = build_career_graph()
        state = {"messages": [], "job_description": query, "scraped_jobs": None, "resume_tailored": None, "mentor_feedback": None, "confidence_score": None}
        print("--- Executing Career Graph ---")
        for s in graph.stream(state):
            print(list(s.keys())[0], "completed.")
            
    elif "Finance" in route:
        graph = build_finance_graph()
        state = {"messages": [], "statement_path": "latest_statement.pdf", "parsed_data": None, "kpi_metrics": None, "audit_flags": None}
        print("--- Executing Finance Graph ---")
        for s in graph.stream(state):
            print(list(s.keys())[0], "completed.")
            
    else:
        print("[Supervisor] I am not sure how to handle this query.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "What is the recent news and fundamental data for NVDA?"
        
    try:
        run_system(user_query)
    except Exception as e:
        print(f"System execution error: {e}")
