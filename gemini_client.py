import google.generativeai as genai
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def initialize_gemini():
    """Initialize the Gemini client with API key from environment."""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not found")
            return None

        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        logger.error(f"Error initializing Gemini client: {e}")
        return None

def query_ship_data(query: str) -> str:
    """Query the Gemini model about Star Citizen ships."""
    try:
        client = initialize_gemini()
        if not client:
            return "Error: Unable to initialize Gemini client"

        # Configure the model for consistent, factual responses
        model = client.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            contents=query,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Lower temperature for more factual responses
                max_output_tokens=500,
            ),
        )

        return response.text
    except Exception as e:
        logger.error(f"Error querying Gemini: {e}")
        return f"Error processing query: {str(e)}"