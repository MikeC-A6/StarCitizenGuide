import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class PriceDataManager:
    def __init__(self, cache_file: str = "cache/price_data.json", cache_duration_hours: int = 24):
        self.cache_file = cache_file
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.price_data = {}
        self.last_update = None
        
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        # Load cached data if available
        self._load_cache()
        
        # Update cache if needed
        if self._needs_update():
            self.update_price_data()

    def _load_cache(self) -> None:
        """Load price data from cache file if it exists"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.price_data = data.get('prices', {})
                    self.last_update = datetime.fromisoformat(data.get('last_update', '2000-01-01'))
                    logger.info("Price data loaded from cache")
        except Exception as e:
            logger.error(f"Error loading price cache: {str(e)}")
            self.price_data = {}
            self.last_update = None

    def _save_cache(self) -> None:
        """Save current price data to cache file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'prices': self.price_data,
                    'last_update': self.last_update.isoformat()
                }, f)
            logger.info("Price data saved to cache")
        except Exception as e:
            logger.error(f"Error saving price cache: {str(e)}")

    def _needs_update(self) -> bool:
        """Check if the cache needs to be updated"""
        if not self.last_update:
            return True
        return datetime.now() - self.last_update > self.cache_duration

    def update_price_data(self) -> None:
        """Fetch and update price data from starcitizen.tools"""
        try:
            url = "https://starcitizen.tools/Purchasing_ships"
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the price table
                price_table = soup.find('table')
                if not price_table:
                    logger.error("Price table not found on the page")
                    return

                # Parse table rows
                new_prices = {}
                for row in price_table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) >= 3:  # Manufacturer, Ship, Base Price columns
                        ship_name = cols[1].get_text(strip=True)
                        price_text = cols[2].get_text(strip=True)
                        try:
                            # Convert price to integer, removing commas
                            price = int(price_text.replace(',', ''))
                            new_prices[ship_name] = price
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse price for {ship_name}: {price_text}")

                if new_prices:
                    self.price_data = new_prices
                    self.last_update = datetime.now()
                    self._save_cache()
                    logger.info(f"Updated prices for {len(new_prices)} ships")
                else:
                    logger.warning("No price data was parsed")

            else:
                logger.error(f"Failed to fetch price data: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating price data: {str(e)}")

    def get_ship_price(self, ship_name: str) -> Optional[int]:
        """Get the base price for a specific ship"""
        # Check if cache needs update
        if self._needs_update():
            self.update_price_data()
            
        # Try to find the exact match first
        if ship_name in self.price_data:
            return self.price_data[ship_name]
            
        # Try case-insensitive match
        ship_name_lower = ship_name.lower()
        for name, price in self.price_data.items():
            if name.lower() == ship_name_lower:
                return price
                
        return None

    def get_all_prices(self) -> Dict[str, int]:
        """Get all cached ship prices"""
        # Check if cache needs update
        if self._needs_update():
            self.update_price_data()
        return self.price_data.copy() 