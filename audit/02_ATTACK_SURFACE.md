# 02 — ATTACK SURFACE INVENTORY

**Target System**: Multi-Agent Research Assistant  
**Authoritative Path**: `c:\Users\DELL\Downloads\Multi_agent_research_assitant`  
**Classification**: Source-Grounded Attack Surface Analysis  

---

## 1. External Ingress Points (Network & API)

### 1.1 HTTP Endpoints (`backend/api/routes/`)

| Method | Path | Auth Required | Input Types / Parameters | Payload Constraints | Handler Location |
|---|---|---|---|---|---|
| `GET` | `/health` | None | None | None | `backend/api/routes/health.py:6` |
| `POST` | `/api/v1/research` | None | JSON Body (`ResearchRequest`) | `query: str (min 3)`, `max_results: int (1..20)`, `query_type: Enum` | `backend/api/routes/research.py:38` |
| `POST` | `/api/v1/research/analyze-doc` | None | JSON Body (`UploadTextRequest`) | `title: str (1..200)`, `content: str (min 20)` | `backend/api/routes/research.py:46` |
| `POST` | `/api/v1/research/upload-pdf` | None | Raw Request Body (`bytes`), Query Param: `title: str` | `Content-Length <= 20MB`, Raw Bytes `<= 20MB` | `backend/api/routes/research.py:62` |
| `GET` | `/api/v1/research` | None | None | Returns all stored session metadata | `backend/api/routes/research.py:164` |
| `GET` | `/api/v1/research/{session_id}` | None | Path Param: `session_id` | Validated by regex `^[a-zA-Z0-9_-]+$` | `backend/api/routes/research.py:146` |
| `DELETE` | `/api/v1/research/{session_id}` | None | Path Param: `session_id` | Validated by regex `^[a-zA-Z0-9_-]+$` | `backend/api/routes/research.py:154` |
| `GET` | `/api/v1/research/export/{session_id}` | None | Path Param: `session_id` | JSON file download | `backend/api/routes/research.py:95` |
| `GET` | `/api/v1/research/{session_id}/export/bibtex` | None | Path Param: `session_id` | BibTeX export download | `backend/api/routes/research.py:110` |
| `GET` | `/api/v1/research/{session_id}/export/markdown` | None | Path Param: `session_id` | Markdown report download | `backend/api/routes/research.py:128` |

### 1.2 WebSocket Endpoint (`backend/api/routes/websocket.py`)

| Protocol | Path | Handshake Auth | Origin Check | Ingress Frame Format | Concurrency Limit | Handler Location |
|---|---|---|---|---|---|---|
| `WS` | `/ws/research` | None | **None** (Accepts any origin) | JSON Text Frame: `{"query": str, "max_results": int, "query_type": str}` | **None** (Unbounded) | `backend/api/routes/websocket.py:20` |

---

## 2. Inbound Data Ingestion Vectors (Untrusted External Sources)

1. **Academic Paper Repositories**:
   - **arXiv Atom Feed**: External XML payloads parsed by `xml.etree.ElementTree` in `ArxivService.parse_response()`. Fields: `title`, `summary`, `author`, `entry_id`.
   - **Semantic Scholar API**: External JSON payloads from `api.semanticscholar.org` parsed in `SemanticScholarService.parse_response()`. Fields: `title`, `abstract`, `authors`, `openAccessPdf.url`.
2. **Open-Access Academic PDFs**:
   - Fetched over HTTP via `ArxivService.fetch_pdf_text()` and `SemanticScholarService.fetch_pdf_text()`.
   - Ingested via user upload at `/api/v1/research/upload-pdf`.
   - Parsed by `pypdf.PdfReader`.
3. **Web Search & Scraped Web Pages**:
   - Query results from DuckDuckGo Search API (`duckduckgo_search.DDGS`).
   - HTML documents retrieved via HTTP GET in `WebScraperService.scrape_url()`.
   - Parsed by `bs4.BeautifulSoup`.

---

## 3. Data Transformation & Propagation Paths

```
Untrusted Input (Query / PDF / Scraped HTML / Academic Paper)
  │
  ├─► [PdfService]: Parses raw bytes -> StructuredDocument (pages, sections)
  │
  ├─► [ReaderAgent]: Extracts findings, creates GroundedChunks with SHA-256 hashes
  │
  ├─► [AnalystAgent]: Synthesizes themes, consensus, conflicts, gaps -> LLM Prompt
  │
  ├─► [ContradictionAgent]: Builds pairwise tension matrix across papers
  │
  ├─► [CitationAuditor]: Fuzzy-matches claims against GroundedChunks -> qualifies unverified
  │
  ├─► [CriticAgent]: Evaluates grounding precision & heuristic flaws -> LLM Prompt
  │
  ├─► [BuilderAgent]: Generates implementation plan & risks -> LLM Prompt
  │
  ├─► [SessionStore]: Serializes final ResearchResponse to filesystem JSON
  │
  └─► [Next.js Frontend]:
        ├── Text & Badges: React DOM nodes
        ├── Markdown: React Markdown components
        └── Diagrams: MermaidViewer -> Dynamic CDN JS + dangerouslySetInnerHTML (SVG)
```

---

## 4. External Egress & Outbound Network Surface

| Destination Host | Protocol / Port | Trigger Component | Authentication / Headers | Sensitive Data Egressed |
|---|---|---|---|---|
| `api.groq.com` | HTTPS / 443 | `GroqService.generate` | `Authorization: Bearer <GROQ_API_KEY>` | User research queries, document abstracts, syntheses |
| `localhost:11434` | HTTP / 11434 | `OllamaService.generate` | None (Local daemon) | User research queries, document abstracts, syntheses |
| `export.arxiv.org` | HTTPS / 443 | `ArxivService.search` | Custom User-Agent | User research query terms |
| `arxiv.org` | HTTPS / 443 | `ArxivService.fetch_pdf_text`| Custom User-Agent | Paper ID |
| `api.semanticscholar.org` | HTTPS / 443 | `SemanticScholarService.search` | Optional `x-api-key` | User research query terms |
| **Arbitrary External Hosts** | HTTP/HTTPS | `SemanticScholarService.fetch_pdf_text` | None | Target PDF URL (Unrestricted HTTP GET) |
| **Arbitrary Scraped Hosts** | HTTP/HTTPS | `WebScraperService.scrape_url` | Browser User-Agent | Target Web Page URL |
| `cdn.jsdelivr.net` | HTTPS / 443 | `MermaidViewer.tsx` (Client) | None | Client browser IP & User-Agent |
| `mermaid.live` | HTTPS / 443 | `MermaidViewer.handleOpenLive` | URL Fragment (`#pako:...`) | Complete diagram code in URL fragment |

---

## 5. Persistence & Local Storage Surface

- **Path**: `backend/data/sessions/`
- **Format**: Flat JSON files named `{session_id}.json`.
- **Operations**:
  - `save_report`: Writes full research report.
  - `get_report`: Reads and deserializes JSON into `ResearchResponse`.
  - `delete_report`: Unlinks file.
  - `list_sessions`: Scans all `*.json` files in the directory.
- **Access Controls**: None. All files accessible to any HTTP caller who knows or lists session IDs.
