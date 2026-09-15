# 09 — PRIORITIZED REMEDIATION ROADMAP

**Target System**: Multi-Agent Research Assistant  
**Authoritative Path**: `c:\Users\DELL\Downloads\Multi_agent_research_assitant`  
**Classification**: Engineering Remediation Plan (Awaiting User Authorization)  

---

## Remediation Philosophy
All proposed fixes adhere strictly to the principle of **minimal blast radius with maximum defensive efficacy**. No heavy third-party framework additions are required.

---

## 🚨 Priority 1: Critical Security Boundaries (Immediate Fixes)

### 1.1 Unify Outbound Fetching & Neutralize SSRF (SEC-003)
- **Component**: `backend/services/semantic_scholar_service.py`
- **Action**:
  - Integrate `WebScraperService.is_safe_url()` or extract a shared `SafeHttpClient` module.
  - Apply IP validation to `pdf_url` before issuing requests in `SemanticScholarService.fetch_pdf_text()`.
  - Set `follow_redirects=False` or implement an `on_response` hook in `httpx` to validate intermediate redirect targets.
- **Architectural Impact**: Component-level fix.

### 1.2 Replace Dynamic CDN Script Import in Frontend (SEC-006)
- **Component**: `frontend/src/components/ui/MermaidViewer.tsx`, `frontend/package.json`
- **Action**:
  - Add `mermaid` (`^11.x`) to `frontend/package.json` dependencies.
  - Replace the `new Function("url", "return import(url)")` call with Next.js bundled dynamic import:
    ```typescript
    import("mermaid").then((m) => {
      const mermaid = m.default || m;
      ...
    });
    ```
- **Architectural Impact**: Local component fix.

### 1.3 Secure CORS & WebSocket Handshake (SEC-002, SEC-008)
- **Component**: `backend/core/config.py`, `backend/api/main.py`, `backend/api/routes/websocket.py`
- **Action**:
  - In `config.py`, default `allowed_origins` to `["http://localhost:3000", "http://127.0.0.1:3000"]` instead of `["*"]`.
  - In `websocket.py`, inspect `ws.headers.get("origin")` and reject unauthorized origins with HTTP 403 before `ws.accept()`.
- **Architectural Impact**: Local configuration & route fix.

---

## ⚡ Priority 2: Resilience & AI Defense (Hardening)

### 2.1 Sanitize Prompt Isolation Tags Against Delimiter Collision (SEC-005)
- **Component**: `backend/agents/analyst_agent.py`, `critic_agent.py`, `builder_agent.py`
- **Action**:
  - Define a sanitization utility:
    ```python
    def escape_untrusted_data(text: str) -> str:
        return text.replace("</untrusted_research_data>", "&lt;/untrusted_research_data&gt;")
    ```
  - Apply `escape_untrusted_data` to all variables interpolated inside `<untrusted_research_data>` blocks.
- **Architectural Impact**: Local agent prompt helper.

### 2.2 Protect Event Loop Against PDF Denial of Service (SEC-004)
- **Component**: `backend/services/pdf_service.py`, `backend/api/routes/research.py`
- **Action**:
  - Enforce a maximum page threshold (`MAX_PDF_PAGES = 100`) in `PdfService._extract_pdf_text`.
  - Wrap synchronous text extraction in `await asyncio.to_thread(pdf_service.extract_text_from_bytes, payload)` inside `research.py`.
- **Architectural Impact**: Local service & route fix.

### 2.3 Add Rate Limiting on Research Ingress (SEC-010)
- **Component**: `backend/api/main.py`, `backend/api/routes/research.py`
- **Action**:
  - Add `slowapi` limiter middleware to FastAPI app.
  - Apply `@limiter.limit("5/minute")` to `POST /api/v1/research` and `POST /api/v1/research/upload-pdf`.
- **Architectural Impact**: Middleware addition.

---

## 🛡️ Priority 3: Authentication & Multi-Tenancy Architecture (Strategic)

### 3.1 Implement Session Ownership & Tenant Authorization (SEC-001)
- **Component**: `backend/storage/session_store.py`, `backend/api/routes/research.py`
- **Action**:
  - Introduce an authentication dependency (e.g. bearer token or API key header).
  - Scope session paths to user identities: `sessions/{user_id}/{session_id}.json`.
  - Enforce ownership validation on `GET`, `EXPORT`, and `DELETE` endpoints.
- **Architectural Impact**: Architecture-level change (requires defining user auth model).

### 3.2 Container & Infrastructure Hardening (SEC-009, SEC-011)
- **Component**: `Dockerfile.backend`, `backend/api/main.py`
- **Action**:
  - In `Dockerfile.backend`, add:
    ```dockerfile
    RUN groupadd -r appuser && useradd -r -g appuser appuser
    USER appuser
    ```
  - In `main.py`, add custom middleware injecting standard security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, etc.).
- **Architectural Impact**: Infrastructure configuration.
