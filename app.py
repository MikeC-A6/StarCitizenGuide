import os
import logging
from flask import Flask, render_template, jsonify, request
from ship_data import ShipDataManager
from scraper import WebScraper
from price_data_manager import PriceDataManager
from gemini_client import query_ship_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_123")

# Initialize managers
ship_manager = ShipDataManager()
web_scraper = WebScraper()
price_manager = PriceDataManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ships', methods=['GET'])
def list_ships():
    try:
        ships = ship_manager.get_all_ships()
        return jsonify({"success": True, "ships": ships})
    except Exception as e:
        logger.error(f"Error listing ships: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def query_ship():
    try:
        query = request.json.get('query')
        if not query:
            return jsonify({"success": False, "error": "No query provided"}), 400

        # Extract ship name from query using common patterns
        ship_name = None
        query_lower = query.lower()
        
        # Common patterns for ship name extraction
        patterns = [
            "of the", 
            "about the",
            "is the",
            "for the"
        ]
        
        # Try to extract full ship name with manufacturer
        for pattern in patterns:
            if pattern in query_lower:
                ship_parts = query_lower.split(pattern)
                if len(ship_parts) > 1:
                    potential_name = ship_parts[1].strip()
                    # Get all ship names and sort by length (longest first to match most specific)
                    all_ships = sorted(ship_manager.get_all_ships(), key=len, reverse=True)
                    # Try to match full manufacturer + ship name
                    for ship in all_ships:
                        ship_lower = ship.lower()
                        # Check if both manufacturer and ship name are in the query
                        if "drake" in potential_name and "caterpillar" in potential_name and "drake caterpillar" in ship_lower:
                            ship_name = ship
                            break
                        elif ship_lower in potential_name:
                            ship_name = ship
                            break
                    if ship_name:
                        break

        # If no pattern match, try direct ship name search
        if not ship_name:
            all_ships = sorted(ship_manager.get_all_ships(), key=len, reverse=True)
            for ship in all_ships:
                ship_lower = ship.lower()
                # Prioritize exact manufacturer + ship name matches
                if "drake" in query_lower and "caterpillar" in query_lower and "drake caterpillar" in ship_lower:
                    ship_name = ship
                    break
                elif ship_lower in query_lower:
                    ship_name = ship
                    break

        if not ship_name:
            return jsonify({
                "success": False,
                "error": "Could not identify which ship you're asking about"
            }), 400

        # For price/location queries
        if "cost" in query_lower or "price" in query_lower or "buy" in query_lower:
            ship_url = ship_manager.get_specific_ship_url(ship_name)
            
            if ship_url:
                # Get base price from cache
                base_price = price_manager.get_ship_price(ship_name)
                
                # Scrape the specific ship's data
                logger.info(f"Scraping data for ship URL: {ship_url}")
                scraped_data = web_scraper.scrape_multiple_urls([ship_url])
                
                # Get the base ship data for context
                ship_data = ship_manager.find_relevant_ships(ship_name)
                
                # Prepare context with both structured and scraped data
                context = {
                    "query": query,
                    "ship_data": ship_data,
                    "scraped_data": scraped_data,
                    "base_price": base_price
                }
                
                # Generate response focusing on price and location
                prompt = f"""Based on this Star Citizen ship data and scraped information: {context}
                    Please provide a detailed answer about the in-game price and purchase location for the {ship_name}.
                    The base_price field contains the standard in-game price from the official price list.
                    
                    Format your response in markdown with the following sections:
                    
                    ## 1. Pledge Store Price
                    Include the standalone pledge price if available. Format prices in bold.
                    
                    ## 2. In-Game Price
                    Include both the base price and any variant prices if available. Format prices in bold.
                    If the base price differs from other sources, mention both and explain the difference.
                    
                    ## 3. Purchase Locations
                    List available purchase locations if known. Use bullet points for multiple locations.
                    
                    ## Additional Context
                    Include any relevant context about the ship that helps explain its pricing or availability.
                    
                    For any information that is not available in the data, clearly state that it is not available in *italics*.
                    Use proper markdown formatting for emphasis, lists, and sections."""
                
                response_text = query_ship_data(prompt)
                
                # Add the price list source if we used base price data
                sources = [ship_url]
                if base_price is not None:
                    sources.append("https://starcitizen.tools/Purchasing_ships")
                
                return jsonify({
                    "success": True,
                    "response": response_text,
                    "sources": sources
                })
        
        # For other types of queries
        ship_data = ship_manager.find_relevant_ships(ship_name)
        
        if not ship_data:
            return jsonify({
                "success": False,
                "error": f"No data found for {ship_name}"
            }), 404

        # Get the specific ship's info
        ship_info = ship_data.get(ship_name)
        if not ship_info:
            # Try to find the most specific match
            for name, info in ship_data.items():
                if "drake caterpillar" in name.lower():
                    ship_info = info
                    ship_name = name
                    break
            if not ship_info:
                ship_info = next(iter(ship_data.values()))

        context = {
            "query": query,
            "ship_data": {ship_name: ship_info}  # Only include relevant ship
        }

        response_text = query_ship_data(f"""Based on this Star Citizen ship data: {context}
            Please provide a detailed answer to: {query}
            Format your response using proper markdown:
            - Use ## for section headings
            - Use bullet points for lists
            - Use **bold** for emphasis on important information
            - Use *italics* for supplementary information
            - Use proper spacing between sections
            Format the response in a clear, natural way that is easy to read.""")

        # Get only the URL for the specific ship
        sources = []
        if ship_info.get('fullurl'):
            sources.append(ship_info['fullurl'])

        return jsonify({
            "success": True,
            "response": response_text,
            "sources": sources
        })

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500