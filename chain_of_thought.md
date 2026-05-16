# Chain of Thought

## Initial Setup Phase
- **Goal:** Set up the basic project structure and prepare for git tracking and local development.
- **Actions taken:**
  - Renamed the initial blueprint file to `README.md`.
  - Created the directory structure separating `core/` architecture, and the four main `teams/` (quant, career, finance, communicator).
  - Created a local `data/` directory with a `.keep` file to track it in git, while making sure the `.gitignore` excludes actual data files to ensure Zero-Cloud security.
  - Created `requirements.txt` with standard LLM/LangGraph and database tooling.
  - Initialized a `chain_of_thought.md` to keep track of development phases.

## Phase 1: Infrastructure
- **Goal:** Setup `llm_factory.py` to route to local Ollama instance.
- **Actions taken:**
  - Implemented `core/llm_factory.py` with `get_ollama` and `get_lm_studio`.
  - Updated `langchain-ollama` dependency and removed deprecation warnings.
  - Verified factory works correctly.

## Phase 2: Memory
- **Goal:** Implement the SQLite storage layer for cross-team state sharing.
- **Actions taken:**
  - Implemented `core/db_manager.py` with the defined SQLite schema.
  - Created tables for `market_reports`, `applications`, `skill_matrix`, and `fin_statements`.
  - Tested db connection and basic query execution.

## Phase 3: Agent Expansion
- **Goal:** Clone `trading_graph.py` to create `career_graph.py` and `finance_graph.py`.
- **Actions taken:**
  - Implemented `teams/quant/trading_graph.py` with fundamental analyst, sentiment agent, and reporter nodes.
  - Implemented `teams/career/career_graph.py` with job scraper, resume tailor, senior mentor, and syllabus tracker nodes.
  - Implemented `teams/finance/finance_graph.py` with statement parser, kpi engine, and auditor nodes.
  - Integrated SQLite DB operations into the graph nodes.

## Phase 4: Supervisor
- **Goal:** Build the entry-point node that routes user queries to the correct sub-graph.
- **Actions taken:**
  - Implemented `main.py` containing `supervisor_router` and `run_system`.
  - Added an LLM-based classifier to route queries to `Quant`, `Career`, `Finance`, or `Unknown`.
  - Integrated the specific team graphs into the routing logic.

## Phase 5: Notifications
- **Goal:** Connect the Telegram Bot tool to the Daily Digest node.
- **Actions taken:**
  - Implemented `teams/communicator/communicator_graph.py`.
  - Added a `daily_digest` node that aggregates DB data.
  - Added a `telegram_bot` node that reads environment variables and dispatches notifications via Telegram API.

- **Status:** Initial architecture implementation is complete! All 5 phases from the roadmap are now laid out in code.
- **V2 Upgrades Complete:** Quant Team (real data, chromaDB, debates), DMV Tutor Team (vision parsing, scheduler).

## Pending Upgrades (Things Left to Do)

### 1. Upgrade the Career Catalyst (Team B) to V2
- Implement real web scraping (using BeautifulSoup, Selenium, or an API) to automatically pull Job Descriptions from links.
- Set up an automated resume-tailoring pipeline that matches the job description against the `skill_matrix` and outputs a custom PDF/Markdown resume.

### 2. Upgrade the Household Accountant (Finance Team) to V2
- Implement a real PDF/CSV parser to read bank/credit card statements.
- Use the Quick LLM to auto-categorize line-item transactions.
- Calculate real KPI metrics (Burn Rate, Savings Rate) and flag unusual subscriptions.

### 3. Finalize the Communicator / Daily Digest
- Wire the `daily_digest` node to aggregate real data from other teams (Quant portfolio performance, Career pending applications, Finance budget status).
- Format and send a rich daily markdown report to Telegram.

### 4. End-to-End System Testing
- Run the `main.py` Supervisor with a live local Ollama instance to rigorously test accurate routing of ambiguous queries to the correct specialized graphs without breaking state.
