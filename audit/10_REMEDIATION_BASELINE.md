# 10 — PRE-REMEDIATION AUDIT & BASELINE

**Target System**: Multi-Agent Research Assistant  
**Authoritative Path**: `c:\Users\DELL\Downloads\Multi_agent_research_assitant`  
**Date**: September 16, 2026  
**Auditor/Engineer**: Principal Security Architect & Adversarial Verification Engineer  
**Status**: Pre-Remediation Baseline Complete  

---

## 1. Baseline Repository & Execution Context

- **Current Git Branch**: `main`
- **Working Tree State**: Clean relative to latest local Master V2 changes; zero remote commits/pushes.
- **Test Baseline**: 59/59 passing unit tests (`backend/tests/`); 0 TypeScript compiler errors in frontend (`npx tsc --noEmit`).
- **Dependencies**:
  - Python: `fastapi`, `uvicorn`, `pydantic-settings`, `httpx`, `beautifulsoup4`, `duckduckgo-search`, `pypdf`.
  - Node: `next: ^16.2.1`, `react: ^19.2.4`, `react-dom: ^19.2.4`, `typescript: 5.8.3`.
- **Infrastructure**: `Dockerfile.backend` (runs as root), `Dockerfile.frontend` (multi-stage alpine), `docker-compose.yml`.

---

## 2. Verification of Audit Findings Against Current Source

| Finding ID | Title | Current Status | Verification Source Details | Fix Approach Still Valid? |
|---|---|---|---|---|
| **SEC-001** | Absence of Auth & BOLA on Session Endpoints | **STILL PRESENT** | `routes/research.py:146-168` and `storage/session_store.py:61-105` have no user identity or ownership check. All sessions live in flat `backend/data/sessions/*.json`. | **YES**: Partition sessions by `user_id` (`sessions/{user_id}/{session_id}.json`) and enforce an authentication/identity dependency. |
| **SEC-002** | Unauthenticated WebSocket & CSWSH | **STILL PRESENT** | `routes/websocket.py:25` calls `await ws.accept()` without Origin inspection or auth handshake. | **YES**: Verify Origin against allowed origins whitelist and extract `user_id` / token before accepting connection. |
| **SEC-003** | Outbound HTTP Ingestion SSRF (Semantic Scholar) | **STILL PRESENT** | `semantic_scholar_service.py:112` executes `httpx.AsyncClient(follow_redirects=True).get(pdf_url)` with no IP safety validation. | **YES**: Implement a unified `SafeHttpClient` / `is_safe_url` checking IP ranges and disabling unvalidated redirects. |
| **SEC-004** | Synchronous Event-Loop Blocking & Unbounded PDF Pages | **STILL PRESENT** | `pdf_service.py:147` loops over `reader.pages` without a page limit; `research.py:86` calls text extraction synchronously in async handler. | **YES**: Limit to `MAX_PDF_PAGES = 100` and offload extraction to `asyncio.to_thread()`. |
| **SEC-005** | Prompt Delimiter Collision & Tag Escaping | **STILL PRESENT** | `analyst_agent.py:76`, `critic_agent.py:166`, `builder_agent.py:70` do not escape `</untrusted_research_data>` in inputs. | **YES**: Sanitize closing delimiter strings across all agent prompt interpolations. |
| **SEC-006** | Dynamic CDN Script Execution in MermaidViewer | **STILL PRESENT** | `MermaidViewer.tsx:26-27` calls `new Function("url", "return import(url)")("https://cdn.jsdelivr.net/...")`. | **YES**: Add `mermaid` to `package.json` and bundle locally using Next.js dynamic import. |
| **SEC-007** | Potential TOCTOU DNS Rebinding in Web Scraper | **NEEDS VALIDATION** | `web_scraper_service.py:48` resolves DNS before `httpx` connects. Exploitation requires sub-second TTL and search indexing. | **YES**: Enhance URL validation and pin/validate connection targets where feasible. |
| **SEC-008** | Permissive Wildcard CORS with Credentials Enabled | **STILL PRESENT** | `config.py:14` defaults `allowed_origins` to `["*"]` while `main.py:22` sets `allow_credentials=True`. | **YES**: Default `allowed_origins` to explicit dev origins (`http://localhost:3000`, `http://127.0.0.1:3000`) when credentials are true. |
| **SEC-009** | Missing Standard HTTP Security Headers | **STILL PRESENT** | `main.py` has no middleware setting CSP, X-Frame-Options, or X-Content-Type-Options. | **YES**: Add a lightweight security headers middleware. |
| **SEC-010** | Unbounded API Rate Limits and Resource Exhaustion | **STILL PRESENT** | No throttling exists on research endpoints. | **YES**: Implement a lightweight in-memory rate limiter / concurrency guard for research endpoints without heavy dependencies. |
| **SEC-011** | Backend Container Process Runs as Root | **STILL PRESENT** | `Dockerfile.backend` does not specify `USER appuser`. | **YES**: Add unprivileged system user and `USER appuser` in `Dockerfile.backend`. |

