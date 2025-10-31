import telebot
from flask import Flask, request, redirect
import requests, threading
from auth import AutodeskAuth

# ----------------------------------------
# CONFIGURATION
# ----------------------------------------
BOT_TOKEN = "8168413961:AAHnwqzUZKpsfFGTNsTK_Fk5PzDKqaBUeI8"
CLIENT_ID = "GdxVaoVK9GponGjg5ekGhIkdxEIOipoAjROfwqA2RvXPM5k9"
CLIENT_SECRET = "QCtZ3oMGXfjUvVkJ80KCJDUMz99MtTFTgdHDVbVFMGWXa5m7GE6VzLMBKUVsuRtV"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "data:read data:write account:read"
PROJECT_ID = "b8df4eae-1fdb-454d-8928-a1d6b68b18af"

# ----------------------------------------
# AUTODESK AUTH SETUP
# ----------------------------------------
autodesk_auth = AutodeskAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scopes=SCOPES
)

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
    if autodesk_auth.is_authenticated():
        return """
        <h2>✅ Already Authenticated</h2>
        <p>Your Autodesk account is connected and ready to use!</p>
        <p>You can now use the Telegram bot to update issues.</p>
        """
    return """
    <h2>Autodesk OAuth Login</h2>
    <p>Click below to authenticate your Autodesk account:</p>
    <a href="/login">🔗 Login with Autodesk</a>
    """

@app.route("/login")
def login():
    """Redirect user to Autodesk login page"""
    return redirect(autodesk_auth.get_auth_url())

@app.route("/callback")
def callback():
    """Handles Autodesk OAuth callback"""
    code = request.args.get("code")
    if not code:
        return "❌ No authorization code received."
    
    access_token = autodesk_auth.exchange_code_for_tokens(code)
    
    if not access_token:
        return "❌ Token exchange failed."
    
    return """
    <h2>✅ Authentication Successful!</h2>
    <p>Your credentials have been saved securely.</p>
    <p>You can now close this window and use the Telegram bot.</p>
    <p><strong>You won't need to login again unless the refresh token expires (typically 14 days of inactivity).</strong></p>
    """

# ----------------------------------------
# HELPER: Update ACC Issue
# ----------------------------------------
def update_acc_issue(issue_guid, new_status):
    """Updates the issue status in Autodesk ACC"""
    access_token = autodesk_auth.get_access_token()
    
    if not access_token:
        return "⚠️ Please log in first via http://localhost:8080/login"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    update_url = f"https://developer.api.autodesk.com/construction/issues/v1/projects/{PROJECT_ID}/issues/{issue_guid}"
    payload = {"status": new_status}
    
    response = requests.patch(update_url, headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        return f"✅ Issue {issue_guid} updated to '{new_status}'"
    elif response.status_code == 401:
        # Token expired, try refreshing
        print("Token expired, attempting refresh...")
        access_token = autodesk_auth.refresh_access_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            response = requests.patch(update_url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                return f"✅ Issue {issue_guid} updated to '{new_status}'"
        return "❌ Authentication expired. Please login again at http://localhost:8080/login"
    else:
        return f"❌ Update failed: {response.text}"

# ----------------------------------------
# TELEGRAM BOT HANDLERS
# ----------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if autodesk_auth.is_authenticated():
        bot.reply_to(
            message,
            "👋 Hi! Your Autodesk account is already connected!\n\n"
            "Use this template to update issues:\n\n"
            "/update\n"
            "Issue ID: <your-issue-guid>\n"
            "New Status: <new-status>\n\n"
            "Example:\n"
            "/update\n"
            "Issue ID: d8e380de-2a93-42c1-8570-b9676ffdc440\n"
            "New Status: pending",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(
            message,
            "👋 Hi! I can help you update Autodesk ACC issues.\n\n"
            "Before using me, please login to Autodesk:\n"
            "👉 [Login Here](http://localhost:8080/login)\n\n"
            "Once logged in, use this template:\n\n"
            "/update\n"
            "Issue ID: <your-issue-guid>\n"
            "New Status: <new-status>",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['update'])
def handle_update(message):
    bot.reply_to(
        message,
        "✍️ Please send the details in this format:\n"
        "Issue ID: <your-issue-guid>\n"
        "New Status: <new-status>",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['status'])
def check_auth_status(message):
    """Check authentication status"""
    if autodesk_auth.is_authenticated():
        bot.reply_to(message, "✅ Autodesk account connected and ready!")
    else:
        bot.reply_to(
            message,
            "❌ Not authenticated. Please login:\n"
            "http://localhost:8080/login"
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
        
        bot.reply_to(message, f"🔄 Updating issue {issue_id} to {new_status}...", parse_mode="Markdown")
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
    print("🚀 Starting bot...")
    
    if autodesk_auth.is_authenticated():
        print("✅ Already authenticated with Autodesk!")
    else:
        print("⚠️ Not authenticated. Please visit http://localhost:8080/login")
    
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=run_telegram, daemon=True).start()
    
    # Keep main thread alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")