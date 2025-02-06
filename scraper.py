import logging
import trafilatura
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers

    def scrape_url(self, url: str) -> Dict[str, str]:
        """Scrape content from a single URL"""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded)
                return {
                    "url": url,
                    "content": content if content else "No content extracted"
                }
            return {"url": url, "content": "Failed to download content"}
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"url": url, "content": f"Error: {str(e)}"}

    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, str]]:
        """Scrape multiple URLs concurrently"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_url, url): url for url in urls}
            for future in as_completed(future_to_url):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    url = future_to_url[future]
                    logger.error(f"Error processing {url}: {str(e)}")
                    results.append({"url": url, "content": f"Error: {str(e)}"})
                    
        return results
