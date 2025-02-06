import os
import logging
import json
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
        
        # First, determine if this is a general question or about a specific ship
        query_type_prompt = f"""Given this query about Star Citizen ships: "{query}"
        Determine if this is a general question about ships or about a specific ship.
        Return ONLY one of these exact words:
        - "GENERAL" for general questions about ships, comparisons, or recommendations
        - "SPECIFIC" for questions about a specific ship
        
        Type:"""
        
        query_type = query_ship_data(query_type_prompt).strip()
        
        if query_type == "GENERAL":
            # Get the raw data from both sources
            context = {
                "query": query,
                "ship_data": ship_manager.ship_data,  # Original data
                "combined_data": ship_manager.combined_data,  # New combined data with prices
                "all_ships": all_ships
            }
            
            prompt = f"""Based on this Star Citizen ship data: {context}
            Please provide a detailed answer to this general question about ships: {query}
            
            You have access to two data sources in the context:
            1. ship_data: Contains detailed ship information including roles, manufacturers, and specifications
            2. combined_data: Contains additional information including in-game prices and cargo capacities
            
            For this query about ships:
            1. Analyze both data sources to find relevant ships
            2. Look for ships that match the query criteria (price, cargo capacity, etc.)
            3. Compare and combine information from both sources
            4. Provide specific examples with actual prices and specifications
            5. Sort recommendations by value/relevance
            
            When discussing prices:
            - For ships under 1M aUEC, show as "**XXX,XXX** aUEC"
            - For ships over 1M aUEC, show as "**X.XX** million aUEC"
            - Always include the cargo capacity if available
            - Always mention the role/purpose of each ship
            
            Format your response using proper markdown:
            - Use ## for section headings (in title case)
            - Use bullet points for lists
            - Use **bold** for numbers and key stats
            - Use *italics* for missing information or additional context
            - Format cargo capacity as "**X** SCU"
            
            Structure your response with these sections:
            ## Overview
            Brief summary of available options
            
            ## Top Recommendations
            List of best options with full details
            
            ## Additional Options
            Other choices worth considering
            
            ## Summary
            Quick recap of best value options"""
            
            response_text = query_ship_data(prompt)
            
            # Include both data sources
            sources = [
                "https://starcitizen.tools/Purchasing_ships",
                "https://starcitizen.tools/Ships"
            ]
            
            return jsonify({
                "success": True,
                "response": response_text,
                "sources": sources
            })
            
        else:
            # Get the specific ship name for SPECIFIC queries
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

            # Handle price/location queries
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
            
            # For other types of queries about specific ships
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

            # Get the ship's URL and scrape additional data
            ship_url = ship_manager.get_specific_ship_url(ship_name)
            scraped_data = {}
            if ship_url:
                logger.info(f"Scraping data for ship URL: {ship_url}")
                scraped_results = web_scraper.scrape_multiple_urls([ship_url])
                logger.info(f"Scraped results: {json.dumps(scraped_results, indent=2)}")
                if scraped_results and scraped_results[0].get('content'):
                    scraped_data = scraped_results[0]['content']
                    logger.info(f"Extracted content: {json.dumps(scraped_data, indent=2)}")

            context = {
                "query": query,
                "ship_data": {ship_name: ship_info},  # Base ship data
                "scraped_data": scraped_data,  # Additional scraped information
                "ship_url": ship_url
            }
            
            logger.info(f"Full context being sent to LLM: {json.dumps(context, indent=2)}")

            prompt = f"""Based on this Star Citizen ship data: {context}
                Please provide a detailed answer to: {query}
                
                Important notes:
                1. Use both the base ship data and the scraped web data to provide the most complete answer
                2. The scraped_data contains several important sections:
                   - 'description': General ship description
                   - 'features': Detailed features including weapons information
                   - 'specifications': Detailed specifications including weapon hardpoints
                   - 'weapons': Specific weapon information including sizes and configurations
                3. If information is found in the scraped data but not in the base data, use the scraped data
                4. For weapon-related queries, check both the 'weapons' section and 'specifications' section
                5. Provide specific details and numbers when available
                
                When discussing weapons:
                - Include both fixed and gimbaled weapon options
                - Specify the size and number of hardpoints
                - Mention default weapon loadout if available
                - Include weapon mounting locations (e.g., nose, wings)
                
                Format your response using proper markdown:
                - Use ## for section headings (in title case)
                - Use bullet points for lists
                - Use **bold** for emphasis on important information and numbers
                - Use *italics* for supplementary information
                - Format all measurements consistently (e.g., "**Size 2**" for weapon sizes)
                - Use proper spacing between sections
                
                Important formatting rules:
                1. Keep all text in the same color (don't use special formatting for units)
                2. Use consistent formatting for all measurements
                3. Don't use any custom HTML or color codes
                4. Keep all text either in the default color or specifically bold/italic as specified above"""

            response_text = query_ship_data(prompt)

            # Include the ship's URL in sources
            sources = []
            if ship_url:
                sources.append(ship_url)

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