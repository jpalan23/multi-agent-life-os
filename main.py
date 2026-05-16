from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, HumanMessage
from core.llm_factory import get_llm
from teams.quant.trading_graph import build_quant_graph
from teams.career.career_graph import build_career_graph
from teams.finance.finance_graph import build_finance_graph
from teams.dmv_tutor.tutor_graph import build_tutor_graph
from teams.dmv_tutor.scheduler import start_scheduler

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
    - Tutor: For DMV practice quizzes, driving written test, or replying 'ready' to the daily ping.
    - Unknown: If it doesn't fit the above.
    
    Query: "{query}"
    
    Reply with ONLY the team name (Quant, Career, Finance, Tutor, or Unknown).
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    route = response.content.strip().replace(".", "").replace('"', '')
    return route

def run_system(query: str, thread_id: str = "default_session") -> dict:
    """Entry point to process a user query and return a dict with text and optional image_path."""
    print(f"[Supervisor] Received Query: {query}")
    route = supervisor_router(query)
    print(f"[Supervisor] Routing to: {route} Team")
    
    final_response = {"text": "Sorry, I couldn't process that.", "image_path": None}
    
    if "Quant" in route:
        graph = build_quant_graph()
        state = {"messages": [], "ticker": "NVDA", "date": "2026-05-16"} # Hardcoded for now
        config = {"configurable": {"thread_id": thread_id}}
        for s in graph.stream(state, config=config):
            pass
        curr_state = graph.get_state(config).values
        if curr_state.get('execution_details'):
            final_response["text"] = f"Quant Decision: {curr_state.get('final_decision')}\n{curr_state.get('execution_details')}"
        else:
            final_response["text"] = "Quant analysis completed."
            
    elif "Career" in route:
        final_response["text"] = "Career Catalyst is currently mocked in V1."
            
    elif "Finance" in route:
        final_response["text"] = "Household Accountant is currently mocked in V1."
            
    elif "Tutor" in route:
        graph = build_tutor_graph()
        config = {"configurable": {"thread_id": f"dmv_tutor_{thread_id}"}}
        for s in graph.stream({"messages": [HumanMessage(content=query)]}, config=config):
            for node, state in s.items():
                if 'messages' in state:
                    msg = state['messages'][-1]
                    final_response["text"] = msg.content
                    final_response["image_path"] = msg.additional_kwargs.get("image_path")
            
    else:
        final_response["text"] = "[Supervisor] I am not sure how to handle this query."
        
    return final_response

if __name__ == "__main__":
    import sys
    
    # Start the background scheduler for daily pings
    start_scheduler()
    
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "What is the recent news and fundamental data for NVDA?"
        
    try:
        run_system(user_query)
    except Exception as e:
        print(f"System execution error: {e}")
