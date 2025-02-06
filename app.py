import os
import logging
from flask import Flask, render_template, jsonify, request
from ship_data import ShipDataManager
from scraper import WebScraper
from gemini_client import query_ship_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_123")

# Initialize managers
ship_manager = ShipDataManager()
web_scraper = WebScraper()

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

        # Get base ship data
        ship_data = ship_manager.find_relevant_ships(query)

        # Generate response using Gemini
        context = f"""Query about Star Citizen ships: {query}
                     Available ship data: {ship_data}"""

        response_text = query_ship_data(context)

        # If we need additional data
        if "insufficient information" in response_text.lower():
            urls = ship_manager.get_relevant_urls(ship_data)
            additional_data = web_scraper.scrape_multiple_urls(urls)

            # Generate new response with additional data
            enhanced_context = f"""{context}
                                 Additional ship information: {additional_data}"""
            response_text = query_ship_data(enhanced_context)

        return jsonify({
            "success": True,
            "response": response_text,
            "sources": ship_manager.get_data_sources(ship_data)
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