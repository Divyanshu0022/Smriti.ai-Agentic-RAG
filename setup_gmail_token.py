"""
One-time Gmail OAuth2 Token Setup
Run this ONCE to authorize Gmail access and store your refresh token in .env

Usage:
    python setup_gmail_token.py

This will:
1. Open your browser to Google's consent screen
2. Ask you to sign in and approve Gmail access
3. Automatically save your refresh token to .env
"""
import os
import json
import urllib.request
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID     = os.environ.get("GMAIL_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8765"
SCOPE         = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/spreadsheets"
ENV_FILE      = ".env"

# ─── Step 1: Build the authorization URL ─────────────────────
auth_url = (
    "https://accounts.google.com/o/oauth2/v2/auth?"
    + urllib.parse.urlencode({
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPE,
        "access_type":   "offline",
        "prompt":        "consent",   # force refresh_token even if already authorized
    })
)

# ─── Step 2: Local server to capture the redirect code ────────
auth_code = None

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html><body style='font-family:sans-serif;text-align:center;padding:60px;background:#0B0B0F;color:#66FCF1'>
                <h2>&#10003; Authorization successful!</h2>
                <p style='color:#EEF2F5'>You can close this tab and return to your terminal.</p>
            </body></html>
        """)

    def log_message(self, *args):
        pass  # suppress server logs

def main():
    print("\n🔐 Gmail OAuth2 Setup\n" + "─" * 40)
    print("Opening browser for Google consent...")
    webbrowser.open(auth_url)

    print("Waiting for authorization (browser redirect)...")
    server = HTTPServer(("localhost", 8765), _Handler)
    server.handle_request()  # handles exactly one request then stops

    if not auth_code:
        print("❌ No authorization code received. Please try again.")
        return

    print("✅ Code received. Exchanging for tokens...")

    # ─── Step 3: Exchange code for tokens ─────────────────────
    payload = urllib.parse.urlencode({
        "code":          auth_code,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read())

    if "refresh_token" not in tokens:
        print(f"❌ No refresh_token in response: {tokens}")
        print("Tip: Go to https://myaccount.google.com/permissions and revoke access, then try again.")
        return

    refresh_token = tokens["refresh_token"]

    # ─── Step 4: Save to .env ─────────────────────────────────
    set_key(ENV_FILE, "GMAIL_REFRESH_TOKEN", refresh_token)
    print(f"✅ Refresh token saved to .env")

    # ─── Step 5: Ask for sender email ─────────────────────────
    sender = input("\nEnter your Gmail address (the one you just authorized): ").strip()
    if sender:
        set_key(ENV_FILE, "GMAIL_SENDER_EMAIL", sender)
        print(f"✅ Sender email saved: {sender}")

    print("\n🎉 Setup complete! Email sending is now active.")
    print("   You can now use 'Email Report' buttons in the AI Knowledge Worker app.\n")

if __name__ == "__main__":
    main()
