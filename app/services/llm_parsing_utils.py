# app/services/llm_parsing_utils.py
import json
import re

def parse_llm_json_response(text: str):
    """
    Cleans and parses a JSON string from an LLM response.
    Handles markdown code fences and other common formatting issues.
    """
    if not text:
        return None

    # Use regex to find the JSON block, even with surrounding text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        print("[ERROR] No JSON object found in the LLM response.")
        return None
    
    json_str = match.group(0)
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from LLM response: {e}")
        print(f"--- Invalid JSON Data Received ---\n{json_str}\n---------------------------------")
        return None
