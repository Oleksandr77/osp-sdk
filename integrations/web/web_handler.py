import logging
import requests
from bs4 import BeautifulSoup
from googlesearch import search

logger = logging.getLogger(__name__)

from duckduckgo_search import DDGS

class WebHandler:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def search_web(self, query, limit=10, engine="duckduckgo"):
        """Performs a web search using the specified engine or strategy."""
        logger.info(f"Searching Web ({engine}): {query}")
        results = []
        try:
            if engine == "google":
                # Google Search Logic
                gen = search(query, num_results=limit, advanced=True)
                for result in gen:
                    results.append({
                        "title": result.title,
                        "url": result.url,
                        "description": result.description,
                        "source": "Google"
                    })
                    if len(results) >= limit:
                        break
            
            elif engine == "duckduckgo_news":
                # specific news search
                with DDGS() as ddgs:
                    news_gen = ddgs.news(query, max_results=limit)
                    for r in news_gen:
                        results.append({
                            "title": r['title'],
                            "url": r['url'],
                            "description": r['body'],
                            "source": f"News ({r.get('source', '')})"
                        })

            elif engine == "reddit":
                # social sentiment search
                with DDGS() as ddgs:
                    gen = ddgs.text(f"site:reddit.com {query}", max_results=limit)
                    for r in gen:
                        results.append({
                            "title": "🗣️ " + r['title'],
                            "url": r['href'],
                            "description": r['body'],
                            "source": "Reddit/Social"
                        })
            
            elif engine == "academic":
                # PDF/Research search
                with DDGS() as ddgs:
                    gen = ddgs.text(f"{query} filetype:pdf", max_results=limit)
                    for r in gen:
                        results.append({
                            "title": "🎓 " + r['title'],
                            "url": r['href'],
                            "description": r['body'],
                            "source": "Academic/PDF"
                        })

            else:
                # Default DuckDuckGo Text
                with DDGS() as ddgs:
                    ddg_gen = ddgs.text(query, max_results=limit)
                    for r in ddg_gen:
                        results.append({
                            "title": r['title'],
                            "url": r['href'],
                            "description": r['body'],
                            "source": "DuckDuckGo"
                        })

            return results
        except Exception as e:
            logger.error(f"Web Search Error ({engine}): {e}")
            return []

    async def fetch_page_content(self, url):
        """Fetches and cleans text content from a URL."""
        logger.info(f"Fetching URL: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            title = soup.title.string if soup.title else url
            
            return {
                "title": title,
                "url": url,
                "text": clean_text[:50000] # Limit for context
            }
            
        except Exception as e:
            logger.error(f"Page Fetch Error: {e}")
            return {"error": str(e)}
