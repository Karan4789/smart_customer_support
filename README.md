# Smart Customer Support Automation

An **AI-powered application** that monitors a Gmail inbox, analyzes incoming emails using **Google’s Gemini Pro**, and automates responses or creates Jira tickets based on the email’s content and priority.

This system is built with **Python**, **FastAPI**, and integrates seamlessly with **Google** and **Atlassian APIs** to create a fully automated support workflow.

---

## 🚀 Features

- **Automated Email Monitoring**: Continuously checks a specified Gmail inbox for new, unread emails.  
- **Intelligent Analysis**: Uses Google Gemini Pro to analyze email content, determine priority (High/Normal), and decide on the next best action (`SEND_REPLY` or `CREATE_TICKET`).  
- **Conditional Actions**:  
  - **Direct Replies**: For low-priority or simple questions, automatically sends a helpful, AI-generated reply.  
  - **Jira Escalation**: For high-priority or complex issues, automatically creates a detailed ticket in Jira.  
- **Context-Rich Tickets**: Populates Jira tickets with the customer’s original message, AI-determined priority, and a suggested reply for human agents.  
- **Customer Acknowledgement**: Sends an automated email with the Jira ticket ID after successful creation.  
- **Robust Logging**: Logs all major actions, successes, and errors to console and `support_app.log` for monitoring and debugging.  

---

## ⚙️ How It Works

The system identifies high-priority emails and automatically creates detailed tickets on the Jira board.  
![Jira Ticket Creation](assets/jira_op1.png)

Each ticket contains the full context, including the original customer message and an AI-suggested reply, ready for a human agent.  
![Jira Ticket Details](assets/jira_op2.png)

---

1. The system continuously monitors a Gmail inbox.  
2. Each new email is analyzed by **Gemini 2.5 flash**:  
   - If it’s **low-priority / simple** → sends an AI-generated reply.  
   - If it’s **high-priority / complex** → creates a Jira ticket and sends an acknowledgement email.  
3. Created Jira tickets contain:  
   - Original customer message  
   - AI-suggested reply  
   - Priority level  

---

## 🛠 Tech Stack

- **Backend**: Python , FastAPI
- **AI/LLM**: Google Gemini 2.5 Flash 
- **Email**: Gmail API  
- **Project Management**: Jira API  
- **Libraries**:  
  - `google-api-python-client`
  - `google-auth-httplib2`
  - `google-auth-oauthlib`
  - `requests`
  - `fastapi`
  - `uvicorn[standard]`  
  - `jira`  
  - `python-dotenv`  

---

## 📦 Setup and Installation

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd <your-repository-name>
```

### 2. Create and Activate a Virtual Environment
```bash
# Create venv
python -m venv venv  

# Activate (MacOS/Linux)
source venv/bin/activate  

# Activate (Windows)
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Credentials

- **Google API**:  
  - Follow Google Cloud steps to create an **OAuth 2.0 Client ID**.  
  - Download `credentials.json` and place it in the project root.  

- **Environment Variables**:  
  - Create a `.env` file in the root directory with:  
    ```text
    GEMINI_API_KEY="your_gemini_api_key"

    # Jira Credentials
    JIRA_DOMAIN="your-domain.atlassian.net"
    JIRA_EMAIL="your-jira-login-email@example.com"
    JIRA_API_TOKEN="your_jira_api_token"
    JIRA_PROJECT_KEY="YOUR_PROJECT_KEY"
    ```
  - A `token.json` file will be auto-created on first run for Gmail authentication.  

---

## ▶️ Running the Application

Run with Uvicorn:  
```bash
uvicorn app.main:app --reload
```

- The app will start.  
- Background task begins monitoring your Gmail inbox.  
- Actions (reply or ticket creation) are logged in console and `app.log`.  

---

## 📖 Example Flow

- **Email:** “How do I reset my password?”  
  → AI categorizes as *simple query* → Auto reply sent.  

- **Email:** “Payment deducted but account not upgraded.”  
  → AI categorizes as *High Priority Billing* → Jira ticket created + Acknowledgement email sent.  
