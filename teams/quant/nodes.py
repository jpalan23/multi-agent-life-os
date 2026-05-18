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

def market_analyst(state: QuantState) -> QuantState:
    """Fetches real-time market data (prices, volume) and news."""
    print(f"[Market Analyst] Fetching market data & news for {state['ticker']}...")
    
    # Fetch Price
    price = price_oracle.get_last_price(state['ticker'])
    if price:
        price_info = f"The latest price for {state['ticker']} is ${price:.2f}."
    else:
        price_info = get_stock_price(state['ticker'])
        
    # Fetch News
    news = get_company_news(state['ticker'])
    
    return {"market_data": price_info, "news_data": news}

def fundamental_analyst(state: QuantState) -> QuantState:
    """Fetches real fundamental data via yfinance."""
    print(f"[Fundamental Analyst] Fetching fundamentals for {state['ticker']}...")
    info = get_stock_info(state['ticker'])
    
    # Use Quick LLM to summarize
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
        
    # Use Quick LLM to extract key insights
    llm = get_quick_llm(temperature=0.1, keep_alive="5m")
    prompt = f"""
    Analyze the following earnings transcript snippet for {state['ticker']}. 
    Extract the key strategic direction, revenue guidance, and any major risks mentioned.
    
    Transcript: {transcript}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"earnings_insights": response.content}

def alternative_data_analyst(state: QuantState) -> QuantState:
    """Synthesizes data from Reddit sentiment and Google searches."""
    print(f"[Alt-Data Analyst] Analyzing Reddit & Web Research for {state['ticker']}...")
    
    reddit = get_reddit_sentiment(state['ticker'])
    google = get_google_search_analysis(state['ticker'])
    
    # Use Quick LLM to synthesize
    llm = get_quick_llm(temperature=0.1, keep_alive="5m")
    prompt = f"""
    Synthesize the following alternative data for {state['ticker']} into a brief sentiment report.
    Reddit Context: {reddit}
    Web Research (Motley Fool/Nasdaq/etc): {google}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"alternative_data": response.content}

def market_scout(state: QuantState) -> QuantState:
    """Discovers high-signal tickers autonomously."""
    print("[Market Scout] Scanning for top movers and unusual volume...")
    
    movers = get_market_movers()
    volume = get_unusual_volume()
    
    all_discovered = list(set(movers + volume))
    
    for ticker in all_discovered:
        db.execute_query(
            "INSERT OR IGNORE INTO watchlist (ticker, source, reason) VALUES (?, ?, ?)",
            (ticker, 'SCOUT', 'Top Mover / Unusual Volume detected by Scout')
        )
        print(f"[Market Scout] Discovered: {ticker}")
        
    return {"scanned_tickers": all_discovered}

def bull_researcher(state: QuantState) -> QuantState:
    """Argues the bull case based on data and previous bear arguments."""
    print(f"[Bull Researcher] Preparing bull thesis (Round {state['debate_round']})...")
    llm = get_deep_llm(temperature=0.3, keep_alive="5m")
    
    context = (
        f"Market Data: {state['market_data']}\n"
        f"Fundamentals: {state['fundamental_data']}\n"
        f"Recent News: {state['news_data']}\n"
        f"Earnings Insights: {state['earnings_insights']}\n"
        f"Alternative Data (Reddit/Web): {state['alternative_data']}"
    )
    
    if state['bear_arguments']:
        context += f"\nCounter the Bear's arguments: {state['bear_arguments']}"
        
    prompt = f"You are a Bullish Researcher. Argue why we should BUY {state['ticker']}. Context:\n{context}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"bull_arguments": response.content}

def bear_researcher(state: QuantState) -> QuantState:
    """Argues the bear case based on data and previous bull arguments."""
    print(f"[Bear Researcher] Preparing bear thesis (Round {state['debate_round']})...")
    llm = get_deep_llm(temperature=0.3, keep_alive="5m")
    
    context = (
        f"Market Data: {state['market_data']}\n"
        f"Fundamentals: {state['fundamental_data']}\n"
        f"Recent News: {state['news_data']}\n"
        f"Earnings Insights: {state['earnings_insights']}\n"
        f"Alternative Data (Reddit/Web): {state['alternative_data']}"
    )
    
    if state['bull_arguments']:
        context += f"\nCounter the Bull's arguments: {state['bull_arguments']}"
        
    prompt = f"You are a Bearish Researcher. Argue why we should SELL or HOLD {state['ticker']}. Context:\n{context}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Increment debate round after the bear speaks
    new_round = state.get('debate_round', 1) + 1
    
    return {"bear_arguments": response.content, "debate_round": new_round}

