# Spatial ACC Telebot

An AI-powered Telegram bot that integrates with **Autodesk Construction Cloud (ACC)** to enable real-time BIM asset status updates from the field via natural language messages.

---

## 🎯 Overview

This system bridges the gap between on-site construction workers and BIM data management by:

1. **Telegram Bot** — Receives natural language status updates from site workers
2. **NLP Engine** — Matches free-text messages to specific BIM/IFC elements using AI
3. **Flask Backend** — Manages Autodesk OAuth and pushes status updates to ACC Assets API

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Telegram Bot   │───▶│   NLP Matcher   │───▶│   ACC Assets    │
│  (bot_logger)   │    │   (OpenAI GPT)  │    │   (APS API)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📁 Project Structure

```
spatial_acc_telebot/
├── root/                   # Flask backend application
│   ├── app/
│   │   ├── __init__.py     # Flask app initialization & OAuth
│   │   ├── routes.py       # API endpoints
│   │   ├── authentication.py
│   │   ├── functions/      # ACC API integrations
│   │   └── src/            # Web dashboard (SPA)
│   └── main.py             # Flask entry point
│
├── telebot/                # Telegram bot
│   ├── bot_logger.py       # Main bot logic
│   ├── run_matcher.py      # NLP integration wrapper
│   └── activity_log.json   # Logged updates
│
├── NLP/                    # AI-powered element matching
│   ├── matcher.py          # OpenAI GPT integration
│   └── io_wrapper.py       # Interface for bot
│
├── data/                   # Runtime data & configs
│   ├── model.json          # IFC model metadata
│   ├── status_sets.csv     # Available statuses
│   └── assets_total.csv    # Asset inventory
│
├── tests/                  # NLP accuracy evaluation
│   ├── test_data.json      # Human-annotated test cases
│   └── nlp_accuracy_evaluation.ipynb
│
├── railway.json            # Railway deployment config
├── nixpacks.toml           # Build configuration
├── Procfile                # Process definition
└── requirements.txt        # Python dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)
- Autodesk APS credentials (Client ID, Secret)
- OpenAI API Key

### 1. Clone & Setup Environment

```bash
git clone https://github.com/CYRAHAHAHA/spatial_acc_telebot.git
cd spatial_acc_telebot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file:

```env
# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token

# Autodesk APS
APS_CLIENT_ID=your_client_id
APS_CLIENT_SECRET=your_client_secret
APS_CALLBACK_URL=http://localhost:8080/callback

# OpenAI
OPENAI_API_KEY=your_openai_key

# ACC Project
PROJECT_ID=your_acc_project_id
```

### 3. Run Locally

```bash
# Start both services
bash start_all.sh

# Or run individually:
cd telebot && python bot_logger.py &
cd root && python main.py
```

---

## 💬 Usage

Send a message to your Telegram group with the bot:

```
[UPDATE]
Door Single Flush Inside Level 1
Installed
```

The bot will:

1. Parse the message using NLP
2. Match it to the correct BIM element(s)
3. Update the asset status in ACC
4. Reply with confirmation

---

## 🔌 API Endpoints

| Endpoint               | Method | Description                 |
| ---------------------- | ------ | --------------------------- |
| `/authorize`           | GET    | Start Autodesk OAuth flow   |
| `/callback`            | GET    | OAuth callback handler      |
| `/update_status`       | POST   | Update asset status in ACC  |
| `/fetch_assets_config` | GET    | Sync ACC configuration      |
| `/api/status`          | GET    | Token & environment info    |

---

## 🧪 Testing

Run NLP accuracy evaluation:

```bash
cd tests
jupyter notebook nlp_accuracy_evaluation.ipynb
```

---

## 📚 Additional Documentation

- [Telegram Bot Setup](telebot/README_Tele.md)
- [APS & ACC Integration](README_APSandACC.md)

---

## 📄 License

MIT License
