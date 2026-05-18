import asyncio
import sys
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage
from core.llm_factory import get_llm, get_deep_llm
from teams.quant.trading_graph import build_quant_graph
from teams.career.career_graph import build_career_graph
from teams.finance.finance_graph import build_finance_graph
from teams.dmv_tutor.tutor_graph import build_tutor_graph
from core.scheduler import start_scheduler
from core.task_manager import task_manager

async def supervisor_router(query: str) -> str:
    """Uses LLM to determine the appropriate team for the query."""
    # Use the quick LLM for routing
    llm = get_llm(temperature=0.0, keep_alive="5m")
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
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    route = response.content.strip().replace(".", "").replace('"', '')
    return route

# --- Task Handlers ---

async def handle_quant_task(payload: Dict[str, Any]):
    query = payload.get("query")
    thread_id = payload.get("thread_id", "default_session")
    print(f"[Quant] Processing: {query}")
    
    graph = build_quant_graph()
    state = {"messages": [HumanMessage(content=query)], "ticker": payload.get("ticker", "NVDA"), "date": "2026-05-16"}
    config = {"configurable": {"thread_id": thread_id}}
    
    async for s in graph.astream(state, config=config):
        pass
    
    curr_state = await graph.aget_state(config)
    values = curr_state.values
    if values.get('execution_details'):
        print(f"[Quant] Decision: {values.get('final_decision')}\n{values.get('execution_details')}")
    else:
        print("[Quant] Analysis completed.")

async def handle_career_task(payload: Dict[str, Any]):
    print("[Career] Processing: Mocked in V1.")
    await asyncio.sleep(1) # Simulate work

async def handle_finance_task(payload: Dict[str, Any]):
    print("[Finance] Processing: Mocked in V1.")
    await asyncio.sleep(1) # Simulate work

async def handle_tutor_task(payload: Dict[str, Any]):
    query = payload.get("query")
    thread_id = payload.get("thread_id", "default_session")
    print(f"[Tutor] Processing: {query}")
    
    graph = build_tutor_graph()
    config = {"configurable": {"thread_id": f"dmv_tutor_{thread_id}"}}
    
    async for s in graph.astream({"messages": [HumanMessage(content=query)]}, config=config):
        for node, state in s.items():
            if 'messages' in state:
                msg = state['messages'][-1]
                print(f"[Tutor] Response: {msg.content}")

# --- System Logic ---

async def run_system(query: str, thread_id: str = "default_session"):
    """Determines the route and adds a task to the queue."""
    print(f"[Supervisor] Received Query: {query}")
    route = await supervisor_router(query)
    print(f"[Supervisor] Routing to: {route} Team")
    
    priority = 2 # Moderate default
    if "Tutor" in route:
        priority = 0 # High priority for direct human interaction
    elif "Quant" in route:
        priority = 1 # Time-sensitive
        
    if route in ["Quant", "Career", "Finance", "Tutor"]:
        await task_manager.add_task(route, {"query": query, "thread_id": thread_id}, priority=priority)
    else:
        print(f"[Supervisor] Unknown route for query: {query}")

async def main():
    # Register handlers
    task_manager.register_handler("Quant", handle_quant_task)
    task_manager.register_handler("Career", handle_career_task)
    task_manager.register_handler("Finance", handle_finance_task)
    task_manager.register_handler("Tutor", handle_tutor_task)
    
    # Restore and start worker
    await task_manager.restore_pending_tasks()
    asyncio.create_task(task_manager.start_worker())
    
    # Start the background scheduler for daily pings
    start_scheduler()
    
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "What is the recent news and fundamental data for NVDA?"
        
    try:
        await run_system(user_query)
        # Keep the script running if there are pending tasks
        while not task_manager.queue.empty() or task_manager.is_running:
            await asyncio.sleep(1)
            # Add a break condition or just let the user Ctrl+C
            if task_manager.queue.empty():
                # Check if currently processing
                processing = db.execute_query("SELECT COUNT(*) as count FROM task_queue WHERE status = 'PROCESSING'")[0]['count']
                if processing == 0:
                    break
    except Exception as e:
        print(f"System execution error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
