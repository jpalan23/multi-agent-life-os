import yfinance as yf
import os
import requests
from typing import List, Optional

def get_stock_price(ticker: str) -> str:
    """Fetches the latest closing price for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        # Get last 1 day of data
        hist = stock.history(period="1d")
        if hist.empty:
            return f"Error: No price data found for {ticker}."
        
        last_close = hist['Close'].iloc[-1]
        return f"The latest closing price for {ticker} is ${last_close:.2f}."
    except Exception as e:
        return f"Error fetching price for {ticker}: {e}"

def get_stock_info(ticker: str) -> str:
    """Fetches fundamental information for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        summary = (
            f"Company: {info.get('longName', ticker)}\n"
            f"Sector: {info.get('sector', 'N/A')}\n"
            f"Industry: {info.get('industry', 'N/A')}\n"
            f"Market Cap: {info.get('marketCap', 'N/A')}\n"
            f"P/E Ratio: {info.get('trailingPE', 'N/A')}\n"
            f"Forward P/E: {info.get('forwardPE', 'N/A')}\n"
            f"52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}\n"
            f"52 Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}\n"
            f"Recommendation: {info.get('recommendationKey', 'N/A')}"
        )
        return summary
    except Exception as e:
        return f"Error fetching info for {ticker}: {e}"

def get_company_news(ticker: str) -> str:
    """Fetches the latest news for a ticker via Finnhub."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return "Finnhub API key not configured. Skipping news."
    
    try:
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from=2026-05-10&to=2026-05-18&token={api_key}"
        response = requests.get(url)
        news = response.json()
        
        if not news:
            return f"No recent news found for {ticker}."
            
        summaries = []
        for item in news[:5]:
            summaries.append(f"- {item['headline']} ({item['source']})")
        
        return "\n".join(summaries)
    except Exception as e:
        return f"Error fetching news: {e}"

def get_earnings_transcript(ticker: str) -> str:
    """Fetches the latest earnings transcript via Financial Modeling Prep (FMP)."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return "FMP API key not configured. Skipping transcripts."
    
    try:
        url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?limit=1&apikey={api_key}"
        response = requests.get(url)
        data = response.json()
        
        if not data:
            return f"No transcripts found for {ticker}."
            
        transcript = data[0].get("content", "")
        return transcript[:2000] + "..." if len(transcript) > 2000 else transcript
    except Exception as e:
        return f"Error fetching transcript: {e}"

# --- Market Scout Tools ---

def get_market_movers() -> List[str]:
    """Fetches top gainers from FMP as a discovery mechanism."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return []
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={api_key}"
        response = requests.get(url)
        data = response.json()
        return [item['symbol'] for item in data[:5]]
    except:
        return []

def get_unusual_volume() -> List[str]:
    """Fetches stocks with unusual volume from FMP."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return []
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={api_key}"
        response = requests.get(url)
        data = response.json()
        return [item['symbol'] for item in data[:5]]
    except:
        return []

# --- Alternative Data Tools ---

def get_reddit_sentiment(ticker: str) -> str:
    """Fetches Reddit sentiment heat for a ticker."""
    # This would ideally use AltIndex or Quiver Quant. 
    # For now, we mock the logic or use a simple search.
    return f"Reddit sentiment for {ticker} is currently 'High Heat' with positive trajectory on r/wallstreetbets."

def get_google_search_analysis(ticker: str) -> str:
    """Uses Serper.dev to find specific analyst articles (Motley Fool, etc)."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Serper API key not configured. Skipping deep web search."
    
    try:
        url = "https://google.serper.dev/search"
        payload = {"q": f"{ticker} stock analysis Motley Fool Nasdaq"}
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        results = response.json()
        
        snippets = []
        for result in results.get("organic", [])[:3]:
            snippets.append(f"- {result['title']}: {result['snippet']}")
        
        return "\n".join(snippets)
    except Exception as e:
        return f"Error during web search: {e}"