---

## 3. Dependencies & Ordering of Fixes

```
1. Phase 1 (Auth & BOLA) 
     │  Creates UserIdentity model & namespaces SessionStore to sessions/{user_id}/{session_id}.json
     ▼
2. Phase 2 (SSRF Hardening)
     │  Creates shared SafeHttpClient / is_safe_url applied across WebScraper and SemanticScholar
     ▼
3. Phase 3 (Frontend Dynamic Code)
     │  Adds mermaid to package.json; replaces new Function() with local dynamic import in MermaidViewer
     ▼
4. Phase 4 (CORS & WebSocket)
     │  Binds WebSocket to allowed origins & user identity; restricts CORS default origins
     ▼
5. Phase 5 (PDF Resource Safety)
     │  Applies MAX_PDF_PAGES and asyncio.to_thread to PDFService
     ▼
6. Phase 6 (Prompt Injection)
     │  Sanitizes delimiter collisions in analyst, critic, and builder agents
     ▼
7. Phase 7 (Rate Limiting)
     │  Adds token bucket / in-memory concurrency limiter on research endpoints
     ▼
8. Phase 8 (Container Hardening)
     │  Updates Dockerfile.backend with unprivileged user
     ▼
9. Phase 9 & 10 (Supply Chain & Information Disclosure)
     │  Removes error detail leakage in production; validates manifests
```

---

## 4. Files Targeted for Remediation

### Files That Will Change:
1. `backend/storage/session_store.py` (User/tenant namespacing, BOLA prevention)
2. `backend/api/routes/research.py` (Auth dependency, BOLA enforcement, async PDF offloading, rate limiting)
3. `backend/api/routes/websocket.py` (Origin validation, auth token/identity extraction)
4. `backend/services/semantic_scholar_service.py` (Outbound SSRF guard, redirect safety)
5. `backend/services/web_scraper_service.py` (Shared SSRF/IP safety validation)
6. `backend/services/pdf_service.py` (Page limits, async thread safety)
7. `backend/core/config.py` (Explicit default CORS origins, auth configuration)
8. `backend/api/main.py` (CORS hardening, security headers middleware)
9. `backend/agents/analyst_agent.py` (Prompt delimiter escaping)
10. `backend/agents/critic_agent.py` (Prompt delimiter escaping)
11. `backend/agents/builder_agent.py` (Prompt delimiter escaping)
12. `frontend/package.json` (Add `mermaid` dependency)
13. `frontend/src/components/ui/MermaidViewer.tsx` (Replace `new Function()` CDN loader with bundled import)
14. `frontend/src/lib/api.ts` (Propagate client user identity header)
15. `frontend/src/lib/websocket.ts` (Propagate client user identity query param)
16. `Dockerfile.backend` (Non-root `USER` directive)
17. `backend/tests/test_security.py` (Comprehensive adversarial regression tests)

### Files That Must NOT Change (Preserve Architecture):
- `backend/core/dag_engine.py` (Core custom DAG engine)
- `backend/core/evidence_graph.py` (Evidence graph model)
- `backend/core/research_sufficiency.py` (Research sufficiency judge)
- `backend/agents/contradiction_agent.py` (Contradiction matrix logic)
- `backend/agents/citation_auditor.py` (Citation grounding logic)
- `backend/agents/orchestrator.py` (Core multi-agent coordination)
- `backend/models/schemas.py` (Core research request/response schemas)

---

## 5. Security Regression Test Strategy

Before applying each fix, a dedicated adversarial test case must be defined and verified to fail (or demonstrate the vulnerability), and then pass post-remediation:
- `test_unauthenticated_session_access_blocked` / `test_cross_user_bola_blocked`
- `test_websocket_unauthorized_origin_rejected`
- `test_semantic_scholar_ssrf_private_ip_and_redirect_blocked`
- `test_pdf_page_limit_enforced`
- `test_prompt_delimiter_escape_neutralized`
- `test_rate_limit_exceeded_returns_429`
- `test_security_headers_present`
