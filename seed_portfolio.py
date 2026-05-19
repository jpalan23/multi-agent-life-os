from core.db_manager import db
from datetime import datetime

def seed_portfolio():
    print("🍓 Initializing Strawberry Economy with Real Portfolio Data...")
    
    # 1. Define Archetypes
    archetypes = ["The Oak", "The Maverick", "The Hummingbird", "The Oracle"]
    
    # 2. User's Real Holdings (Merged from CSV and Screenshots)
    # Using Screenshot values for Qty where they differ (assuming more recent)
    real_holdings = [
        {"ticker": "AMZN", "qty": 17.01, "cost": 211.9353},
        {"ticker": "AVGO", "qty": 3.0, "cost": 314.8267},
        {"ticker": "BRK.B", "qty": 22.0, "cost": 483.6872},
        {"ticker": "CEG", "qty": 15.0, "cost": 276.788},
        {"ticker": "DAL", "qty": 10.0, "cost": 58.91},
        {"ticker": "GOOGL", "qty": 50.29, "cost": 273.545},
        {"ticker": "INTU", "qty": 0.416, "cost": 583.3173},
        {"ticker": "JPM", "qty": 9.0, "cost": 296.66},
        {"ticker": "MSFT", "qty": 22.538, "cost": 435.0179},
        {"ticker": "NEE", "qty": 7.0, "cost": 91.5643},
        {"ticker": "NFLX", "qty": 100.0, "cost": 84.2403},
        {"ticker": "NOW", "qty": 50.0, "cost": 85.43},
        {"ticker": "NVDA", "qty": 20.0, "cost": 170.7915},
        {"ticker": "SOFI", "qty": 100.0, "cost": 17.5866},
        {"ticker": "FIG", "qty": 50.11, "cost": 23.87}, # From screenshot
        {"ticker": "GLD", "qty": 0.750479, "cost": 417.53}, # From screenshot
        {"ticker": "AXP", "qty": 0.014236, "cost": 314.28}, # From screenshot
        {"ticker": "HOOD", "qty": 9.78, "cost": 77.83}, # From screenshot
    ]
    
    # 3. Setup Agent Portfolios
    for agent in archetypes:
        if agent == "The Oak":
            # The Oak starts with your actual cash balance
            balance = 81.55 
        else:
            # Others start with a fresh 1000 strawberries
            balance = 1000.0
            
        db.execute_query(
            "INSERT OR REPLACE INTO strawberry_portfolio (agent_name, strawberry_balance) VALUES (?, ?)",
            (agent, balance)
        )
        print(f"   -> Initialized {agent} with {balance} 🍓")

    # 4. Load Real Holdings into 'The Oak'
    for holding in real_holdings:
        db.execute_query(
            """INSERT OR REPLACE INTO strawberry_holdings 
               (agent_name, ticker, quantity, average_cost_strawberries) 
               VALUES (?, ?, ?, ?)""",
            ("The Oak", holding['ticker'], holding['qty'], holding['cost'])
        )
        print(f"   -> Added {holding['qty']} {holding['ticker']} to The Oak's portfolio.")

    print("✅ Strawberry Economy successfully seeded.")

if __name__ == "__main__":
    seed_portfolio()
