import os
import yfinance as yf
from typing import Optional, Dict, Any
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest
except ImportError:
    StockHistoricalDataClient = None

class PriceOracle:
    """
    Provides real-time price data for the Multi-Agent Life-OS.
    Uses Alpaca as primary and yfinance as fallback.
    """
    
    def __init__(self):
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.client = None
        
        if self.alpaca_api_key and self.alpaca_secret_key and StockHistoricalDataClient:
            try:
                self.client = StockHistoricalDataClient(self.alpaca_api_key, self.alpaca_secret_key)
            except Exception as e:
                print(f"[PriceOracle] Failed to initialize Alpaca client: {e}")

    def get_last_price(self, ticker: str) -> Optional[float]:
        """Fetches the last known price for a ticker."""
        # Try Alpaca first
        if self.client:
            try:
                request_params = StockLatestQuoteRequest(symbol_or_symbols=ticker)
                latest_quote = self.client.get_stock_latest_quote(request_params)
                price = latest_quote[ticker].ask_price
                if price and price > 0:
                    print(f"[PriceOracle] Fetched {ticker} price from Alpaca: {price}")
                    return float(price)
            except Exception as e:
                print(f"[PriceOracle] Alpaca fetch failed for {ticker}: {e}")

        # Fallback to yfinance
        try:
            ticker_obj = yf.Ticker(ticker)
            # Use fast_info if available, otherwise fallback to history
            price = ticker_obj.fast_info.get('last_price')
            if not price or price <= 0:
                # Get the last close from history
                hist = ticker_obj.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            if price and price > 0:
                print(f"[PriceOracle] Fetched {ticker} price from yfinance: {price}")
                return float(price)
        except Exception as e:
            print(f"[PriceOracle] yfinance fetch failed for {ticker}: {e}")

        return None

# Singleton instance
price_oracle = PriceOracle()
