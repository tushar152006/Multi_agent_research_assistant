import asyncio
import logging
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class WebResult(BaseModel):
    title: str
    url: str
    content: str
    relevance_score: int = 0

class WebScraperService:
    """Service to search the web and scrape content from top results."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def search_and_scrape(self, query: str, max_results: int = 3) -> List[WebResult]:
        """Search the web and scrape the top results."""
        results = []
        try:
            # Run DDGS in a thread to avoid blocking async loop if it's not native async
            # duckduckgo_search 6.x DDGS is sync, but we can use it simply.
            with DDGS() as ddgs:
                ddgs_results = list(ddgs.text(query, max_results=max_results))
            
            tasks = []
            for res in ddgs_results:
                tasks.append(self.scrape_url(res["title"], res["href"]))
            
            scraped_results = await asyncio.gather(*tasks)
            results = [r for r in scraped_results if r]
            
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            
        return results

    async def scrape_url(self, title: str, url: str) -> Optional[WebResult]:
        """Scrape a single URL and return clean text."""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove script and style elements
                for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                    script_or_style.decompose()
                
                # Get text
                text = soup.get_text(separator=" ", strip=True)
                
                # Limit content size for LLM context safety
                content = text[:2000] if len(text) > 2000 else text
                
                return WebResult(
                    title=title,
                    url=url,
                    content=content
                )
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None
