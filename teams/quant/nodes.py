from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm_factory import get_quick_llm, get_deep_llm
from core.db_manager import db
from core.vector_store import vector_db
from core.price_oracle import price_oracle
from teams.quant.tools import (
    get_stock_price, 
    get_stock_info, 
    get_company_news, 
    get_earnings_transcript,
    get_market_movers,
    get_unusual_volume,
    get_reddit_sentiment,
    get_google_search_analysis
)
from teams.quant.state import QuantState
from teams.quant.archetypes import ARCHETYPES

# --- Strategy Layer ---

def portfolio_manager(state: QuantState) -> QuantState:
    """Analyzes the strawberry portfolio and market regime to set top-level strategy."""
    print("[Portfolio Manager] Analyzing market regime and strawberry allocation...")
    
    # Fetch User Goals
    goals = db.execute_query("SELECT goal_description FROM user_goals WHERE goal_key = 'PRIMARY'")
    user_goal = goals[0]['goal_description'] if goals else "No goal defined."
    
    # Fetch Portfolio Status (All Agents)
    portfolio = db.execute_query("SELECT * FROM strawberry_portfolio")
    holdings = db.execute_query("SELECT * FROM strawberry_holdings")
    
    context = f"""
    User Primary Goal: {user_goal}
    Current Market Data: {state['market_data']}
    Current News/Sentiment: {state['news_data']}
    Portfolio Balances: {portfolio}
    Agent Holdings: {holdings}
    """
    
    # Use Deep LLM for strategic planning
    llm = get_deep_llm(temperature=0.1, keep_alive="5m")
    prompt = f"""
    You are the Chief Investment Officer (CIO). 
    Based on the following context, set a mandatory High-Level Strategy for the next week.
    Your strategy should guide the individual archetypes (The Oak, The Maverick, etc.).
    
    CONTEXT:
    {context}
    
    RESPOND with a concise strategy (max 3 sentences).
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {
        "user_goals": user_goal,
        "portfolio_strategy": response.content,
        "portfolio_summary": {"balances": portfolio, "holdings": holdings}
    }

# --- Analyst Layer ---

def market_analyst(state: QuantState) -> QuantState:
    """Fetches real-time market data (prices, volume) and news."""
    print(f"[Market Analyst] Fetching market data & news for {state['ticker']}...")
    price = price_oracle.get_last_price(state['ticker'])
    price_info = f"The latest price for {state['ticker']} is {price:.2f} Strawberries." if price else get_stock_price(state['ticker'])
    news = get_company_news(state['ticker'])
    return {"market_data": price_info, "news_data": news}

def fundamental_analyst(state: QuantState) -> QuantState:
    """Fetches real fundamental data via yfinance."""
    print(f"[Fundamental Analyst] Fetching fundamentals for {state['ticker']}...")
    info = get_stock_info(state['ticker'])
    llm = get_quick_llm(temperature=0.1, keep_alive="5m")
    prompt = f"Summarize the following fundamental data for {state['ticker']} into a concise analyst report:\n{info}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"fundamental_data": response.content}

def earnings_analyst(state: QuantState) -> QuantState:
    """Fetches and analyzes the latest earnings transcript."""
    print(f"[Earnings Analyst] Analyzing latest transcript for {state['ticker']}...")
    transcript = get_earnings_transcript(state['ticker'])
    if "Skipping" in transcript or "No transcripts found" in transcript:
        return {"earnings_insights": transcript}
    llm = get_quick_llm(temperature=0.1, keep_alive="5m")
    prompt = f"Analyze the following earnings transcript snippet for {state['ticker']}. Extract key strategic direction, revenue guidance, and risks.\n\nTranscript: {transcript}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"earnings_insights": response.content}

def alternative_data_analyst(state: QuantState) -> QuantState:
    """Synthesizes data from Reddit sentiment and Google searches."""
    print(f"[Alt-Data Analyst] Analyzing Reddit & Web Research for {state['ticker']}...")
    reddit = get_reddit_sentiment(state['ticker'])
    google = get_google_search_analysis(state['ticker'])
    llm = get_quick_llm(temperature=0.1, keep_alive="5m")
    prompt = f"Synthesize the following alternative data for {state['ticker']} into a brief sentiment report.\nReddit Context: {reddit}\nWeb Research: {google}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"alternative_data": response.content}

def market_scout(state: QuantState) -> QuantState:
    """Discovers high-signal tickers autonomously."""
    print("[Market Scout] Scanning for top movers and unusual volume...")
    movers = get_market_movers()
    volume = get_unusual_volume()
    all_discovered = list(set(movers + volume))
    for ticker in all_discovered:
        db.execute_query("INSERT OR IGNORE INTO watchlist (ticker, source, reason) VALUES (?, ?, ?)", (ticker, 'SCOUT', 'Discovered by Scout'))
    return {"scanned_tickers": all_discovered}

# --- Researcher Layer ---

def bull_researcher(state: QuantState) -> QuantState:
    """Argues the bull case based on data and CIO strategy."""
    print(f"[Bull Researcher] Preparing bull thesis for {state['ticker']}...")
    llm = get_deep_llm(temperature=0.3, keep_alive="5m")
    context = f"Strategy: {state['portfolio_strategy']}\nMarket Data: {state['market_data']}\nFundamentals: {state['fundamental_data']}\nNews: {state['news_data']}\nEarnings: {state['earnings_insights']}\nAlt-Data: {state['alternative_data']}"
    prompt = f"You are a Bullish Researcher. Argue why we should BUY {state['ticker']} in Strawberries. Alignment with CIO Strategy is MANDATORY. Context:\n{context}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"bull_arguments": response.content}

def bear_researcher(state: QuantState) -> QuantState:
    """Argues the bear case based on data and CIO strategy."""
    print(f"[Bear Researcher] Preparing bear thesis for {state['ticker']}...")
    llm = get_deep_llm(temperature=0.3, keep_alive="5m")
    context = f"Strategy: {state['portfolio_strategy']}\nMarket Data: {state['market_data']}\nFundamentals: {state['fundamental_data']}\nNews: {state['news_data']}\nEarnings: {state['earnings_insights']}\nAlt-Data: {state['alternative_data']}"
    prompt = f"You are a Bearish Researcher. Argue why we should SELL/HOLD {state['ticker']} in Strawberries. Alignment with CIO Strategy is MANDATORY. Context:\n{context}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"bear_arguments": response.content, "debate_round": state.get('debate_round', 1) + 1}

# --- Decision Layer ---

def trader_decision(state: QuantState) -> QuantState:
    """Makes a decision based on the debate and the CIO's high-level strategy."""
    archetype_name = state.get("archetype", "The Oak")
    print(f"[Trader] {archetype_name} deciding on {state['ticker']}...")
    llm = get_deep_llm(temperature=0.1, keep_alive="0")
    archetype_prompt = f"\nYOUR PERSONA: {ARCHETYPES.get(archetype_name, {}).get('system_prompt', '')}"
    prompt = f"You are the Lead Trader.{archetype_prompt}\nCIO STRATEGY: {state['portfolio_strategy']}\nDecide to BUY, SELL, or HOLD {state['ticker']}.\nBull Case: {state['bull_arguments']}\nBear Case: {state['bear_arguments']}\nRespond with ONLY action (BUY, SELL, HOLD) on line 1, then a brief persona-aligned justification."
    response = llm.invoke([HumanMessage(content=prompt)], config={"tags": [f"Trader: {archetype_name}"]})
    content = response.content.strip().split('\n')
    action = content[0].strip().replace(".", "").upper()
    justification = "\n".join(content[1:]).strip()
    return {"final_decision": action if action in ["BUY", "SELL", "HOLD"] else "HOLD", "execution_details": justification}

