import os
import sqlite3
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from teams.quant.state import QuantState
from teams.quant.nodes import (
    market_scout,
    market_analyst,
    fundamental_analyst,
    earnings_analyst,
    alternative_data_analyst,
    portfolio_manager,
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
    builder.add_node("earnings_analyst", earnings_analyst)
    builder.add_node("alternative_data_analyst", alternative_data_analyst)
    builder.add_node("portfolio_manager", portfolio_manager)
    builder.add_node("bull_researcher", bull_researcher)
    builder.add_node("bear_researcher", bear_researcher)
    builder.add_node("trader_decision", trader_decision)
    builder.add_node("risk_manager", risk_manager)
    builder.add_node("execution_agent", execution_agent)
    
    # Define edges
    # Stage 1: Parallel Analysis
    builder.add_edge(START, "market_analyst")
    builder.add_edge(START, "fundamental_analyst")
    builder.add_edge(START, "earnings_analyst")
    builder.add_edge(START, "alternative_data_analyst")
    
    # Stage 2: Strategy Layer (CIO)
    # Portfolio manager needs the data from analysts to set strategy
    builder.add_edge("market_analyst", "portfolio_manager")
    builder.add_edge("fundamental_analyst", "portfolio_manager")
    builder.add_edge("earnings_analyst", "portfolio_manager")
    builder.add_edge("alternative_data_analyst", "portfolio_manager")
    
    # Stage 3: Persona Researchers
    builder.add_edge("portfolio_manager", "bull_researcher")
    
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
