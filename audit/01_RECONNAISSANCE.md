# 01 — RECONNAISSANCE & ARCHITECTURE TRACING

**Target System**: Multi-Agent Research Assistant  
**Repository**: `https://github.com/tushar152006/Multi_agent_research_assistant.git`  
**Authoritative Scope**: Local working tree (`c:\Users\DELL\Downloads\Multi_agent_research_assitant`)  
**Audit Date**: September 16, 2026  
**Auditor Persona**: Principal Application Security Engineer & Adversarial AI Systems Auditor  
**Operating Mode**: Strictly Read-Only (Zero Code Modifications, Zero Commits, Zero Architecture Alterations)

---

## 1. System Overview & Technology Stack

The Multi-Agent Research Assistant is an asynchronous full-stack platform designed to automate systematic academic literature reviews, citation grounding, contradiction detection, and engineering roadmap generation.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM STACK                                  │
├──────────────────────┬─────────────────────────────────────────────────┤
│ Backend Framework    │ Python 3.11 / 3.12, FastAPI, Uvicorn, Pydantic  │
│ Orchestration        │ Custom Async DAG Engine (DAGEngine), AsyncIO    │
│ Frontend Framework   │ Next.js 16.2.1 (App Router), React 19.2.4       │
│ Language / Typing    │ TypeScript 5.8.3 (Frontend), Python typing      │
│ LLM / Inference      │ Groq Cloud API (openai/gpt-oss-120b), Ollama    │
│ Document Parsing     │ pypdf (v4.0 - 5.x), BeautifulSoup4              │
│ External Ingestion   │ arXiv Atom API, Semantic Scholar Graph API, DDG │
│ State & Persistence  │ Local Filesystem JSON Store (SessionStore)      │
│ Deployment           │ Docker, Docker Compose, Railway, Render         │
└──────────────────────┴─────────────────────────────────────────────────┘
```

---

## 2. Directory Structure & Critical Component Inventory

```
c:\Users\DELL\Downloads\Multi_agent_research_assitant
├── .github/workflows/ci.yml           # CI Pipeline (Pytest, Ruff, TypeScript)
├── Dockerfile.backend                 # Python 3.12-slim container (root execution)
├── Dockerfile.frontend                # Node 20-alpine Next.js multi-stage build
├── docker-compose.yml                 # Dual-service container orchestration
├── .gitignore                         # Secret and cache ignore definitions
├── .env.example                       # Sanitized template for environment variables
├── backend/
│   ├── api/
│   │   ├── main.py                   # FastAPI instantiation & CORS configuration
│   │   └── routes/
│   │       ├── health.py             # Liveness healthcheck route (/health)
│   │       ├── research.py           # REST endpoints for research, upload, sessions
│   │       └── websocket.py          # WebSocket streaming pipeline (/ws/research)
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings & environment loader
│   │   ├── dag_engine.py             # Custom asynchronous DAG runner
│   │   ├── llm.py                    # Groq, Ollama, Heuristic LLM service abstraction
│   │   ├── citation_grounding.py     # Sentence segmentation & SHA-256 chunk hashing
│   │   ├── evidence_graph.py         # Network evidence graph (Nodes & Relations)
│   │   └── research_sufficiency.py   # Autonomous stopping & refinement judge
│   ├── agents/
│   │   ├── research_agent.py         # Query expansion & paper deduplication
│   │   ├── reader_agent.py           # Multi-page parsing & chunk generation
│   │   ├── analyst_agent.py          # Thematic consensus & gap extraction
│   │   ├── contradiction_agent.py    # N x N tension & conflict matrix
│   │   ├── citation_auditor.py       # Fuzzy quote matching & truth qualification
│   │   ├── critic_agent.py           # Quality scoring & LLM risk critique
│   │   ├── builder_agent.py          # MVP translation roadmap generator
│   │   └── orchestrator.py           # DAG wiring, adaptive iteration, event emitter
│   ├── services/
│   │   ├── arxiv_service.py          # arXiv Atom API client & PDF fetcher
│   │   ├── semantic_scholar_service.py # Semantic Scholar API & OA PDF fetcher
│   │   ├── web_scraper_service.py    # DuckDuckGo search & HTML parser with SSRF guard
│   │   ├── pdf_service.py            # pypdf wrapper & section segmentation
│   │   └── academic_exporter.py      # BibTeX & Markdown report generator
│   └── storage/
│       └── session_store.py          # Asynchronous filesystem session persistence
└── frontend/
    ├── src/app/                      # Next.js App Router root layout & main page
    ├── src/components/
    │   ├── research-dashboard.tsx    # Primary UI coordinator & state manager
    │   ├── dashboard/
    │   │   ├── AgentTimeline.tsx     # Live DAG step indicator
    │   │   ├── PdfDropzone.tsx       # Drag-and-drop document upload
    │   │   └── ResultTabs.tsx        # Multi-tab research viewer (Audit, Graph, Plan)
    │   └── ui/
    │       └── MermaidViewer.tsx     # Diagram viewer using dynamic CDN script
    └── src/lib/
        ├── api.ts                    # Fetch wrapper for REST backend
        ├── websocket.ts              # WebSocket client for live event streaming
        └── types.ts                  # Shared TypeScript interfaces