def risk_manager(state: QuantState) -> QuantState:
    """Checks Strawberry balance and portfolio risk."""
    archetype_name = state.get("archetype", "The Oak")
    print(f"[Risk Manager] Assessing Strawberry risk for {archetype_name} on {state['ticker']}...")
    
    if state['final_decision'] == "HOLD":
        return {"risk_approved": True, "risk_assessment": "Hold requires no Strawberries."}
        
    try:
        # Initialize agent if not exists
        db.execute_query("INSERT OR IGNORE INTO strawberry_portfolio (agent_name) VALUES (?)", (archetype_name,))
        
        agent_data = db.execute_query("SELECT strawberry_balance FROM strawberry_portfolio WHERE agent_name = ?", (archetype_name,))
        holding_data = db.execute_query("SELECT quantity FROM strawberry_holdings WHERE agent_name = ? AND ticker = ?", (archetype_name, state['ticker']))
        
        balance = agent_data[0]['strawberry_balance'] if agent_data else 0.0
        qty_owned = holding_data[0]['quantity'] if holding_data else 0.0
        
        approved = False
        assessment = ""
        
        if state['final_decision'] == "BUY":
            if balance >= 100: # Min 100 Strawberries to buy
                approved = True
                assessment = f"Approved BUY. Agent {archetype_name} has {balance:.2f} 🍓."
            else:
                assessment = f"Rejected BUY. Agent {archetype_name} has only {balance:.2f} 🍓."
        elif state['final_decision'] == "SELL":
            if qty_owned > 0:
                approved = True
                assessment = f"Approved SELL. Agent {archetype_name} owns {qty_owned} {state['ticker']}."
            else:
                assessment = f"Rejected SELL. Agent {archetype_name} owns zero shares."
                
        return {"risk_approved": approved, "risk_assessment": assessment, "final_decision": state['final_decision'] if approved else "HOLD"}
    except Exception as e:
        return {"risk_approved": False, "risk_assessment": str(e), "final_decision": "HOLD"}

