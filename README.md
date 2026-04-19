# 🧠 Multi-Agent Autonomous Research Assistant

![CI](https://github.com/tushar152006/Multi_agent_research_assistant/actions/workflows/ci.yml/badge.svg)
![Next.js](https://img.shields.io/badge/Next.js-black?style=for-the-badge&logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-black?style=for-the-badge&logo=ollama&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-131415?style=for-the-badge&logo=railway&logoColor=white)

An AI-powered research ecosystem that simulates a complete human research team. Using **5 specialized, autonomous agents**, this system automatically discovers, analyzes, critiques, and synthesizes academic literature into actionable insights — all running **free and fully private** using local LLMs (via Ollama) bridged to cloud deployments.

---

## ⚡ Key Features

- **🌐 Real-Time Agent Dashboard:** Watch the AI reasoning live via WebSockets on a glassmorphic Next.js UI.
- **🛡️ 100% Free LLM Execution:** Leverages your personal computer's hardware using Ollama (Llama 3.1), allowing massive generation without API fees.
- **🧩 5 Specialized Agent Personas:** A cascading pipeline where agents literally debate and refine each other's work.
- **🚀 Cloud-Local Bridge:** Frontend on Vercel, Backend on Railway, with an Ngrok tunnel routing heavy LLM tasks to your local machine.
- **📚 Multi-Source Discovery:** Simultaneously queries arXiv, Semantic Scholar, and the live web — with deduplication and relevance scoring.
- **💾 Session Persistence:** Save, reload, and export research sessions as JSON.

---

## 🤖 The Agent Pipeline

```
User Query
    │
    ▼
┌─────────────────────┐
│  Research Agent      │  ← Discovers papers from arXiv + Semantic Scholar + Web
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Reader Agent        │  ← Extracts methodology, findings, limitations from each paper
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Analyst Agent       │  ← Synthesises themes, consensus, conflicts, and gaps
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Critic Agent        │  ← Challenges weak evidence and assumptions (via LLM)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Builder Agent       │  ← Generates an actionable project/startup implementation plan
└─────────────────────┘
```

---

## 🏗️ Architecture & Deployment

Because cloud GPU hosting is extremely expensive, this project uses a **Hybrid Deployment Strategy**:

| Layer | Technology | Where |
|---|---|---|
| Frontend | Next.js + TypeScript | Vercel (global CDN) |
| Backend API | FastAPI + WebSockets | Railway (24/7) |
| LLM Brain | Ollama (Llama 3.1:8b) | Your local PC |
| Tunnel | Ngrok | Bridges local → cloud |

---

## 💻 Local Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) with `llama3.1:8b` installed

```bash
ollama pull llama3.1:8b
```

### 1. Start the Backend
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Mac / Linux

# Install dependencies
pip install -r backend/requirements.txt

# Copy and fill in env vars
cp .env.example .env

# Start FastAPI server
uvicorn backend.api.main:app --reload --port 8000
```

### 2. Start the Frontend
```bash
cd frontend
cp .env.example .env.local    # Set NEXT_PUBLIC_API_BASE_URL & NEXT_PUBLIC_WS_BASE_URL
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — your full app is running! 🎉

---

## 🌍 Cloud Deployment

### 1. Start Your Local Ngrok Tunnel
```bash
ngrok http 11434 --host-header="localhost:11434"
```
Copy the `https://xxxx.ngrok.app` URL.

### 2. Deploy Backend to Railway
1. Push this repo to GitHub and connect to [Railway](https://railway.app).
2. Railway auto-detects `railway.toml` for build config.
3. Add environment variables:

| Variable | Value |
|---|---|
| `LLM_PROVIDER` | `ollama` |
| `OLLAMA_MODEL` | `llama3.1:8b` |
| `OLLAMA_BASE_URL` | Your Ngrok URL |
| `ALLOWED_ORIGINS` | Your Vercel frontend URL |

### 3. Deploy Frontend to Vercel
1. Connect your repo to [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Add environment variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://your-railway-app.up.railway.app/api/v1` |
| `NEXT_PUBLIC_WS_BASE_URL` | `wss://your-railway-app.up.railway.app` |

---

## 🧪 Running Tests

```bash
# Backend unit tests
pip install pytest pytest-asyncio
python -m pytest backend/tests/ -v

# Frontend type check
cd frontend && npx tsc --noEmit
```

---

## 📁 Project Structure

```
├── .github/workflows/ci.yml   # GitHub Actions CI
├── backend/
│   ├── agents/                # 5 autonomous agents + orchestrator
│   ├── api/                   # FastAPI routes + WebSocket endpoint
│   ├── core/                  # Config, LLM client
│   ├── models/                # Pydantic schemas
│   ├── services/              # arXiv, Semantic Scholar, Web scraper, PDF
│   ├── storage/               # Session persistence
│   └── tests/                 # 12 test files
├── frontend/
│   └── src/
│       ├── app/               # Next.js App Router pages
│       ├── components/        # UI components + research dashboard
│       └── lib/               # Types, API client, WebSocket
├── railway.toml               # Railway deployment config
├── render.yaml                # Render.com alt deployment
└── .env.example               # Environment variable template
```

---

> Built with ❤️ using FastAPI, Next.js, Ollama, and a lot of async Python.