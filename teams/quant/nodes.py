from langchain_core.messages import HumanMessage, AIMessage
from core.llm_factory import get_quick_llm, get_deep_llm
from core.db_manager import db
from core.vector_store import vector_db
from core.price_oracle import price_oracle
from teams.quant.tools import get_stock_price, get_stock_info
from teams.quant.state import QuantState

def market_analyst(state: QuantState) -> QuantState:
    """Fetches real-time market data (prices, volume)."""
    print(f"[Market Analyst] Fetching market data for {state['ticker']}...")
    price = price_oracle.get_last_price(state['ticker'])
    if price:
        price_info = f"The latest price for {state['ticker']} is ${price:.2f}."
    else:
        price_info = get_stock_price(state['ticker']) # fallback to tool
    return {"market_data": price_info}

def fundamental_analyst(state: QuantState) -> QuantState:
    """Fetches real fundamental data via yfinance."""
    print(f"[Fundamental Analyst] Fetching fundamentals for {state['ticker']}...")
    info = get_stock_info(state['ticker'])
    
    # Use Quick LLM to summarize
    llm = get_quick_llm(temperature=0.1, keep_alive="5m")
    prompt = f"Summarize the following fundamental data for {state['ticker']} into a concise analyst report:\n{info}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"fundamental_data": response.content}

def bull_researcher(state: QuantState) -> QuantState:
    """Argues the bull case based on data and previous bear arguments."""
    print(f"[Bull Researcher] Preparing bull thesis (Round {state['debate_round']})...")
    llm = get_deep_llm(temperature=0.3, keep_alive="5m")
    
    context = f"Market Data: {state['market_data']}\nFundamentals: {state['fundamental_data']}"
    if state['bear_arguments']:
        context += f"\nCounter the Bear's arguments: {state['bear_arguments']}"
        
    prompt = f"You are a Bullish Researcher. Argue why we should BUY {state['ticker']}. Context:\n{context}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"bull_arguments": response.content}

def bear_researcher(state: QuantState) -> QuantState:
    """Argues the bear case based on data and previous bull arguments."""
    print(f"[Bear Researcher] Preparing bear thesis (Round {state['debate_round']})...")
    llm = get_deep_llm(temperature=0.3, keep_alive="5m")
    
    context = f"Market Data: {state['market_data']}\nFundamentals: {state['fundamental_data']}"
    if state['bull_arguments']:
        context += f"\nCounter the Bull's arguments: {state['bull_arguments']}"
        
    prompt = f"You are a Bearish Researcher. Argue why we should SELL or HOLD {state['ticker']}. Context:\n{context}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Increment debate round after the bear speaks
    new_round = state.get('debate_round', 1) + 1
    
    return {"bear_arguments": response.content, "debate_round": new_round}

def trader_decision(state: QuantState) -> QuantState:
    """Weighs the bull and bear arguments and makes a final decision."""
    print(f"[Trader] Evaluating debate for {state['ticker']}...")
    # This is the final step in the LLM chain, so explicitly drop the model from VRAM!
    llm = get_deep_llm(temperature=0.1, keep_alive="0")
    
    prompt = f"""
    You are the Lead Trader. Decide to BUY, SELL, or HOLD {state['ticker']}.
    Bull Case: {state['bull_arguments']}
    Bear Case: {state['bear_arguments']}
    
    Respond with ONLY the action (BUY, SELL, HOLD) on the first line. 
    Then provide a brief justification.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
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