def execution_agent(state: QuantState) -> QuantState:
    """Executes the trade in the Strawberry Economy."""
    archetype_name = state.get("archetype", "The Oak")
    print(f"[Execution Agent] Finalizing Strawberry trade for {archetype_name}: {state['final_decision']}")
    
    if state['final_decision'] in ["BUY", "SELL"]:
        price = price_oracle.get_last_price(state['ticker'])
        if not price:
            try: price = float(state['market_data'].split('$')[-1].split(' ')[0])
            except: price = 100.0
            
        qty = 10.0 # Standard batch size
        total_strawberries = price * qty
        
        try:
            if state['final_decision'] == "BUY":
                db.execute_query("UPDATE strawberry_portfolio SET strawberry_balance = strawberry_balance - ? WHERE agent_name = ?", (total_strawberries, archetype_name))
                db.execute_query("INSERT OR IGNORE INTO strawberry_holdings (agent_name, ticker, quantity) VALUES (?, ?, 0.0)", (archetype_name, state['ticker']))
                db.execute_query("UPDATE strawberry_holdings SET quantity = quantity + ? WHERE agent_name = ? AND ticker = ?", (qty, archetype_name, state['ticker']))
            elif state['final_decision'] == "SELL":
                db.execute_query("UPDATE strawberry_portfolio SET strawberry_balance = strawberry_balance + ? WHERE agent_name = ?", (total_strawberries, archetype_name))
                db.execute_query("UPDATE strawberry_holdings SET quantity = quantity - ? WHERE agent_name = ? AND ticker = ?", (qty, archetype_name, state['ticker']))
                
            db.execute_query(
                "INSERT INTO strawberry_trade_history (agent_name, ticker, action, quantity, strawberry_price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
                (archetype_name, state['ticker'], state['final_decision'], qty, price, state['execution_details'])
            )
            print(f"🍓 Strawberry Trade Executed: {archetype_name} {state['final_decision']} {qty} {state['ticker']} @ {price} 🍓")
        except Exception as e:
            print(f"Strawberry Execution error: {e}")

    finding = f"Decision: {state['final_decision']}\nRationale: {state['execution_details']}\nStrategy: {state['portfolio_strategy']}"
    vector_db.add_trade_finding(state['ticker'], state['date'], finding)
    return {}
