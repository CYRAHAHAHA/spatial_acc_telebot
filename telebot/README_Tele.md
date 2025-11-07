# Telegram BIM Update Bot (Quick Setup)

This bot reads `[UPDATE]` messages sent in your Telegram group and saves them into a JSON file.
It also triggers the main Flask app (`root/`) to update Autodesk ACC asset status via the `/update_status` endpoint.

---

## 🧰 1. Requirements

- Python 3.9 or newer
- The bot token (from @BotFather)
- Access to the Telegram group where the bot is added

---

## ⚙️ 2. Installation Steps

### Step 1 — Open Terminal or PowerShell
Go to the folder containing `bot_logger.py` and `requirements.txt`.

### Step 2 — Create a virtual environment
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate

### Step 3 — Install dependencies
Run pip install -r requirements.txt in terminal

### Step 4 — Run the bot
**Windows:**
```bash
python bot_logger.py

### Step 5 — Test the bot in telegram
In your group chat (where the bot is added), send:

[UPDATE]
Location: Building A, Level 3
Zone / Grid / Area: Grid 5-7, East Wing
Task: Internal Partition Walls
Status: Completed
Remarks: Ready for inspection


You should see the bot reply: Update logged.

### Step 6 - Check log_message.jsonl to see if it is updated
#site_updates.jsonl: flask-api endpoint

---

## 🔗 Integration with the main Flask app

To push updates to Autodesk automatically, keep the primary app running (`python root/main.py`) and set the following environment variables before launching `flask_api.py`:

```
SITE_UPDATES_TOKEN=<shared-secret-for-telegram-flask>
ROOT_APP_BASE=http://localhost:8000  # or wherever root/app is exposed
```

`flask_api.py` writes every Telegram update to `telebot/site_updates.json` and then POSTs `{ asset_guid, status_value }` to `<ROOT_APP_BASE>/update_status`. The root app handles Autodesk authentication and status mapping, so you don’t need duplicate logic inside the Telegram service.
