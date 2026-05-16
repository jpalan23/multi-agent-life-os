# Multi-Agent Life-OS: AI Memory & Context

## Project Overview
This is a LangGraph-powered multi-agent system (Life-OS) handling financial trading, job search automation, personal finance, and notifications. It relies heavily on local LLMs (Ollama / LM Studio) to maintain Zero-Cloud security.

## Architecture & State
- **Quant Team (Trading V2):** A mature, robust graph (`teams/quant/trading_graph.py`) utilizing `yfinance` for real data, Bull vs. Bear adversarial debates, Risk Management checks, and LangGraph Checkpointing (`SqliteSaver`).
- **Memory & Storage:** 
  - **SQLite** (`core/db_manager.py`) manages dummy money (`portfolio`), trade history, and state variables.
  - **ChromaDB** (`core/vector_store.py`) provides semantic memory, storing past trade findings and debate summaries so the agents can learn over time.
- **LLM Factory:** Dual-model architecture (`get_quick_llm` for parsing, `get_deep_llm` for reasoning).
- **Other Teams:** Career, Finance, and Communicator (Telegram Bot) exist but are currently in V1 (mocked state).

## Development Guidelines
1. **Data Security:** All sensitive data (DB files, PDFs) stay in `data/`. Do not commit actual data files.
2. **Execution Flow:** Simulated trades must strictly respect the dummy portfolio balance ($USD).
3. **Continuous Learning:** Keep track of major architectural shifts. Store all long-form artifacts, implementation plans, and walkthroughs in the `learning/` directory.
4. **Testing:** Before making broad changes to the graph, use `python -m py_compile` or execute the graph to catch LangChain deprecations or schema errors.

## Useful Commands
- **Run Quant Graph:** `python teams/quant/trading_graph.py <TICKER>`
- **Test LLM Setup:** `python test_factory.py`
- **Test DB Setup:** `python test_db.py`
