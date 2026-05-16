import sqlite3
import os

class DBManager:
    """
    Manages the SQLite database connection and schema for the Multi-Agent Life-OS.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to data/life_os.db
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, "data", "life_os.db")
        else:
            self.db_path = db_path
            
        self._initialize_schema()

    def get_connection(self):
        """Returns a new connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_schema(self):
        """Creates the required tables if they don't exist."""
        schema = """
        -- Team A: The Quant
        CREATE TABLE IF NOT EXISTS market_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            sentiment_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            summary TEXT
        );

        -- Quant V2: Portfolio and Paper Trading
        CREATE TABLE IF NOT EXISTS portfolio (
            asset TEXT PRIMARY KEY,
            quantity REAL NOT NULL,
            average_price REAL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert dummy money (100k USD) if not exists
        INSERT OR IGNORE INTO portfolio (asset, quantity) VALUES ('USD', 100000.0);

        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL, -- 'BUY' or 'SELL'
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            reasoning TEXT
        );

        -- Team B: The Career Catalyst
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            status TEXT NOT NULL,
            jd_text TEXT,
            resume_version TEXT,
            applied_date DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS skill_matrix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL UNIQUE,
            confidence_level INTEGER DEFAULT 1,
            last_practiced DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Team C: The Household Accountant
        CREATE TABLE IF NOT EXISTS fin_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date DATE NOT NULL,
            account_source TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema)
            conn.commit()

    def execute_query(self, query: str, parameters: tuple = ()):
        """Executes a query and returns the results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return cursor.lastrowid

# Singleton-like instance for easy importing
db = DBManager()
