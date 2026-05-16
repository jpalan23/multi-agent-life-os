import os
import chromadb
from chromadb.config import Settings

class VectorStore:
    """
    Manages the local ChromaDB instance for semantic memory storage.
    """
    
    def __init__(self, db_dir: str = None):
        if db_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_dir = os.path.join(base_dir, "data", "chroma_db")
        else:
            self.db_dir = db_dir
            
        os.makedirs(self.db_dir, exist_ok=True)
        
        # Initialize the Chroma client
        self.client = chromadb.PersistentClient(path=self.db_dir)
        
        # We will create collections for different agent memories
        self.trade_findings = self.client.get_or_create_collection(name="trade_findings")

    def add_trade_finding(self, ticker: str, date: str, finding: str, metadata: dict = None):
        """Adds a research finding to the vector store."""
        doc_id = f"{ticker}_{date}"
        meta = metadata or {}
        meta["ticker"] = ticker
        meta["date"] = date
        
        self.trade_findings.add(
            documents=[finding],
            metadatas=[meta],
            ids=[doc_id]
        )
        print(f"[VectorStore] Added finding for {ticker} on {date}")

    def query_findings(self, query_text: str, n_results: int = 3, where: dict = None) -> list:
        """Queries the vector store for relevant past findings."""
        results = self.trade_findings.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        
        # Format the output into a list of strings
        if results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            return [{"document": d, "metadata": m} for d, m in zip(docs, metas)]
            
        return []

# Singleton-like instance
vector_db = VectorStore()
