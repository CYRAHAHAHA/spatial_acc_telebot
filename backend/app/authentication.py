import requests
import json
import os
from datetime import datetime, timedelta

class AutodeskAuth:
    def __init__(self, client_id, client_secret, redirect_uri, scopes):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.token_file = "autodesk_tokens.json"
        
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        
        # Load existing tokens if available
        self.load_tokens()
    
    def save_tokens(self, access_token, refresh_token, expires_in):
        """Save tokens to file"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = (datetime.now() + timedelta(seconds=expires_in - 300)).isoformat()
        
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": self.expires_at
        }
        
        with open(self.token_file, "w") as f:
            json.dump(token_data, f)
        
        print("✅ Tokens saved to file")
    
    def load_tokens(self):
        """Load tokens from file"""
        if not os.path.exists(self.token_file):
            print("⚠️ No saved tokens found")
            return False
        
        try:
            with open(self.token_file, "r") as f:
                token_data = json.load(f)
            
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            self.expires_at = token_data.get("expires_at")
            
            print("✅ Tokens loaded from file")
            return True
        except Exception as e:
            print(f"❌ Error loading tokens: {e}")
            return False
    
    def is_token_valid(self):
        """Check if current access token is still valid"""
        if not self.access_token or not self.expires_at:
            return False
        
        expiry_time = datetime.fromisoformat(self.expires_at)
        return datetime.now() < expiry_time
    
    def get_access_token(self):
        """Get a valid access token (refresh if needed)"""
        if self.is_token_valid():
            print("✅ Using existing valid token")
            return self.access_token
        
        if self.refresh_token:
            print("🔄 Refreshing access token...")
            return self.refresh_access_token()
        
        print("⚠️ No valid tokens available. Please authenticate.")
        return None
    
    def exchange_code_for_tokens(self, code):
        """Exchange authorization code for tokens"""
        token_url = "https://developer.api.autodesk.com/authentication/v2/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            print(f"❌ Token exchange failed: {response.text}")
            return None
        
        token_data = response.json()
        self.save_tokens(
            token_data["access_token"],
            token_data["refresh_token"],
            token_data["expires_in"]
        )
        
        return self.access_token
    
    def refresh_access_token(self):
        """Use refresh token to get a new access token"""
        if not self.refresh_token:
            print("❌ No refresh token available")
            return None
        
        token_url = "https://developer.api.autodesk.com/authentication/v2/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            print(f"❌ Token refresh failed: {response.text}")
            # Clear invalid tokens
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            self.access_token = None
            self.refresh_token = None
            return None
        
        token_data = response.json()
        self.save_tokens(
            token_data["access_token"],
            token_data["refresh_token"],
            token_data["expires_in"]
        )
        
        print("✅ Token refreshed successfully")
        return self.access_token
    
    def get_auth_url(self):
        """Get the authorization URL for user login"""
        return (
            "https://developer.api.autodesk.com/authentication/v2/authorize"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={self.scopes}"
        )
    
    def is_authenticated(self):
        """Check if we have valid authentication"""
        return self.get_access_token() is not None