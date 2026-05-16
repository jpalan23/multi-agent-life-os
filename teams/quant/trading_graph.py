import os
import sqlite3
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from teams.quant.state import QuantState
from teams.quant.nodes import (
    market_analyst,
    fundamental_analyst,
    bull_researcher,
    bear_researcher,
    trader_decision,
    risk_manager,
    execution_agent
)

def debate_router(state: QuantState) -> Literal["trader_decision", "bull_researcher"]:
    """Routes the debate. If max rounds reached, goes to trader. Else, continues debate."""
    round = state.get("debate_round", 1)
    max_rounds = state.get("max_debate_rounds", 2)
    
    if round > max_rounds:
        return "trader_decision"
    return "bull_researcher"

def build_quant_graph():
    builder = StateGraph(QuantState)
    
    # Add nodes
    builder.add_node("market_analyst", market_analyst)
    builder.add_node("fundamental_analyst", fundamental_analyst)
    builder.add_node("bull_researcher", bull_researcher)
    builder.add_node("bear_researcher", bear_researcher)
    builder.add_node("trader_decision", trader_decision)
    builder.add_node("risk_manager", risk_manager)
    builder.add_node("execution_agent", execution_agent)
    
    # Define edges
    builder.add_edge(START, "market_analyst")
    builder.add_edge(START, "fundamental_analyst")
    
    # Start debate after analysis
    builder.add_edge("market_analyst", "bull_researcher")
    builder.add_edge("fundamental_analyst", "bull_researcher")
    
    # Debate loop
    builder.add_edge("bull_researcher", "bear_researcher")
    builder.add_conditional_edges("bear_researcher", debate_router)
    
    # Execution flow
    builder.add_edge("trader_decision", "risk_manager")
    builder.add_edge("risk_manager", "execution_agent")
    builder.add_edge("execution_agent", END)
    
    # Setup Checkpointer (SqliteSaver)
    db_path = os.path.join("data", "quant_checkpoints.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    
    return builder.compile(checkpointer=memory)

# For easy testing
if __name__ == "__main__":
    from datetime import datetime
    import sys
    
    graph = build_quant_graph()
    
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    initial_state = {
        "messages": [], 
        "ticker": ticker, 
        "date": datetime.now().strftime("%Y-%m-%d"),
        "fundamental_data": None, 
        "market_data": None, 
        "bull_arguments": None,
        "bear_arguments": None,
        "debate_round": 1,
        "max_debate_rounds": 2,
        "risk_assessment": None,
        "risk_approved": False,
        "final_decision": None,
        "execution_details": None
    }
    
    config = {"configurable": {"thread_id": f"test_run_{ticker}_{initial_state['date']}"}}
    
    for s in graph.stream(initial_state, config=config):
        print("--- Node completed ---")
