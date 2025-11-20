### **PREREQUISITES**
- Autodesk account with access to ACC project
- Python 3.7+ installed

### **STEP 1: Create APS App & Set API Access**

1. Sign in at https://aps.autodesk.com/
2. Navigate to **My Apps** > **Create Application**
3. Fill in the form:
   - **App Name:** [Your app name]
   - **Application Type:** Tradtional Web App
   

**✓ Validation Check:** After clicking Create, you should see a page displaying your Client ID and Client Secret.

4. Then, scroll down to API Access, and select Autodesk Construction Cloud API, BIM360 API, Data Management API. (Can select all as well)

5. Add URL: **Callback URL:** `http://localhost:8080/callback`
---

### **STEP 2: Save Your Credentials**

1. On the app details page, locate:
   - **Client ID**
   - **Client Secret** (click "Show" to reveal)

2. Create a `.env` file in your project folder:
```bash
APS_CLIENT_ID=your_client_id_here
APS_CLIENT_SECRET=your_client_secret_here
CALLBACK_URL=http://localhost:8080/callback
```
---

### **STEP 3: Note Your APS Account Email**

The email you used to log into APS (visible in top-right corner) will need access to your ACC project.

**✓ Validation Check:** Copy down this email - you'll add it to ACC in the next step.

---

### **STEP 4: Grant ACC Project Access**

1. Go to https://acc.autodesk.com/ and open your project
2. Click **Project Admin** (left sidebar) > **Members**
3. Click **Add Members** button
4. Enter **the APS account email from Step 3**
5. Assign role: **Project Admin** (recommended for development)
6. Click **Add**

**Enable Assets Module:**
- Go to **Project Admin** > **Scroll to the right**
- Toggle **Build** to ON (if not already enabled)

**✓ Validation Check:** 
- The APS account email should appear in the Members list
- You may receive an email invitation (accept it)
- Log into ACC with that account at least once to activate permissions

---

### **STEP 5: Find Your Project & Account IDs**

These IDs are needed for API calls.

**To find Project ID:**
1. In ACC, open your project
2. Look at the URL: `https://acc.autodesk.com/projects/[PROJECT_ID]/...`
3. Copy the UUID between `/projects/` and the next `/`

**✓ Validation Check:** 
- IDs should be a long string (UUIDs) like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- Save these in your `.env` file:
```bash
ACC_PROJECT_ID=your_project_id
```

---

### **STEP 6: Set Up Authentication**

Install required packages:
```bash
pip install flask requests python-dotenv
```

Create `app.py`:
```python
from flask import Flask, redirect, request, session
import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random key

CLIENT_ID = os.getenv('APS_CLIENT_ID')
CLIENT_SECRET = os.getenv('APS_CLIENT_SECRET')
CALLBACK_URL = os.getenv('CALLBACK_URL')

AUTHORIZE_URL = 'https://developer.api.autodesk.com/authentication/v2/authorize'
TOKEN_URL = 'https://developer.api.autodesk.com/authentication/v2/token'

@app.route('/')
def home():
    return '<a href="/login">Login with Autodesk</a>'

@app.route('/login')
def login():
    scopes = [
        'data:read', 'data:write', 'data:create',
        'account:read', 'account:write', 'user:read'
    ]
    auth_url = (
        f"{AUTHORIZE_URL}?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={CALLBACK_URL}&"
        f"scope={' '.join(scopes)}"
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    
    if not code:
        return "Error: No authorization code received", 400
    
    # Exchange code for token
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CALLBACK_URL
    }
    
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_bytes}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        
        session['access_token'] = token_data['access_token']
        return redirect('/test-api')
        
    except requests.exceptions.RequestException as e:
        return f"Authentication failed: {str(e)}", 500

@app.route('/test-api')
def test_api():
    access_token = session.get('access_token')
    
    if not access_token:
        return redirect('/login')
    
    return f'''
        <h2>✓ Authentication Successful!</h2>
        <p>Your access token: {access_token[:20]}...</p>
        <p><a href="/list-assets">Test: List Assets</a></p>
    '''

if __name__ == '__main__':
    print("Starting server at http://localhost:8080")
    print("Visit http://localhost:8080 to begin")
    app.run(port=8080, debug=True)
```

**Run the app:**
```bash
python app.py
```

**✓ Validation Check:**
1. Visit `http://localhost:8080`
2. Click "Login with Autodesk"
3. You should be redirected to Autodesk login
4. After login, you should see "Authentication Successful!" page
5. **If you see an error:** Check that your `.env` values are correct

---

### **STEP 7: Test API Access to Assets**

Add this route to `app.py` (after the `test_api` route):

```python
@app.route('/list-assets')
def list_assets():
    access_token = session.get('access_token')
    
    if not access_token:
        return redirect('/login')
    
    project_id = os.getenv('ACC_PROJECT_ID')
    
    if not project_id:
        return "Error: ACC_PROJECT_ID not set in .env file", 500
    
    url = f'https://developer.api.autodesk.com/construction/assets/v1/projects/{project_id}/assets'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        assets = response.json()
        
        return f'''
            <h2>✓ API Access Successful!</h2>
            <p>Found {len(assets.get('results', []))} assets</p>
            <pre>{str(assets)[:500]}...</pre>
            <p><a href="/">Back to Home</a></p>
        '''
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "Error 401: Token expired or invalid. <a href='/login'>Login again</a>", 401
        elif e.response.status_code == 403:
            return "Error 403: Permission denied. Check that your APS account has access to this ACC project.", 403
        elif e.response.status_code == 404:
            return "Error 404: Project not found. Check your ACC_PROJECT_ID in .env", 404
        else:
            return f"API Error: {str(e)}", 500
    except Exception as e:
        return f"Unexpected error: {str(e)}", 500
```

**✓ Validation Check:**
1. Restart your Flask app
2. Visit `http://localhost:8080/test-api`
3. Click "Test: List Assets"
4. You should see a list of assets from your ACC project
5. **If you see an error:** See Troubleshooting section below

---

## **TROUBLESHOOTING**

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| **401 Unauthorized** | Token expired or invalid scopes | Re-authenticate via `/login` |
| **403 Forbidden** | APS account not added to ACC project | Verify Step 4 - check ACC Members list |
| **404 Not Found** | Wrong Project ID or Assets module disabled | Check Project ID (Step 5) and enable Assets in ACC |
| **Module not found (Python)** | Missing packages | Run `pip install flask requests python-dotenv` |
| **Connection refused** | Flask not running | Run `python app.py` in terminal |

---

## **NEXT STEPS**

Now that you can authenticate and read assets, you can:
- **Update Status** Use POST to `/hello`

See [APS Assets API Documentation](https://aps.autodesk.com/en/docs/acc/v1/reference/http/assets-v1-projects-projectId-assets-GET/) for full API details.

---