import os
import base64
import json
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# load config
CLIENT_ID      = os.environ.get("GMAIL_CLIENT_ID", "")
CLIENT_SECRET  = os.environ.get("GMAIL_CLIENT_SECRET", "")
REFRESH_TOKEN  = os.environ.get("GMAIL_REFRESH_TOKEN", "")
SENDER_EMAIL   = os.environ.get("GMAIL_SENDER_EMAIL", "").strip()

def _get_access_token():
    """Exchange the refresh token for a fresh access token."""
    if not REFRESH_TOKEN:
        raise ValueError("GMAIL_REFRESH_TOKEN is missing. Please run setup_gmail_token.py.")

    payload = urllib.parse.urlencode({
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    }).encode()

    try:
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        if "access_token" not in data:
            raise RuntimeError(f"OAuth2 Error: {data.get('error_description', 'Unknown error')}")
        return data["access_token"]
    except Exception as e:
        raise RuntimeError(f"Failed to refresh Gmail token: {str(e)}")

def send_email(to, subject, content, is_otp=False):
    """
    Sends a premium HTML email. 
    If is_otp is True, uses the OTP specific text.
    """
    if not SENDER_EMAIL:
        return {"success": False, "message": "GMAIL_SENDER_EMAIL not configured."}

    try:
        access_token = _get_access_token()
        
        msg = MIMEMultipart("alternative")
        msg["From"] = f"Smriti.ai <{SENDER_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject

        # Premium HTML Body
        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0B0B0F; color: #EEF2F5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #15161C; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #66FCF1 0%, #45A29E 100%); padding: 30px; text-align: center;">
                    <h1 style="margin: 0; color: #0B0B0F; font-size: 24px;">Smriti.ai Notification</h1>
                </div>
                <div style="padding: 40px;">
                    <p style="font-size: 16px; line-height: 1.6; color: #8B949E;">
                        {content}
                    </p>
                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center; color: #45A29E; font-size: 12px;">
                        This is an automated message from your Smriti.ai Agentic Platform.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(content, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip('=')
        
        send_req = urllib.request.Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=json.dumps({"raw": raw_message}).encode(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        
        with urllib.request.urlopen(send_req) as resp:
            result = json.loads(resp.read())
            
        return {"success": True, "message": f"Email sent to {to}", "id": result.get("id")}

    except Exception as e:
        print(f"DEBUG: Email failure - {str(e)}")
        return {"success": False, "message": str(e)}
