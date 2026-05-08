# Multi-Agent Life-OS: Project Blueprint

## 1. System Overview
A local, LangGraph-powered multi-agent system running on local LLMs (Ollama/LM Studio). The system consists of four specialized "Teams" coordinated by a Central Supervisor.

### Core Architecture
- **Framework:** LangGraph (State Machine)
- **Inference:** Local LLM via OpenAI-compatible API (Port 11434/1234)
- **Database:** SQLite (Local Persistence & KPI tracking)
- **Notification:** Telegram Bot API / Discord Webhook

---

## 2. Team Definitions

### Team A: The Quant (Trading & Stocks)
* **Fundamental Analyst:** Evaluates NASDAQ/NSE stock health.
* **Sentiment Agent:** Scrapes financial news for bullish/bearish signals.
* **Reporter:** Generates a daily summary of portfolio performance.

### Team B: The Career Catalyst (Job Search & Senior Prep)
* **Job Scraper:** Monitors LinkedIn/Indeed for "Senior Full Stack" roles.
* **Resume Tailor:** Auto-aligns CV with JD keywords using local LLM.
* **Senior Mentor:** Tracks LeetCode progress and provides System Design feedback (Mermaid.js).
* **Syllabus Tracker:** Maps JD requirements to a learning "Confidence Score" (1-10).

### Team C: The Household Accountant (Personal Finance)
* **Statement Parser:** Extracts data from Bank/Credit Card PDFs (OCR-ready).
* **KPI Engine:** Calculates Burn Rate, Savings Rate, and Investment Ratios.
* **Auditor:** Flags unusual spending or upcoming bill cycles.

### Team D: The Communicator (Event-Driven Notifications)
* **Daily Digest:** Aggregates outputs from Team A, B, and C at 08:00 and 20:00.
* **Alert Agent:** Triggers immediate messages for high-priority stock moves or interview invites.

---

## 3. Database Schema (SQLite)

| Table | Purpose | Key Fields |
| :--- | :--- | :--- |
| `market_reports` | Stock History | `ticker`, `sentiment_score`, `timestamp` |
| `applications` | Job Pipeline | `company`, `status`, `jd_text`, `resume_version` |
| `skill_matrix` | Learning KPIs | `topic`, `confidence_level`, `last_practiced` |
| `fin_statements` | Usage KPIs | `category`, `amount`, `date`, `account_source` |

---

## 4. Implementation Roadmap

1.  **Phase 1 (Infrastructure):** Setup `llm_factory.py` to route to local Ollama instance.
2.  **Phase 2 (Memory):** Implement the SQLite storage layer for cross-team state sharing.
3.  **Phase 3 (Agent Expansion):** Clone `trading_graph.py` to create `career_graph.py` and `finance_graph.py`.
4.  **Phase 4 (Supervisor):** Build the entry-point node that routes user queries to the correct sub-graph.
5.  **Phase 5 (Notifications):** Connect the Telegram Bot tool to the `Daily Digest` node.

---

## 5. Senior Role Skill Integration
* **Observability:** Implement structured logging for every agent thought process.
* **Scalability:** Use a message-queue pattern (even locally) for PDF parsing tasks.
* **Security:** Ensure all bank statements remain in the local `data/` directory (Zero-Cloud).