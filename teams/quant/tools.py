import yfinance as yf

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
