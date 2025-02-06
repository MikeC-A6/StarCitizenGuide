import logging
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup, NavigableString
import requests

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers

    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape all relevant data from a given URL. It groups the page’s content
        by sections based on header tags (h2, h3, h4) and extracts table data.
        """
        try:
            logger.info(f"Scraping URL: {url}")
            response = requests.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to download content: {response.status_code}")
                return {"url": url, "content": f"Failed to download content: {response.status_code}"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = soup.find('div', {'class': 'mw-parser-output'})
            if not main_content:
                logger.error("Main content div not found")
                return {"url": url, "content": "No content found"}

            # Initialize sections; content before the first header goes into the "intro" section.
            sections = {}
            current_section = "intro"
            sections[current_section] = []

            # Iterate over the direct contents of the main container.
            # This includes both NavigableString (plain text) and Tag objects.
            for element in main_content.contents:
                # Capture any standalone text nodes
                if isinstance(element, NavigableString):
                    text = element.strip()
                    if text:
                        sections[current_section].append(text)
                    continue

                # If the element is a header tag, start a new section
                if element.name in ['h2', 'h3', 'h4']:
                    header_text = element.get_text(strip=True)
                    current_section = header_text
                    if current_section not in sections:
                        sections[current_section] = []
                    logger.debug(f"New section: {current_section}")
                    continue

                # For other tags (p, div, ul, table, etc.), extract text.
                # Using get_text(separator=' ', strip=True) helps join nested text parts.
                text = element.get_text(separator=' ', strip=True)
                if text:
                    sections[current_section].append(text)

            # Join all text blocks in each section into one string.
            for section in sections:
                sections[section] = "\n".join(sections[section])
                logger.info(f"Section '{section}' captured with {len(sections[section])} characters.")

            # Extract table data: iterate over all tables in the main content.
            tables = []
            for table in main_content.find_all('table'):
                table_rows = []
                for row in table.find_all('tr'):
                    # Look for both header and standard cells
                    cols = row.find_all(['th', 'td'])
                    if cols:
                        row_data = [col.get_text(separator=' ', strip=True) for col in cols]
                        table_rows.append(row_data)
                if table_rows:
                    tables.append(table_rows)
            if tables:
                logger.info(f"Extracted {len(tables)} tables from the page.")

            content = {"sections": sections, "tables": tables}
            return {"url": url, "content": content}

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"url": url, "content": f"Error: {str(e)}"}

    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs concurrently."""
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

if __name__ == '__main__':
    scraper = WebScraper()
    test_url = "https://starcitizen.tools/Mustang_Alpha"
    result = scraper.scrape_url(test_url)
    
    # For a pretty-print of the result
    import pprint
    pprint.pprint(result)

