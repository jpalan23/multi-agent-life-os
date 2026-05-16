from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage
from core.db_manager import db
import operator

class FinanceState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    statement_path: str
    parsed_data: Optional[str]
    kpi_metrics: Optional[dict]
    audit_flags: Optional[str]

def statement_parser(state: FinanceState) -> FinanceState:
    """Extracts data from Bank/Credit Card PDFs."""
    print(f"[Statement Parser] Parsing {state['statement_path']}...")
    return {"parsed_data": "Extracted $500 groceries, $1500 rent."}

def kpi_engine(state: FinanceState) -> FinanceState:
    """Calculates Burn Rate, Savings Rate, and Investment Ratios."""
    print(f"[KPI Engine] Calculating metrics...")
    
    # Save a mock statement to DB
    db.execute_query(
        "INSERT INTO fin_statements (category, amount, date, account_source) VALUES (?, ?, ?, ?)",
        ("Groceries", 500.0, "2026-05-16", "Chase Checking")
    )
    
    return {"kpi_metrics": {"burn_rate": 2000.0, "savings_rate": 0.2}}

def auditor(state: FinanceState) -> FinanceState:
    """Flags unusual spending or upcoming bill cycles."""
    print(f"[Auditor] Auditing finances...")
    return {"audit_flags": "Unusual high spending on dining detected."}

def build_finance_graph():
    builder = StateGraph(FinanceState)
    
    builder.add_node("statement_parser", statement_parser)
    builder.add_node("kpi_engine", kpi_engine)
    builder.add_node("auditor", auditor)
    
    builder.add_edge(START, "statement_parser")
    builder.add_edge("statement_parser", "kpi_engine")
    builder.add_edge("kpi_engine", "auditor")
    builder.add_edge("auditor", END)
    
    return builder.compile()

if __name__ == "__main__":
    graph = build_finance_graph()
    initial_state = {"messages": [], "statement_path": "statement_may.pdf", "parsed_data": None, "kpi_metrics": None, "audit_flags": None}
    for s in graph.stream(initial_state):
        print(s)
        print("---")
