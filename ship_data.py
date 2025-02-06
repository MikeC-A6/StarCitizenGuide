import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ShipDataManager:
    def __init__(self, data_file: str = "attached_assets/Starships.txt"):
        self.data_file = data_file
        self.ship_data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load ship data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading ship data: {str(e)}")
            return {}

    def get_all_ships(self) -> List[str]:
        """Return list of all ship names"""
        return list(self.ship_data.keys())

    def find_relevant_ships(self, query: str) -> Dict[str, Any]:
        """Find ships relevant to the query"""
        relevant_ships = {}
        query_terms = query.lower().split()
        
        for ship_name, ship_info in self.ship_data.items():
            if any(term in ship_name.lower() for term in query_terms):
                relevant_ships[ship_name] = ship_info
            elif self._check_ship_attributes(ship_info, query_terms):
                relevant_ships[ship_name] = ship_info
                
        return relevant_ships

    def _check_ship_attributes(self, ship_info: Dict[str, Any], query_terms: List[str]) -> bool:
        """Check if ship attributes match query terms"""
        printouts = ship_info.get('printouts', {})
        
        # Check manufacturer
        manufacturer = printouts.get('Manufacturer', [])
        if manufacturer and any(term in manufacturer[0].get('fulltext', '').lower() for term in query_terms):
            return True
            
        # Check roles
        roles = printouts.get('Role', [])
        if any(any(term in role.lower() for term in query_terms) for role in roles):
            return True
            
        return False

    def needs_additional_data(self, query: str, ship_data: Dict[str, Any]) -> bool:
        """Determine if web scraping is needed for complete answer"""
        # Check if we have enough information in structured data
        required_fields = ['Manufacturer', 'Role', 'Cargo capacity', 'SCM speed', 'Quantum speed']
        
        for ship_info in ship_data.values():
            printouts = ship_info.get('printouts', {})
            if not all(field in printouts and printouts[field] for field in required_fields):
                return True
                
        return False

    def get_relevant_urls(self, ship_data: Dict[str, Any]) -> List[str]:
        """Extract relevant URLs for web scraping"""
        urls = []
        for ship_info in ship_data.values():
            # Get ship details page URL
            if ship_info.get('fullurl'):
                urls.append(ship_info['fullurl'])
            
            # Get pledge store URL if available
            pledge_url = ship_info.get('printouts', {}).get('Pledge store URL', [])
            if pledge_url:
                urls.append(pledge_url[0])
                
        return list(set(urls))  # Remove duplicates

    def get_data_sources(self, ship_data: Dict[str, Any]) -> List[str]:
        """Get list of data sources used"""
        sources = []
        for ship_info in ship_data.values():
            if ship_info.get('fullurl'):
                sources.append(ship_info['fullurl'])
        return sources
