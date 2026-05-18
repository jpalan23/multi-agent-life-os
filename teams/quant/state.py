from typing import TypedDict, Annotated, Sequence, Optional, List
import operator
from langchain_core.messages import BaseMessage

class QuantState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    ticker: str
    date: str
    
    # Discovery
    scanned_tickers: Optional[List[str]]
    
    # Analyst outputs
    fundamental_data: Optional[str]
    market_data: Optional[str]
    news_data: Optional[str]
    earnings_insights: Optional[str]
    alternative_data: Optional[str] # Reddit, Google Search, etc.
    
    # Debate state
    bull_arguments: Optional[str]
    bear_arguments: Optional[str]
    debate_round: int
    max_debate_rounds: int
    
    # Simulation context
    archetype: Optional[str] # "The Oak", "The Maverick", etc.
    
    # Decisions
    risk_assessment: Optional[str]
    risk_approved: bool
    final_decision: Optional[str] # "BUY", "SELL", "HOLD"
    execution_details: Optional[str]
