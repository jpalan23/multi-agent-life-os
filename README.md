# Multi-Agent Life-OS 🧠

A production-grade, LangGraph-powered multi-agent system designed to act as your autonomous personal assistant. The system consists of specialized "Teams" coordinated by a Central Supervisor, running entirely on local LLMs (Ollama) to maintain strict **Zero-Cloud Data Privacy**.

It features an always-on WhatsApp interface, allowing you to trigger agents, query data, and take practice quizzes from anywhere in the world.

---

## 1. System Architecture

- **Framework:** [LangGraph](https://python.langchain.com/v0.1/docs/langgraph/) (Stateful Multi-Agent Workflows)
- **Inference (Zero-Cloud):** Local LLMs via [Ollama](https://ollama.com/) (Using `llama3` for reasoning, `llava` for vision)
- **Persistence (Short-term):** Local SQLite (`life_os.db`)
- **Semantic Memory (Long-term):** ChromaDB (Local Vector Store)
- **Communication:** Twilio WhatsApp Webhook via FastAPI & ngrok
- **Always-On Daemon:** Linux `systemd` configuration

---

## 2. The Teams (Agents)

### ⚙️ Master Orchestration: P0 Reliability - *[V3 Active]*
- **Sequential Task Queue:** Enforces Zero-Concurrency to protect local hardware (Ollama) from over-saturation.
- **Model Tiering:** Strategically routes tasks between fast (1B-3B) and deep (8B-70B) models.
- **Milestone Checkpointing:** Persists task state to SQLite, allowing for seamless recovery after system crashes.
- **Trajectory Auditing:** Logs every reasoning step and tool call to a JSON-based audit trail for future evaluation.

### 📈 Team A: The Quant (Trading & Stocks) - *[V4 Active]*
- **Autonomous Discovery:** Integrated **Market Scout** node that scans pre-market movers and unusual volume to suggest stocks for analysis.
- **Alternative Data:** Ingests non-traditional signals from **Reddit sentiment** and **Google Analyst Search** (Motley Fool, Nasdaq, 24/7 Wall St).
- **Adversarial Debate:** Employs Bull vs. Bear researchers to debate stock prospects using deep context.
- **Risk Management:** Paper trading engine with a simulated $100k dummy portfolio.
- **Vector Memory:** Saves trade rationale to ChromaDB to inform future decisions.

### 🚗 Team E: The DMV Tutor - *[V2 Active]*
- **Vision PDF Parsing:** Uses `PyMuPDF` and `llava` to extract CA DMV handbook text and Road Sign images to generate dynamic quizzes.
- **Stateful Interactive Quiz:** Uses LangGraph `SqliteSaver` checkpointers to ask you questions one-at-a-time via WhatsApp, remembering what questions you have historically failed.
- **Daily Ping:** Uses `schedule` to run a background thread that pings you every day at 11:00 AM to practice.

### 💼 Team B: The Career Catalyst - *[V1 Mock]*
- Resume tailoring, Job scraping, and Senior interview prep (System Design).

### 🏦 Team C: The Household Accountant - *[V1 Mock]*
- Bank statement OCR parsing, KPI calculations (Burn Rate), and budget auditing.

### 📡 Team D: The Communicator - *[V2 Active]*
- A `FastAPI` webhook that listens to Twilio WhatsApp payloads, processes them through the `main.py` Supervisor Router, and replies with rich text and images.

---

## 3. Installation & Setup

### Requirements
- Ubuntu/Linux Environment
- Python 3.10+
- [Ollama](https://ollama.com/download) installed locally

### Step 1: Clone & Install
```bash
git clone <your-repo-url>
cd Agents
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Download Local AI Models
Open a terminal and pull the required models into your local Ollama instance:
```bash
ollama pull llama3
ollama pull llava
```

### Step 3: Populate the Database (Optional)
If you want to use the DMV Tutor, download the CA DMV Handbook to `data/dmv.pdf` and run:
```bash
python teams/dmv_tutor/pdf_parser.py
```
*(This will use LLaVA to read the book, look at the signs, and build a massive SQLite database of questions).*

---

## 4. Running the System (WhatsApp Mode)

To make the system "Always-On" and accessible from your phone via WhatsApp:

### Step 1: Prevent Sleep
Ensure your Ubuntu machine doesn't go to sleep and kill the server:
```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

### Step 2: Setup the systemd Daemon
```bash
sudo ln -s $(pwd)/deployment/life-os.service /etc/systemd/system/life-os.service
sudo systemctl daemon-reload
sudo systemctl enable life-os.service
sudo systemctl start life-os.service
```
*Your Life-OS is now permanently running in the background on port 8000!*

### Step 3: Connect to the Internet (ngrok)
In a terminal, run an ngrok tunnel to expose port 8000 securely:
```bash
ngrok http 8000
```
Copy the `https://xyz.ngrok.app` URL it gives you.

### Step 4: Twilio Setup
1. Create a free Twilio account and navigate to **Messaging > Try it out > Send a WhatsApp message**.
2. Under "Sandbox settings", paste your ngrok URL into the "When a message comes in" webhook field like this: `https://xyz.ngrok.app/whatsapp`
3. Send the join code (e.g. `join fluffy-raccoon`) from your personal phone to the Twilio number.
4. Send *"give me a stock report"* and watch the Quant team execute on your local PC!