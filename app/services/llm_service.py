# app/services/llm_service.py
import google.generativeai as genai
from app.config import config
from app.services.llm_parsing_utils import parse_llm_json_response

genai.configure(api_key=config.GEMINI_API_KEY)

def analyze_and_decide_action(email_content: str):
    """
    Analyzes email content, decides on an action (reply or create ticket),
    and generates the necessary content for that action.
    """
    # Using a newer model for better instruction following
    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    prompt = f"""
    Analyze the following customer email and decide on the correct course of action.

    **Step 1: Categorize Priority**
    - If the email mentions 'urgent', 'payment failed', 'error', 'cannot access', 'broken', or 'not working', classify priority as 'High'.
    - Otherwise, classify priority as 'Normal'.

    **Step 2: Decide Action**
    - If priority is 'High', the action should be 'CREATE_TICKET'.
    - If priority is 'Normal' and it's a simple question (e.g., asking about features, pricing), the action should be 'SEND_REPLY'.
    - If priority is 'Normal' but the query is vague or seems to describe a problem, the action should be 'CREATE_TICKET'.

    **Step 3: Generate Content**
    - **summary:** Create a short, one-line summary of the user's issue. This will be the Jira ticket title.
    - **reply_body:** Craft a polite, professional reply.
        - If action is 'CREATE_TICKET', the reply should be an acknowledgement that a support ticket has been created and the team will look into it.
        - If action is 'SEND_REPLY', the reply should directly answer the user's question if possible, or provide helpful information.

    **Step 4: Format Output**
    Your response must be ONLY a valid JSON object with four keys: "priority", "action", "summary", and "reply_body".

    **Email to Analyze:**
    ---
    {email_content}
    ---
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

