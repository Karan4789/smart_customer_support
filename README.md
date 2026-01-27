# Smart Customer Support Automation

An **AI-powered, multi-agent application** that automates customer support workflows across **multiple channels**. This system uses dedicated **Scout Agents** to monitor Gmail, Discord, and Telegram, a **Triage Agent** to analyze and decide on actions, and an **Orchestrator** to execute tasks like creating Jira tickets or sending intelligent replies.

Built with **Python**, **FastAPI**, **LangChain**, and **Groq LLMs**, this project demonstrates a robust, scalable producer-consumer architecture for handling real-world support automation across diverse communication platforms.

---

## 🏛️ Architecture

The system uses a queue-based, multi-agent workflow to decouple tasks and ensure reliable processing across multiple communication channels.

![Smart Customer Support Architecture](assets/architecture.png)

---

## 🚀 Features

-   **Multi-Channel Support**: Monitors and responds to customer inquiries from **Gmail**, **Discord**, and **Telegram** simultaneously.
-   **Agentic Workflow**: Utilizes specialized LangChain agents for distinct tasks: dedicated `Scout Agents` for each channel, a `Triage Agent` for decision-making, and a `Reply Agent` for generating responses.
-   **Intelligent Triage**: The Triage Agent analyzes message content to determine priority (`High`, `Normal`, `Low`) and the best action (`CREATE_TICKET` or `SEND_REPLY`).
-   **Tool-Based Execution**: The orchestrator uses specific, reliable tools to interact with external services like Jira, Gmail, Discord, and Telegram, ensuring predictable outcomes.
-   **AI-Generated Responses**: A dedicated Reply Agent generates context-aware, empathetic, and platform-appropriate responses tailored to each communication channel.
-   **Persistent Queue System**: Built on SQLite database queue (`customer_request.db`), allowing reliable message processing with status tracking (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`).
-   **Robust Logging**: Logs all agent actions, orchestrator decisions, and errors to both the console and a persistent `app.log` file.
-   **Async Architecture**: Fully asynchronous design with FastAPI lifespan events managing background tasks for optimal performance.

---

## ✨ Showcase: Jira Integration

The system identifies high-priority emails and automatically creates detailed tickets on the Jira board.
![Jira Ticket Creation](assets/jira_op1.png)

Each ticket contains the full context needed for a human agent to take over, including the original customer message.
![Jira Ticket Details](assets/jira_op2.png)

For tickets requiring a human touch, the system can even suggest a reply, which can be included in the ticket description.
![Jira Ticket Details](assets/jira_op3.png)

---

## 🛠 Tech Stack

-   **Backend**: Python, FastAPI, Uvicorn
-   **Agent Framework**: LangChain, LangChain Agents
-   **AI / LLM**: 
    -   **Groq** (Llama 3.3 70B) via `langchain-groq` for Triage and Reply Agents, Scout Agents
-   **Database**: SQLite3 for persistent queue management
-   **Integrations & Tools**:
    -   **Gmail**: `langchain-google-community[gmail]` for email monitoring and sending
    -   **Jira**: `jira` and `atlassian-python-api` libraries for ticket creation
    -   **Discord**: `discord.py` for real-time channel monitoring
    -   **Telegram**: `python-telegram-bot` for polling and message handling

---

## 📦 Setup and Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd smart-customer-support
```

### 2. Create and Activate a Virtual Environment

```bash
# Create a virtual environment
uv venv

# Activate on Windows
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Configure Credentials

-   **Google API**:
    -   Follow the Google Cloud documentation to create an **OAuth 2.0 Client ID**.
    -   Download the `credentials.json` file and place it in the project's root directory.
    -   Enable the Gmail API in your Google Cloud Console.

-   **Groq API**:
    -   Sign up at [Groq](https://groq.com/) and obtain an API key.

-   **Jira Setup**:
    -   Create a Jira Cloud account and project.
    -   Generate an API token from your Atlassian account settings.

-   **Discord Setup** (Optional):
    -   Create a Discord bot in the [Discord Developer Portal](https://discord.com/developers/applications).
    -   Add the bot to your server and copy the bot token and channel ID.

-   **Telegram Setup** (Optional):
    -   Create a bot using [@BotFather](https://t.me/botfather) on Telegram.
    -   Copy the bot token provided.

-   **Environment Variables**:
    -   Create a `.env` file in the root directory.
    -   Copy and paste the following, filling in your own secret values.

    ```env
    # .env

    # Google
    GMAIL_CREDENTIALS_PATH=credentials.json
    GEMINI_API_KEY="your_gemini_api_key"

    # Groq (Required for Triage and Reply Agents)
    GROQ_API_KEY="your_groq_api_key"

    # Jira
    JIRA_API_TOKEN="your_jira_api_token"
    JIRA_EMAIL="your-jira-login-email@example.com"
    JIRA_DOMAIN="your-domain.atlassian.net"
    JIRA_PROJECT_KEY="YOUR_PROJECT_KEY"

    # Discord (Optional)
    DISCORD_BOT_TOKEN="your_discord_bot_token"
    DISCORD_SUPPORT_CHANNEL_ID="your_discord_channel_id"

    # Telegram (Optional)
    TELEGRAM_BOT_TOKEN="your_telegram_bot_token"

    # Logging (Optional)
    LOG_LEVEL=INFO
    LOG_FILE=app.log
    ```

-   **Gmail Token**: A `token.json` file will be automatically created in the root directory the first time you run the application, after you complete the browser-based authentication flow.

---

## ▶️ Running the Application

Start the FastAPI server with Uvicorn. The `--reload` flag will automatically restart the server when you make code changes.

```bash
uvicorn app.main:app --reload
```

Once running, the application will:
1.  Start the FastAPI server on `http://127.0.0.1:8000`.
2.  Initialize the SQLite database (`customer_request.db`).
3.  Launch background tasks for:
    -   Gmail Scout Agent (monitors inbox)
    -   Discord Scout Agent (monitors channel)
    -   Telegram Scout Agent (polls for updates)
    -   Orchestrator (processes the ticket queue)
4.  Begin logging all activities to the console and `app.log`.

Visit `http://127.0.0.1:8000` to verify the service is running.

