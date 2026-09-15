# 08 — UNRESOLVED FINDINGS (NEEDS VALIDATION)

**Target System**: Multi-Agent Research Assistant  
**Authoritative Path**: `c:\Users\DELL\Downloads\Multi_agent_research_assitant`  

---

## 1. Item Ref: SEC-007
**Title**: Potential Time-of-Check to Time-of-Use (TOCTOU) DNS Rebinding in WebScraperService  
**Category**: Server-Side Request Forgery (SSRF)  
**CWE**: CWE-367  
**OWASP API**: API7:2023 Server-Side Request Forgery  
**Severity**: LOW  
**Confidence**: LOW  

### Technical Description
In `backend/services/web_scraper_service.py`:
```python
@staticmethod
def is_safe_url(url: str) -> bool:
    ...
    addr_info = socket.getaddrinfo(hostname, None)
    for item in addr_info:
        ip = ipaddress.ip_address(item[4][0])
        if ip.is_private or ip.is_loopback ...:
            return False
    return True

async def scrape_url(self, title: str, url: str) -> Optional[WebResult]:
    if not self.is_safe_url(url):
        return None
    ...
    async with httpx.AsyncClient(...) as client:
        response = await client.get(url)
```

### Why it Needs Validation:
1. `is_safe_url()` performs an initial DNS resolution using Python's `socket.getaddrinfo()`.
2. When `client.get(url)` is invoked, `httpx` initiates its own independent connection and DNS resolution.
3. If an attacker controls an authoritative DNS nameserver configured with a Time-To-Live (TTL) of 0 seconds, the first DNS request from `socket.getaddrinfo()` could return a legitimate public IP address (e.g. `93.184.216.34`), passing the check. The second DNS resolution performed milliseconds later by `httpx` could return `127.0.0.1` or `169.254.169.254`.

### Attack Feasibility & Real-World Constraints:
- In this specific architecture, `scrape_url()` receives URLs discovered via DuckDuckGo search results (`ddgs.text(query)`).
- An attacker would need to get an actively rebinding domain indexed by DuckDuckGo and ranked within the top 3 results for academic research queries.
- Furthermore, modern OS-level DNS resolvers often cache negative or sub-second TTL responses for a minimum duration.

### Validation Experiment Required:
To definitively prove or disprove this finding:
1. Configure a local DNS rebinding test harness (e.g. `127.0.0.1.xip.name` or `rbndr.us`).
2. Run automated consecutive `is_safe_url()` and `client.get()` calls to measure whether `httpx` hits the rebound loopback address in a realistic Python runtime environment.

### Recommended Proactive Fix (Defense-in-Depth):
Pin the validated IP address directly by connecting to `http://<validated_ip>` with the `Host: <original_hostname>` header, or use a custom `httpx.AsyncHTTPTransport` with a custom socket resolver.
