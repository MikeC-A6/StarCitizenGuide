import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers

    def scrape_url(self, url: str) -> Dict[str, str]:
        """Scrape content from a single URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                content = {}
                
                # Find the Quick facts section
                quick_facts = {}
                
                # Look for the Cost section which contains price info
                cost_info = {}
                
                # Find standalone price
                standalone_row = soup.find('tr', string=lambda text: text and 'Standalone' in text)
                if standalone_row:
                    price_cell = standalone_row.find_next('td')
                    if price_cell:
                        pledge_price = price_cell.get_text(strip=True)
                        cost_info['pledge_price'] = pledge_price
                
                # Find in-game price
                ingame_row = soup.find('tr', string=lambda text: text and 'In-game price' in text)
                if ingame_row:
                    price_cell = ingame_row.find_next('td')
                    if price_cell:
                        ingame_price = price_cell.get_text(strip=True)
                        cost_info['in_game_price'] = ingame_price
                
                # Find purchase locations
                location_row = soup.find('tr', string=lambda text: text and 'Purchase location' in text)
                if location_row:
                    location_cell = location_row.find_next('td')
                    if location_cell:
                        locations = location_cell.get_text(strip=True)
                        cost_info['purchase_locations'] = locations
                
                content['cost'] = cost_info
                
                # Get the main description
                main_content = soup.find('div', {'class': 'mw-parser-output'})
                if main_content:
                    # Get the first paragraph after the intro
                    paragraphs = main_content.find_all('p')
                    if paragraphs:
                        content['description'] = paragraphs[0].get_text(strip=True)
                
                return {
                    "url": url,
                    "content": content
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
