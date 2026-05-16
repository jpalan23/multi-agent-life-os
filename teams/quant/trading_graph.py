from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from core.llm_factory import get_llm
from core.db_manager import db
import operator

# Define the State for the Quant Team
class QuantState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    ticker: str
    fundamental_data: Optional[str]
    sentiment_data: Optional[str]
    final_report: Optional[str]

# Define the Nodes (Agents)
def fundamental_analyst(state: QuantState) -> QuantState:
    """Evaluates stock health based on basic fundamental mock data."""
    print(f"[Fundamental Analyst] Analyzing {state['ticker']}...")
    # In a real app, we would fetch API data here (e.g., yfinance)
    mock_fundamentals = f"{state['ticker']} has a healthy P/E ratio and strong quarterly revenue growth."
    
    # We could use the LLM to format/analyze the data
    llm = get_llm(temperature=0.1)
    prompt = f"Analyze the following fundamental data for {state['ticker']}: {mock_fundamentals}. Keep it brief."
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"fundamental_data": response.content}

def sentiment_agent(state: QuantState) -> QuantState:
    """Scrapes/evaluates financial news for sentiment."""
    print(f"[Sentiment Agent] Checking news for {state['ticker']}...")
    # In a real app, this would scrape news sites
    mock_news = f"Recent news for {state['ticker']} shows positive momentum and new product launches."
    
    llm = get_llm(temperature=0.1)
    prompt = f"Determine the sentiment (Bullish, Bearish, or Neutral) based on this news: {mock_news}. Explain briefly."
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"sentiment_data": response.content}

def reporter(state: QuantState) -> QuantState:
    """Generates a daily summary and saves it to the database."""
    print(f"[Reporter] Generating report for {state['ticker']}...")
    
    llm = get_llm(temperature=0.3)
    prompt = f"""
    Create a final investment report for {state['ticker']} based on:
    Fundamental Analysis: {state['fundamental_data']}
    Sentiment Analysis: {state['sentiment_data']}
    
    Provide a clear BUY, HOLD, or SELL recommendation.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    final_report = response.content
    
    # Extract sentiment score (Mocking a 0-100 score for DB based on content)
    sentiment_score = 80.0 if "Bullish" in str(state['sentiment_data']) else (20.0 if "Bearish" in str(state['sentiment_data']) else 50.0)
    
    # Save to database
    db.execute_query(
        "INSERT INTO market_reports (ticker, sentiment_score, summary) VALUES (?, ?, ?)",
        (state['ticker'], sentiment_score, final_report)
    )
    
    return {
        "final_report": final_report,
        "messages": [AIMessage(content=final_report)]
    }

# Build the Graph
def build_quant_graph():
    builder = StateGraph(QuantState)
    
    # Add nodes
    builder.add_node("fundamental_analyst", fundamental_analyst)
    builder.add_node("sentiment_agent", sentiment_agent)
    builder.add_node("reporter", reporter)
    
    # Define edges (Flow)
    builder.add_edge(START, "fundamental_analyst")
    builder.add_edge("fundamental_analyst", "sentiment_agent")
    builder.add_edge("sentiment_agent", "reporter")
    builder.add_edge("reporter", END)
    
    return builder.compile()

# For easy testing
if __name__ == "__main__":
    graph = build_quant_graph()
    initial_state = {"messages": [], "ticker": "AAPL", "fundamental_data": None, "sentiment_data": None, "final_report": None}
    
    for s in graph.stream(initial_state):
        print(s)
        print("---")
