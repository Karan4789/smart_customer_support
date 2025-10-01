# app/services/llm_service.py
import google.generativeai as genai
from app.config import config
from app.services.llm_parsing_utils import parse_llm_json_response # Import the new function

genai.configure(api_key=config.GEMINI_API_KEY)

def analyze_and_craft_reply(email_content: str):
    """
    Analyzes email content using Gemini and uses a robust parser for the response.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Analyze the following customer email. Assess its urgency and generate a polite, professional reply.
    - If the email mentions 'urgent', 'payment failed', 'error', or 'cannot access', classify priority as 'High'.
    - Otherwise, classify priority as 'Normal'.
    
    Based on the priority, craft a response. 
    - For 'High' priority, the response should be empathetic and promise a quick follow-up.
    - For 'Normal' priority, the response should be helpful and set a realistic expectation for a response time (e.g., within 24 hours).
    
    Your response must be ONLY a valid JSON object with two keys: "priority" and "reply_body".

    Email: "{email_content}"
    """
    
    try:
        response = model.generate_content(prompt)
        print(f"[DEBUG] Raw LLM response text: {response.text}")
        
        # Use the robust parsing function
        parsed_json = parse_llm_json_response(response.text)
        
        if parsed_json is None:
            print("[ERROR] Failed to parse the LLM response as JSON.")
            return None
            
        return parsed_json

    except Exception as e:
        print(f"An error occurred in LLM service: {e}")
        return None
