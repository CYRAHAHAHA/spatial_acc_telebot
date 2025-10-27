from flask import Flask, request
from app.config import config

app = Flask(__name__)
# import routes so Flask registers them
from app import routes

@app.route("/")
def home():
    msg = request.args.get("msg", "")
    msg_html = f'<div class="msg">{msg}</div>' if msg else ""

    # List all keys for the current user (without values)
    keys = [attr for attr in dir(config) if not attr.startswith("__") and not callable(getattr(config, attr))]
    keys_list_html = "<ul>" + "".join(f"<li>{k}</li>" for k in keys) + "</ul>"

    return f'''
        <h1>ACC API Integration</h1>
        {msg_html}
        <h3>Current user: {config.user}</h3>
        <p>Env variable keys for this user:</p>
        {keys_list_html}
        <form action="/fetch_assets_config">
            <button type="submit">Fetch Assets Config</button>
        </form>
        <p>To switch user, go to /switch_user/&lt;user&gt; where &lt;user&gt; is 'YR' or 'DEV'.</p>
    '''
