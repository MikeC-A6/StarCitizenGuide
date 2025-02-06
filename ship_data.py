import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ShipDataManager:
    def __init__(self, data_file: str = "attached_assets/Starships.txt", combined_data_file: str = "attached_assets/combined_star_citizen_ships.json"):
        self.data_file = data_file
        self.combined_data_file = combined_data_file
        self.ship_data = self._load_data()
        self.combined_data = self._load_combined_data()
        self.merged_data = self._merge_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load ship data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading ship data: {str(e)}")
            return {}

    def _load_combined_data(self) -> Dict[str, Any]:
        """Load combined ship data from JSON file"""
        try:
            with open(self.combined_data_file, 'r') as f:
                ships_list = json.load(f)
                # Convert list to dictionary with ship names as keys
                ships_dict = {}
                for ship in ships_list:
                    # Use the name field as the key
                    if "name" in ship:
                        ships_dict[ship["name"]] = ship
                return ships_dict
        except Exception as e:
            logger.error(f"Error loading combined ship data: {str(e)}")
            return {}

    def _merge_data(self) -> Dict[str, Any]:
        """Merge both data sources, prioritizing combined data for certain fields"""
        merged = {}
        
        # First, add all ships from the original data
        for ship_name, ship_info in self.ship_data.items():
            merged[ship_name] = {
                "original_data": ship_info,
                "combined_data": None
            }
        
        # Then add or update with combined data
        for ship_name, ship_info in self.combined_data.items():
            normalized_name = ship_name.strip()
            if normalized_name in merged:
                merged[normalized_name]["combined_data"] = ship_info
            else:
                merged[normalized_name] = {
                    "original_data": None,
                    "combined_data": ship_info
                }
        
        return merged

    def get_all_ships(self) -> List[str]:
        """Return list of all ship names"""
        return list(self.merged_data.keys())

    def find_relevant_ships(self, query: str) -> Dict[str, Any]:
        """Find ships relevant to the query"""
        relevant_ships = {}
        query_terms = query.lower().split()
        
        # First try to find exact ship matches
        for ship_name, ship_info in self.merged_data.items():
            # Check for exact ship name matches first
            ship_terms = ship_name.lower().split()
            if all(term in ship_name.lower() for term in query_terms if len(term) > 2):
                relevant_ships[ship_name] = self._combine_ship_data(ship_info)
                
        # If no exact matches, try broader matching
        if not relevant_ships:
            for ship_name, ship_info in self.merged_data.items():
                if any(term in ship_name.lower() for term in query_terms if len(term) > 2):
                    relevant_ships[ship_name] = self._combine_ship_data(ship_info)
                elif self._check_ship_attributes(ship_info, query_terms):
                    relevant_ships[ship_name] = self._combine_ship_data(ship_info)
                
        return relevant_ships

    def _combine_ship_data(self, ship_info: Dict[str, Any]) -> Dict[str, Any]:
        """Combine data from both sources into a single ship record"""
        combined = {}
        
        original_data = ship_info.get("original_data", {})
        extra_data = ship_info.get("combined_data", {})
        
        if original_data:
            combined.update(original_data)
            
        if extra_data:
            # Add or update with combined data fields
            combined["in_game_price"] = extra_data.get("price")
            combined["manufacturer"] = extra_data.get("manufacturer")
            combined["size"] = extra_data.get("size")
            combined["cargo_capacity"] = extra_data.get("cargo_capacity")
            combined["crew_size"] = extra_data.get("crew_size")
            combined["role"] = extra_data.get("role")
            # Add any additional fields from combined data that are useful
            
        return combined

    def _check_ship_attributes(self, ship_info: Dict[str, Any], query_terms: List[str]) -> bool:
        """Check if ship attributes match query terms"""
        matches = False
        
        # Check original data
        if ship_info.get("original_data"):
            printouts = ship_info["original_data"].get('printouts', {})
            
            # Check manufacturer
            manufacturer = printouts.get('Manufacturer', [])
            if manufacturer and any(term in manufacturer[0].get('fulltext', '').lower() for term in query_terms):
                matches = True
                
            # Check roles
            roles = printouts.get('Role', [])
            if any(any(term in role.lower() for term in query_terms) for role in roles):
                matches = True
        
        # Check combined data
        if ship_info.get("combined_data"):
            combined_data = ship_info["combined_data"]
            
            # Check manufacturer
            if combined_data.get("manufacturer") and any(term in combined_data["manufacturer"].lower() for term in query_terms):
                matches = True
                
            # Check role
            if combined_data.get("role") and any(term in combined_data["role"].lower() for term in query_terms):
                matches = True
                
            # Check price for "cheap" queries
            if "cheap" in query_terms and combined_data.get("price"):
                try:
                    price = float(combined_data["price"])
                    if price < 2000000:  # Consider ships under 2M aUEC as cheap
                        matches = True
                except (ValueError, TypeError):
                    pass
                    
            # Check cargo capacity for cargo-related queries
            if any(term in ["cargo", "transport", "hauling"] for term in query_terms) and combined_data.get("cargo_capacity"):
                matches = True
                
        return matches

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
        ship_info = self.merged_data.get(ship_name, {})
        if ship_info.get("original_data"):
            return ship_info["original_data"].get('fullurl', '')
        return ''

    def get_specific_ship_url(self, query: str) -> str:
        """Get URL for a specific ship based on query"""
        # Normalize query
        query = query.lower()
        
        # First try exact match
        for ship_name, ship_info in self.merged_data.items():
            if query in ship_name.lower():
                if ship_info.get("original_data"):
                    return ship_info["original_data"].get('fullurl', '')
                
        return ''

    def get_ship_price(self, ship_name: str) -> int:
        """Get the in-game price for a specific ship"""
        ship_info = self.merged_data.get(ship_name, {})
        if ship_info.get("combined_data"):
            try:
                return int(ship_info["combined_data"].get("price", 0))
            except (ValueError, TypeError):
                return 0
        return 0
