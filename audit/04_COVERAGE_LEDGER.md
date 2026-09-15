# 04 — AUDIT COVERAGE LEDGER

**Target System**: Multi-Agent Research Assistant  
**Authoritative Path**: `c:\Users\DELL\Downloads\Multi_agent_research_assitant`  
**Classification**: Systematic Security Coverage Ledger  

---

| Security Class | Target Components Audited | Status | Finding Ref | Notes / Observations |
|---|---|---|---|---|
| **Authentication (API)** | `backend/api/routes/*.py` | **CONFIRMED FINDING** | `SEC-001` | All endpoints are completely unauthenticated; no auth middleware or token checks exist. |
| **Authorization (BOLA/IDOR)**| `backend/storage/session_store.py`, `backend/api/routes/research.py` | **CONFIRMED FINDING** | `SEC-001` | No tenant separation or session ownership; any caller can list, view, export, and delete any session. |
| **WebSocket Authentication** | `backend/api/routes/websocket.py` | **CONFIRMED FINDING** | `SEC-002` | `/ws/research` accepts connections without handshake authentication or token exchange. |
| **WebSocket Origin Validation**| `backend/api/routes/websocket.py` | **CONFIRMED FINDING** | `SEC-002` | No origin header validation; vulnerable to Cross-Site WebSocket Hijacking (CSWSH). |
| **SSRF (Web Scraper)** | `backend/services/web_scraper_service.py` | **NEEDS VALIDATION** | `SEC-007` | `is_safe_url()` validates scheme, IP range, and blocks redirects, but DNS re-resolution in `httpx` creates theoretical TOCTOU window. |
| **SSRF (Semantic Scholar)** | `backend/services/semantic_scholar_service.py:100` | **CONFIRMED FINDING** | `SEC-003` | `fetch_pdf_text()` takes arbitrary URLs from external API data, enables `follow_redirects=True`, and lacks `is_safe_url()` check. |
| **SSRF (ArXiv Service)** | `backend/services/arxiv_service.py:105` | **NO FINDING** | — | Hardcoded to `https://arxiv.org/pdf/{arxiv_id}.pdf`. `arxiv_id` is stripped of prefixes; cannot redirect to arbitrary IP. |
| **File Upload (Size Limits)** | `backend/api/routes/research.py:70` | **NO FINDING** | — | 20MB limit enforced on Content-Length header and request body length upfront (HTTP 413). |
| **PDF Decompression / DoS** | `backend/services/pdf_service.py:143` | **CONFIRMED FINDING** | `SEC-004` | No page limit on `reader.pages`; parsing runs synchronously in the main async event loop. |
| **Path Traversal (Storage)** | `backend/storage/session_store.py:21` | **NO FINDING** | — | Regex `^[a-zA-Z0-9_-]+$` strictly prevents directory traversal (`../`). |
| **Command / Code Injection** | `backend/core/`, `backend/agents/` | **NO FINDING** | — | No `eval()`, `exec()`, `subprocess`, or `os.system` calls present in application execution path. |
| **SQL / NoSQL Injection** | `backend/storage/` | **NO FINDING** | — | Application uses flat JSON filesystem storage; no SQL or NoSQL database queries exist. |
| **Prompt Injection (Delimiter)**| `backend/agents/analyst_agent.py`, `critic_agent.py`, `builder_agent.py` | **CONFIRMED FINDING** | `SEC-005` | Untrusted data tags `<untrusted_research_data>` can be prematurely closed by unescaped `</untrusted_research_data>` in inputs. |
| **Agent Excessive Agency** | `backend/agents/orchestrator.py`, `dag_engine.py` | **NO FINDING** | — | Agents cannot execute arbitrary tools or system commands; workflows are strictly constrained to DAG nodes. |
| **XSS / DOM Sinks (Frontend)**| `frontend/src/components/ui/MermaidViewer.tsx:114` | **CONFIRMED FINDING** | `SEC-006` | SVG rendered via `dangerouslySetInnerHTML` after regex-only sanitization; unpinned dynamic import from jsDelivr CDN. |
| **CORS Misconfiguration** | `backend/api/main.py:21`, `backend/core/config.py:14` | **CONFIRMED FINDING** | `SEC-008` | `allowed_origins` defaults to `["*"]` with `allow_credentials=True`, causing reflection of cross-origin requests. |
| **Browser Security Headers** | `backend/api/main.py` | **CONFIRMED FINDING** | `SEC-009` | Missing CSP, X-Frame-Options, X-Content-Type-Options, HSTS headers. |
| **Rate Limiting / DoS** | `backend/api/routes/*.py` | **CONFIRMED FINDING** | `SEC-010` | No rate limiting on expensive LLM generation routes or PDF parsing endpoints. |
| **Secrets in Git History** | Git repository root commit history | **NO FINDING** | — | Git history inspected; `.env` was never committed; mock test keys sanitized. |
| **Secrets in Config / Source**| Entire backend & frontend codebase | **NO FINDING** | — | `.env.example` sanitized to placeholders; actual secrets kept strictly in uncommitted local `.env`. |
| **Container Execution User** | `Dockerfile.backend` | **CONFIRMED FINDING** | `SEC-011` | Backend container runs as `root` (missing non-root `USER` directive). |
| **Dependency Supply Chain** | `backend/requirements.txt`, `frontend/package.json` | **NO FINDING** | — | Standard libraries pinned to major/minor versions; frontend dependencies clean. |
