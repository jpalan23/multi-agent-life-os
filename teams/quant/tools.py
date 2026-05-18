import yfinance as yf
import os
import requests

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
        # Get news for the last week (mock dates for now)
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from=2026-05-10&to=2026-05-18&token={api_key}"
        response = requests.get(url)
        news = response.json()
        
        if not news:
            return f"No recent news found for {ticker}."
            
        # Take the top 5 news items
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
        # Get the latest transcript
        url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?limit=1&apikey={api_key}"
        response = requests.get(url)
        data = response.json()
        
        if not data:
            return f"No transcripts found for {ticker}."
            
        transcript = data[0].get("content", "")
        # Return the first 2000 characters to keep context manageable
        return transcript[:2000] + "..." if len(transcript) > 2000 else transcript
    except Exception as e:
        return f"Error fetching transcript: {e}"
