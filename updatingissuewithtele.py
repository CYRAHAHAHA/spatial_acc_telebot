import telebot
from flask import Flask, request, redirect
import requests, threading, webbrowser, json, time

# ----------------------------------------
# CONFIGURATION
# ----------------------------------------
BOT_TOKEN = "8168413961:AAHnwqzUZKpsfFGTNsTK_Fk5PzDKqaBUeI8"
CLIENT_ID = "-"
CLIENT_SECRET = "-"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "data:read data:write account:read"
PROJECT_ID = "b8df4eae-1fdb-454d-8928-a1d6b68b18af"

# ----------------------------------------
# TELEGRAM BOT SETUP
# ----------------------------------------
bot = telebot.TeleBot(BOT_TOKEN)

# ----------------------------------------
# FLASK APP
# ----------------------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return """
    <h2>Autodesk OAuth Login</h2>
    <p>Click below to authenticate your Autodesk account:</p>
    <a href="/login">🔗 Login with Autodesk</a>
    """

@app.route("/login")
def login():
    """Redirect user to Autodesk login page"""
    auth_url = (
        "https://developer.api.autodesk.com/authentication/v2/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    """Handles Autodesk OAuth callback"""
    code = request.args.get("code")
    if not code:
        return "❌ No authorization code received."

    token_url = "https://developer.api.autodesk.com/authentication/v2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    token_response = requests.post(token_url, data=data)
    if token_response.status_code != 200:
        return f"❌ Token exchange failed: {token_response.text}"

    access_token = token_response.json()["access_token"]
    print("✅ Autodesk access token obtained!")
    global AUTODESK_ACCESS_TOKEN
    AUTODESK_ACCESS_TOKEN = access_token
    return "✅ Auth successful! You can now use the Telegram bot to update issues."

AUTODESK_ACCESS_TOKEN = None

# ----------------------------------------
# HELPER: Update ACC Issue
# ----------------------------------------
def update_acc_issue(issue_guid, new_status):
    """Updates the issue status in Autodesk ACC"""

    global AUTODESK_ACCESS_TOKEN
    if not AUTODESK_ACCESS_TOKEN:
        return "⚠️ Please log in first via http://localhost:8080/login"

    headers = {
        "Authorization": f"Bearer {AUTODESK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    update_url = f"https://developer.api.autodesk.com/construction/issues/v1/projects/{PROJECT_ID}/issues/{issue_guid}"
    payload = {"status": new_status}

    response = requests.patch(update_url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        return f"✅ Issue {issue_guid} updated to '{new_status}'"
    else:
        return f"❌ Update failed: {response.text}"

# ----------------------------------------
# TELEGRAM BOT HANDLERS
# ----------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "👋 Hi! I can help you update Autodesk ACC issues.\n\n"
        "Before using me, please login to Autodesk:\n"
        "👉 [Login Here](http://localhost:8080/login)\n\n"
        "Once logged in, use this template:\n\n"
        "`/update`\n"
        "`Issue ID: <your-issue-guid>`\n"
        "`New Status: <new-status>`\n\n"
        "Example:\n"
        "`/update`\n"
        "`Issue ID: d8e380de-2a93-42c1-8570-b9676ffdc440`\n"
        "`New Status: pending`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['update'])
def handle_update(message):
    bot.reply_to(
        message,
        "✍️ Please send the details in this format:\n"
        "`Issue ID: <your-issue-guid>`\n"
        "`New Status: <new-status>`",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: "issue id:" in msg.text.lower() and "new status:" in msg.text.lower())
def process_issue_update(message):
    try:
        lines = message.text.strip().split("\n")
        issue_id = None
        new_status = None

        for line in lines:
            line_lower = line.lower().strip()
            if line_lower.startswith("issue id:"):
                issue_id = line.split(":", 1)[1].strip()
            elif line_lower.startswith("new status:"):
                new_status = line.split(":", 1)[1].strip()

        if not issue_id or not new_status:
            bot.reply_to(message, "⚠️ Could not parse your message. Please follow the format carefully.")
            return

        bot.reply_to(message, f"🔄 Updating issue `{issue_id}` to `{new_status}`...", parse_mode="Markdown")
        result = update_acc_issue(issue_id, new_status)
        bot.reply_to(message, result)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ----------------------------------------
# RUN FLASK + TELEGRAM BOT
# ----------------------------------------
def run_flask():
    app.run(port=8080, debug=False)

def run_telegram():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_telegram).start()