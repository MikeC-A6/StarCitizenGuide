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
        
        # First try to find exact ship matches
        for ship_name, ship_info in self.ship_data.items():
            # Check for exact ship name matches first
            ship_terms = ship_name.lower().split()
            if all(term in ship_name.lower() for term in query_terms if len(term) > 2):
                relevant_ships[ship_name] = ship_info
                
        # If no exact matches, try broader matching
        if not relevant_ships:
            for ship_name, ship_info in self.ship_data.items():
                if any(term in ship_name.lower() for term in query_terms if len(term) > 2):
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
        """Determine if web scraping is needed based on query context"""
        query = query.lower()
        
        # Define field mappings for common query topics
        field_mappings = {
            'cargo': ['Cargo capacity'],
            'speed': ['SCM speed', 'Quantum speed'],
            'fuel': ['Hydrogen fuel capacity', 'Quantum fuel capacity'],
            'price': ['Pledge price', 'In-game price'],
            'crew': ['Crew'],
            'role': ['Role'],
            'manufacturer': ['Manufacturer']
        }
        
        # Determine which fields are relevant to the query
        required_fields = []
        for keyword, fields in field_mappings.items():
            if keyword in query:
                required_fields.extend(fields)
                
        # If no specific fields are identified, use a minimal set
        if not required_fields:
            required_fields = ['Manufacturer', 'Role']
            
        # Only check relevant fields for the ships
        for ship_info in ship_data.values():
            printouts = ship_info.get('printouts', {})
            # Only check fields that are relevant to the query
            missing_relevant_data = any(
                field in required_fields and 
                (field not in printouts or not printouts[field])
                for field in required_fields
            )
            if missing_relevant_data:
                return True
                
        return False

    def get_relevant_urls(self, ship_data: Dict[str, Any]) -> List[str]:
        """Extract only the most relevant URLs for web scraping"""
        urls = []
        for ship_info in ship_data.values():
            # Only get the main ship details URL, skip pledge store URL
            if ship_info.get('fullurl'):
                urls.append(ship_info['fullurl'])
                
        return list(set(urls))  # Remove duplicates

    def get_data_sources(self, ship_data: Dict[str, Any]) -> List[str]:
        """Get list of data sources used - only returns URLs for ships that were found in the query"""
        sources = []
        
        # Get the ship names that were actually found in the query
        found_ships = list(ship_data.keys())
        
        # Only include URLs for ships that were actually found/used
        for ship_name, ship_info in self.ship_data.items():
            # Check if this ship was in our query results
            if ship_name in found_ships:
                if ship_info.get('fullurl'):
                    sources.append(ship_info['fullurl'])
                # Include manufacturer URL only if it's relevant to the query
                manufacturer = ship_info.get('printouts', {}).get('Manufacturer', [])
                if manufacturer and manufacturer[0].get('fullurl'):
                    sources.append(manufacturer[0]['fullurl'])
                    
        return list(set(sources))  # Remove any duplicates

    def get_ship_url(self, ship_name: str) -> str:
        """Get the specific URL for a ship"""
        ship_info = self.ship_data.get(ship_name, {})
        return ship_info.get('fullurl', '')

    def get_specific_ship_url(self, query: str) -> str:
        """Get URL for a specific ship based on query"""
        # Normalize query
        query = query.lower()
        
        # First try exact match
        for ship_name, ship_info in self.ship_data.items():
            if query in ship_name.lower():
                return ship_info.get('fullurl', '')
                
        return ''