```

---

## 3. End-to-End Execution Flow

1. **Initiation**:
   - **Path A (REST)**: `POST /api/v1/research` with `{ query, max_results, query_type }` or `POST /api/v1/research/upload-pdf`.
   - **Path B (WebSocket)**: `WS /ws/research`, client sends `{ query, max_results, query_type }`.
2. **DAG Instantiation**:
   `Orchestrator` builds an instance of `DAGEngine` containing 7 dependent nodes:
   ```
   research_agent 
        │
        ▼
   reader_agent (downloads PDFs, extracts chunks with SHA-256)
        │
   ┌────┴────────────────────────┐
   ▼                             ▼
   contradiction_agent       analyst_agent
   (cross-paper matrix)      (themes, consensus, gaps)
   └────┬────────────────────────┬┘
        ▼                        ▼
        └─────────► citation_auditor ◄──────────┘
                    (verifies claims against chunks)
                         │
                         ▼
                    critic_agent
                    (heuristic & LLM critique)
                         │
                         ▼
                    builder_agent
                    (MVP implementation plan)
   ```
3. **Adaptive Loop & Sufficiency Check**:
   `ResearchSufficiencyJudge` evaluates whether grounding precision $\ge 0.65$ and unresolved gaps remain. If insufficient and iteration budget $\le 3$, orchestrator triggers targeted follow-up queries.
4. **State Persistence**:
   The final `ResearchResponse` is saved via `SessionStore.save_report` as `backend/data/sessions/{session_id}.json`.
5. **Client Presentation**:
   Frontend renders results: text cards, Markdown tables, and SVG diagrams via `MermaidViewer`.

---

## 4. Trust Boundaries & Security Enclaves

```
  [ UNTRUSTED INTERNET / PUBLIC ATTACKER ]
                      │
   (Boundary 1: Network / HTTP & WS Ingestion)
                      ▼
             [ FastAPI Backend API ]
             ├── /api/v1/research (Unauthenticated)
             ├── /ws/research (Unauthenticated)
             └── /upload-pdf (20MB Payload Ceiling)
                      │
   (Boundary 2: Local Session Filesystem Storage)
                      ▼
         [ backend/data/sessions/*.json ]
                      │
   (Boundary 3: External Outbound Network Calls)
         ├── ArXiv API (https://export.arxiv.org)
         ├── Semantic Scholar API (https://api.semanticscholar.org)
         ├── External PDF Download URLs (Arbitrary OA URLs)
         └── Web Search & Scraper (DuckDuckGo + Target Web Sites)
                      │
   (Boundary 4: LLM External Inference API)
                      ▼
          [ Groq API (https://api.groq.com) ]
          └── Prompts with <untrusted_research_data>
                      │
   (Boundary 5: Client-Side DOM & Dynamic Execution)
                      ▼
      [ Next.js Frontend / Browser DOM ]
      ├── dangerouslySetInnerHTML in MermaidViewer
      └── Dynamic Script Execution: jsDelivr CDN
```

### Trust Boundary Analysis:
- **Boundary 1 (API Edge)**: Lacks authentication, session tokens, rate limiting, and origin checks on WebSockets.
- **Boundary 2 (Storage)**: Flat directory storing all users' sessions without tenant separation.
- **Boundary 3 (Outbound Fetch)**: `WebScraperService` has `is_safe_url()` but lacks DNS-pinning; `SemanticScholarService` has **NO SSRF protection** on its PDF fetch path.
- **Boundary 4 (LLM Prompts)**: Untrusted external strings enter prompt templates without delimiter escaping.
- **Boundary 5 (Browser Rendering)**: Unpinned dynamic CDN script evaluation via `new Function()`.
