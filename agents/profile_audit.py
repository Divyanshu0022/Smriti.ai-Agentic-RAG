import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.rag import get_llm, get_full_text_from_uploads
from langchain_core.prompts import ChatPromptTemplate

# Configuration
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_ID", "1Shpc-PmI3WLlQwSL2qhvdT_heMSaF4Ar4SYH6XQjHGw")

def _get_sheets_service():
    """Authenticate with Google Sheets API using OAuth2 credentials from .env."""
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing OAuth credentials. Please run setup_gmail_token.py")
        
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    return build('sheets', 'v4', credentials=creds)

def _normalize_str(value):
    """Ensures any value (list, string, etc.) becomes a plain string for Sheets."""
    if isinstance(value, list):
        # Join list items as comma-separated short string
        return ", ".join(str(v) for v in value)
    return str(value) if value else "N/A"

def audit_profile_and_save(model_name="gemini-2.5-flash-lite"):
    """
    1. Extracts full text of uploaded resume.
    2. Uses LLM to produce a compact structured profile.
    3. Saves to Google Sheets.
    Returns structured data dict on success for the UI to consume.
    """
    full_text = get_full_text_from_uploads()
    if not full_text:
        return {"success": False, "message": "No document content found."}

    llm = get_llm(model_name)

    # Strict prompt: forces compact single-line strings, never lists
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a concise HR Profiler. Return ONLY a JSON object with these exact string keys. "
         "All values MUST be plain strings — no arrays, no lists. "
         "Keys: full_name (e.g. 'Divyanshu Roy'), "
         "experience (e.g. '1 yr' or '2 yrs'), "
         "top_skills (e.g. 'GenAI, Agentic AI, Python, MLOps' — max 5 words/phrases, comma-separated), "
         "linkedin (LinkedIn or GitHub URL or 'N/A'), "
         "summary (one sentence: candidate's name + 2-3 role fit areas, max 20 words), "
         "audit_date will be filled by the system. "
         "Do NOT include markdown, backticks, or explanations. Output raw JSON only."),
        ("human", "{text}")
    ])

    chain = prompt | llm
    response = chain.invoke({"text": full_text[:15000]})

    try:
        raw_content = response.content.strip()
        print(f"[ProfileAudit] LLM raw:\n{raw_content}")

        # Strip markdown fences if present
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()

        data = json.loads(raw_content)

        # Normalize every field to a plain string to prevent Sheets 400 errors
        full_name   = _normalize_str(data.get('full_name', 'N/A'))
        experience  = _normalize_str(data.get('experience', data.get('experience_years', 'N/A')))
        top_skills  = _normalize_str(data.get('top_skills', 'N/A'))
        linkedin    = _normalize_str(data.get('linkedin', data.get('social_links', 'N/A')))
        summary     = _normalize_str(data.get('summary', 'N/A'))
        audit_date  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [full_name, experience, top_skills, linkedin, summary, audit_date]

        # Validate — all cells must be plain strings
        for i, cell in enumerate(row):
            if not isinstance(cell, str):
                row[i] = str(cell)

        # Append to Google Sheet
        service = _get_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A2",
            valueInputOption="RAW",
            body={'values': [row]}
        ).execute()

        print(f"[ProfileAudit] Sheet append success: {result.get('updates')}")

        # Return clean dict used by UI
        return {
            "success": True,
            "message": "Profile audited and saved to Google Sheets!",
            "data": {
                "full_name":   full_name,
                "experience":  experience,
                "top_skills":  top_skills,
                "linkedin":    linkedin,
                "summary":     summary,
                "audit_date":  audit_date
            }
        }

    except Exception as e:
        print(f"❌ PROFILE AUDIT ERROR: {str(e)}")
        return {"success": False, "message": f"Audit failed: {str(e)}", "raw": response.content}


def get_profile_summary(model_name="gemini-2.5-flash-lite"):
    """Just returns the summary string without saving (for UI preview)."""
    full_text = get_full_text_from_uploads()
    if not full_text:
        return "No resume content found."

    llm = get_llm(model_name)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize this professional profile based on skills and achievements for a showcase project."),
        ("human", "{text}")
    ])
    chain = prompt | llm
    return chain.invoke({"text": full_text[:20000]}).content
