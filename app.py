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

        # Get list of all available ships for context
        all_ships = ship_manager.get_all_ships()
        
        # Use LLM to identify the ship
        ship_identification_prompt = f"""Given this query about Star Citizen ships: "{query}"
        And this list of available ships: {all_ships}
        
        What specific ship is being asked about? Return ONLY the exact ship name from the list.
        If multiple ships are mentioned, return the main one being asked about.
        If no specific ship is mentioned or the ship isn't in the list, return "NONE".
        
        Ship name:"""
        
        ship_name = query_ship_data(ship_identification_prompt).strip()
        
        if ship_name == "NONE" or ship_name not in all_ships:
            return jsonify({
                "success": False,
                "error": "Could not identify which ship you're asking about. Please include the full ship name in your query."
            }), 400

        # For price/location queries
        if "cost" in query.lower() or "price" in query.lower() or "buy" in query.lower():
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
            return jsonify({
                "success": False,
                "error": f"Could not find data for {ship_name}"
            }), 404

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