# 🧠 Multi-Agent Autonomous Research Assistant

![Next.js](https://img.shields.io/badge/Next.js-black?style=for-the-badge&logo=next.js&logoColor=white) 
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi) 
![Ollama](https://img.shields.io/badge/Ollama-black?style=for-the-badge&logo=ollama&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-131415?style=for-the-badge&logo=railway&logoColor=white)

An AI-powered research ecosystem that simulates a complete human research team. Using 5 specialized, autonomous agents, this system automatically discovers, analyzes, critiques, and synthesizes academic literature into actionable insights—all running for **free and fully private** using local LLMs (via Ollama) bridged to cloud deployments.

---

## ⚡ Key Features

- **🌐 Real-Time Agent Dashboard:** Watch the AI reasoning live via WebSockets on a beautiful, glassmorphic Next.js UI.
- **🛡️ 100% Free LLM Execution:** Leverages your personal computer's hardware using Ollama (Llama-3), allowing massive generation without API fees.
- **🧩 5 Specialized Agent Personas:** A cascading pipeline of intelligence where agents literally debate and refine each other's work.
- **🚀 Cloud-Local Bridge:** The Frontend is globally distributed on Vercel, the Backend runs on Railway, and an Ngrok tunnel routes heavy LLM tasks securely back to your living room.

---

## 🤖 The Agent Pipeline

1. **The Research Agent:** Generates intelligent search queries and discovers relevant academic papers.
2. **The Reader Agent:** Extracts methodologies, core findings, limitations, and statistics from the raw text.
3. **The Analyst Agent:** Synthesizes multiple papers to find trends, gaps, and consensus.
4. **The Critic Agent:** Plays "Devil's Advocate" by rigorously challenging the Analyst's assumptions.
5. **The Builder Agent:** Takes all the research and creates a concrete, actionable project or startup implementation plan.

---

## 🏗️ Architecture & Deployment Overview

Because cloud GPU hosting is extremely expensive, this project utilizes a **Hybrid Deployment Strategy**:

*   **Frontend (Vercel):** The Next.js React application is hosted publicly on Vercel.
*   **Backend (Railway):** The Python FastAPI web server acts as the central router and is deployed 24/7 on Railway to manage WebSocket connections without timing out.
*   **LLM Brain (Local PC):** The actual AI intelligence runs entirely locally using `Ollama: Llama-3`.
*   **The Bridge (Ngrok):** We utilize `ngrok` to create a secure tunnel from your local PC to the internet. The Railway backend automatically sends all generative prompts securely through this tunnel directly to your personal hardware.

---

## 💻 Local Development Setup

Want to run everything locally on your machine without deploying?

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) (with `llama3.1:8b` installed: run `ollama run llama3.1:8b`)

### 2. Start the Backend
```bash
cd backend
python -m venv .venv
# Activate the environment ( Windows: .venv\Scripts\activate | Mac/Linux: source .venv/bin/activate )
pip install -r requirements.txt

# Start FastAPI
uvicorn api.main:app --reload --port 8000
```

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

*Your complete app is now running at `http://localhost:3000`!*

---

## 🌍 Launching to the World (Cloud Deployment)

### 1. Start Your Local Ngrok Tunnel
On the PC running Ollama, open a terminal and run:
```bash
ngrok http 11434 --host-header="localhost:11434"
```
*Copy the `https://xxxx.ngrok.app` Forwarding URL.*

### 2. Deploy Backend to Railway
- Connect your GitHub repo to a new Railway project.
- It will automatically use the `railway.toml` to build the Python environment.
- Under Variables, add the following:
  - `LLM_PROVIDER`: `ollama`
  - `OLLAMA_MODEL`: `llama3.1:8b`
  - `OLLAMA_BASE_URL`: *(Paste your exact Ngrok URL here)*
  - `ALLOWED_ORIGINS`: *(Paste your frontend Vercel URL later)*

### 3. Deploy Frontend to Vercel
- Connect your repo to Vercel.
- **Important:** Go to Settings > General > "Root Directory" and set it to `frontend` so Vercel can find Next.js!
- Add the Environment Variables:
  - `NEXT_PUBLIC_API_BASE_URL`: `https://your-railway-app.up.railway.app/api/v1`
  - `NEXT_PUBLIC_WS_BASE_URL`: `wss://your-railway-app.up.railway.app`
- Deploy!

> Enjoy your private, hyper-intelligent, completely free Multi-Agent Researcher! 🔬