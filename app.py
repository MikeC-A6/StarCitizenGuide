import os
import logging
from flask import Flask, render_template, jsonify, request
from ship_data import ShipDataManager
from scraper import WebScraper
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_123")

# Initialize Google Gemini API
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "your-api-key")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-001')

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
        
        # First, try to generate a response with just the structured data
        initial_context = {
            "query": query,
            "ship_data": ship_data
        }

        initial_response = model.generate_content(
            f"""Based on this ship data: {initial_context}
            Can you provide a complete answer to: {query}
            If you cannot provide a complete answer, respond with 'NEED_MORE_DATA'.
            Otherwise, provide your response."""
        )

        # If the model indicates it needs more data
        if "NEED_MORE_DATA" in initial_response.text:
            # Check which specific data we need
            if ship_manager.needs_additional_data(query, ship_data):
                urls = ship_manager.get_relevant_urls(ship_data)
                additional_data = web_scraper.scrape_multiple_urls(urls)
                initial_context["additional_data"] = additional_data

                # Generate final response with additional data
                final_response = model.generate_content(
                    f"""Based on this combined data: {initial_context}
                    Please provide a detailed response to: {query}
                    Format the response in a clear, structured way."""
                )
                response_text = final_response.text
            else:
                response_text = "I apologize, but I don't have enough information to provide a complete answer to your query."
        else:
            response_text = initial_response.text

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
