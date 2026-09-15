# 03 — SYSTEM THREAT MODEL & INVARIANTS

**Target System**: Multi-Agent Research Assistant  
**Authoritative Path**: `c:\Users\DELL\Downloads\Multi_agent_research_assitant`  
**Methodology**: STRIDE + OWASP Top 10 API (2023) + OWASP Top 10 for LLM Applications (2025)

---

## 1. Threat Actors & Capabilities

| Threat Actor | Motivation | Access Level / Capabilities |
|---|---|---|
| **Unauthenticated External Attacker** | Data theft, quota theft, DoS | Direct network access to public HTTP & WebSocket ports; can submit queries, upload PDFs, call REST APIs. |
| **Malicious Webmaster / Academic Publisher** | System compromise, disinformation | Controls external websites indexed by DuckDuckGo or papers indexed by Semantic Scholar; can serve crafted HTML or PDFs containing prompt injection payloads or redirecting to internal network addresses. |
| **Malicious Authorized Tenant / User** | Privilege escalation, espionage | Legitimate user of the shared platform attempting to view other researchers' confidential literature reviews, proprietary pre-prints, or delete other users' sessions. |
| **Compromised Upstream Dependency / CDN** | Remote code execution on clients | Controls or tampers with external script feeds (e.g. `cdn.jsdelivr.net`) to compromise browser sessions. |

---

## 2. Core Assets & Security Invariants

### 2.1 Critical Assets
1. **Confidential Research Sessions**: User queries, proprietary uploaded PDF texts, notes, and generated synthesis reports stored in `backend/data/sessions/`.
2. **API Credentials & Quotas**: `GROQ_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, server CPU/memory, and external service rate limits.
3. **Internal Network Infrastructure**: Localhost services (e.g., local Ollama daemon on `127.0.0.1:11434`, backend services, Docker host interfaces, cloud metadata endpoints `169.254.169.254`).
4. **Client Browser Execution Context**: User session integrity, DOM security, and protection against Cross-Site Scripting (XSS).
5. **Research Integrity & Provenance**: Assurance that scientific claims and citations correspond to real literature and cannot be forged by indirect prompt injection.

### 2.2 Formal Security Invariants
- **Invariant 1 (Data Segregation)**: *User A must not be able to view, list, export, or delete the research sessions or uploaded documents belonging to User B.*
- **Invariant 2 (Network Boundary / SSRF)**: *No external input (query, URL, metadata) may cause the backend to issue requests to loopback (`127.0.0.0/8`), private RFC1918 subnets, link-local addresses, or cloud metadata endpoints.*
- **Invariant 3 (Resource Boundedness)**: *An uploaded document or query must not consume unbounded server memory or monopolize the asynchronous event loop.*
- **Invariant 4 (Prompt Isolation / AI Boundary)**: *External untrusted data (abstracts, scraped pages, PDF text) must never be interpreted as instructions by the LLM, nor escape isolation delimiters.*
- **Invariant 5 (Execution Integrity)**: *Generated reports and diagram representations must not execute arbitrary JavaScript within the user's browser.*
- **Invariant 6 (Credential Secrecy)**: *API keys and secrets must never be leaked through HTTP response bodies, WebSocket event frames, or client-side JavaScript bundles.*

---

## 3. STRIDE Threat Mapping

| STRIDE Category | Threat Description | Affected Components | Invariant Violated |
|---|---|---|---|
| **Spoofing** | Cross-Site WebSocket Hijacking (CSWSH) and unauthenticated session access. | `routes/websocket.py`, `routes/research.py` | Invariant 1 |
| **Tampering** | Deleting or modifying other users' sessions; poisoning knowledge graph via indirect prompt injection. | `SessionStore`, `analyst_agent.py`, `builder_agent.py` | Invariant 1, Invariant 4 |
| **Repudiation** | Actions performed across sessions without user identity logging or audit trail. | `main.py`, `routes/research.py` | Invariant 1 |
| **Information Disclosure** | Unauthenticated enumeration and export of research reports; SSRF to cloud metadata. | `SessionStore.list_sessions`, `semantic_scholar_service.py` | Invariant 1, Invariant 2, Invariant 6 |
| **Denial of Service** | Unbounded PDF page extraction and synchronous CPU execution; concurrent WebSocket flooding. | `pdf_service.py`, `routes/websocket.py` | Invariant 3 |
| **Elevation of Privilege** | Remote code execution in user browser via untrusted CDN script loading. | `MermaidViewer.tsx` | Invariant 5 |

---

## 4. Agentic & LLM-Specific Threat Taxonomy (OWASP LLM 2025)

```
[Attacker-Crafted Paper / Scraped Page]
          │
          ▼
   (Indirect Prompt Injection via Ingestion)
          │
          ├─► Delimiter Collision: Injects "</untrusted_research_data>"
          │
          ▼
   [Analyst Agent]
          │ (Forced to output attacker-controlled themes / bogus consensus)
          ▼
   [Critic Agent & Builder Agent]
          │ (Downstream agents inherit injected conclusions)
          ▼
   [Evidence Graph & Final Implementation Plan]
          │ (Attacker alters commercial recommendations / suppresses contradictions)
          ▼
   [User Dashboard Presentation]
```

1. **LLM01: Prompt Injection (Indirect)**: External research text escapes `<untrusted_research_data>` tag due to lack of delimiter escaping, steering Analyst and Builder agent conclusions.
2. **LLM04: Model Denial of Service**: Long, repetitive documents trigger token context limits and Groq API rate limit exhaustion.
3. **LLM07: System Prompt & Intellectual Property Leakage**: System instructions and prompt templates can be retrieved by an attacker prompting the agent to print its prompt.
4. **LLM08: Excessive Agency**: System autonomously initiates outbound web scraping and PDF downloads based on expanded search query terms.