def trader_decision(state: QuantState) -> QuantState:
    """Weighs the bull and bear arguments and makes a final decision."""
    archetype_name = state.get("archetype", "Standard")
    print(f"[Trader] {archetype_name} evaluating debate for {state['ticker']}...")
    
    # This is the final step in the LLM chain, so explicitly drop the model from VRAM!
    llm = get_deep_llm(temperature=0.1, keep_alive="0")
    
    archetype_prompt = ""
    if archetype_name in ARCHETYPES:
        archetype_prompt = f"\nYOUR PERSONA: {ARCHETYPES[archetype_name]['system_prompt']}"
    
    prompt = f"""
    You are the Lead Trader.{archetype_prompt}
    Decide to BUY, SELL, or HOLD {state['ticker']}.
    Bull Case: {state['bull_arguments']}
    Bear Case: {state['bear_arguments']}
    
    Respond with ONLY the action (BUY, SELL, HOLD) on the first line. 
    Then provide a brief justification based on your specific persona and philosophy.
    """
    response = llm.invoke([HumanMessage(content=prompt)], config={"tags": [f"Trader: {archetype_name}"]})
    content = response.content.strip().split('\n')
    action = content[0].strip().replace(".", "").upper()
    justification = "\n".join(content[1:]).strip()
    
    if action not in ["BUY", "SELL", "HOLD"]:
        action = "HOLD" # fallback
        
    return {"final_decision": action, "execution_details": justification}

def risk_manager(state: QuantState) -> QuantState:
    """Checks dummy money balance and portfolio risk before execution."""
    print(f"[Risk Manager] Assessing risk for {state['ticker']} decision: {state['final_decision']}...")
    
    if state['final_decision'] == "HOLD":
        return {"risk_approved": True, "risk_assessment": "Hold requires no capital."}
        
    # Check dummy money portfolio
    try:
        portfolio = db.execute_query("SELECT asset, quantity FROM portfolio")
        port_dict = {row['asset']: row['quantity'] for row in portfolio}
        cash = port_dict.get('USD', 0.0)
        stock_qty = port_dict.get(state['ticker'], 0.0)
        
        assessment = ""
        approved = False
        
        if state['final_decision'] == "BUY":
            if cash > 1000: # We need at least $1000 to buy
                approved = True
                assessment = f"Approved BUY. Available Cash: ${cash:.2f}"
            else:
                assessment = f"Rejected BUY. Insufficient Cash: ${cash:.2f}"
                
        elif state['final_decision'] == "SELL":
            if stock_qty > 0:
                approved = True
                assessment = f"Approved SELL. Available shares: {stock_qty}"
            else:
                assessment = f"Rejected SELL. No shares owned."
                
        # If rejected, override decision
        final_decision = state['final_decision'] if approved else "HOLD"
        
        return {"risk_approved": approved, "risk_assessment": assessment, "final_decision": final_decision}
    except Exception as e:
        print(f"[Risk Manager] DB Error: {e}")
        return {"risk_approved": False, "risk_assessment": str(e), "final_decision": "HOLD"}

def execution_agent(state: QuantState) -> QuantState:
    """Executes the trade in the local SQLite DB and saves findings to VectorDB."""
    print(f"[Execution Agent] Finalizing execution for {state['ticker']}: {state['final_decision']}")
    
    if state['final_decision'] in ["BUY", "SELL"]:
        # Fetch real-time price from Oracle at execution time
        price = price_oracle.get_last_price(state['ticker'])
        if not price:
            # Fallback to parsing market_data if oracle fails
            try:
                price_str = state['market_data']
                # extract float from "$123.45"
                price = float(price_str.split('$')[-1])
            except:
                price = 100.0 # fallback dummy price
            
        qty = 10.0
        
        try:
            if state['final_decision'] == "BUY":
                # Deduct cash, add stock
                db.execute_query("UPDATE portfolio SET quantity = quantity - ? WHERE asset = 'USD'", (price * qty,))
                db.execute_query("INSERT OR IGNORE INTO portfolio (asset, quantity) VALUES (?, 0.0)", (state['ticker'],))
                db.execute_query("UPDATE portfolio SET quantity = quantity + ? WHERE asset = ?", (qty, state['ticker']))
            elif state['final_decision'] == "SELL":
                # Add cash, deduct stock
                db.execute_query("UPDATE portfolio SET quantity = quantity + ? WHERE asset = 'USD'", (price * qty,))
                db.execute_query("UPDATE portfolio SET quantity = quantity - ? WHERE asset = ?", (qty, state['ticker']))
                
            db.execute_query(
                "INSERT INTO trade_history (ticker, action, quantity, price, reasoning) VALUES (?, ?, ?, ?, ?)",
                (state['ticker'], state['final_decision'], qty, price, state['execution_details'])
            )
            print(f"--> Simulated Trade Executed: {state['final_decision']} {qty} {state['ticker']} @ ${price}")
        except Exception as e:
            print(f"DB Execution error: {e}")

    # Store findings in Vector DB
    finding = f"Trade Decision: {state['final_decision']}\nReasoning: {state['execution_details']}\nBull: {state['bull_arguments']}\nBear: {state['bear_arguments']}"
    vector_db.add_trade_finding(state['ticker'], state['date'], finding)
    
    return {}
