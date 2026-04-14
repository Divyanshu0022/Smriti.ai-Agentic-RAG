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

def audit_profile_and_save():
    """
    1. Extracts full text of uploaded resume.
    2. Uses LLM to summarize based on skills.
    3. Saves structured data to Google Sheets.
    """
    full_text = get_full_text_from_uploads()
    if not full_text:
        return {"success": False, "message": "No document content found."}

    llm = get_llm()
    
    # Prompt for structured extraction
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert HR Profiler. Extract the following details from the resume text provided in JSON format: "
                   "full_name, experience_years, top_skills (comma separated), social_links (LinkedIn/GitHub), summary. "
                   "If any field is missing, use 'N/A'."),
        ("human", "{text}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"text": full_text[:20000]}) # Limit text for speed
    
    try:
        # Extract JSON from LLM response (sometimes LLM wraps it in ```json)
        raw_content = response.content
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(raw_content)
        
        # Prepare row for Google Sheets
        # Headers: Full Name, Experience, Top Skills, LinkedIn/Social, LLM Summary, Audit Date
        row = [
            data.get('full_name', 'N/A'),
            data.get('experience_years', 'N/A'),
            data.get('top_skills', 'N/A'),
            data.get('social_links', 'N/A'),
            data.get('summary', 'N/A'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        # Append to Google Sheet
        service = _get_sheets_service()
        sheet = service.spreadsheets()
        
        body = {'values': [row]}
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A2",
            valueInputOption="RAW",
            body=body
        ).execute()
        
        return {
            "success": True, 
            "message": "Profile audited and saved to Google Sheets!",
            "data": data
        }
        
    except Exception as e:
        return {"success": False, "message": f"Audit failed: {str(e)}", "raw": response.content}

def get_profile_summary():
    """Just returns the summary without saving (for UI preview)."""
    full_text = get_full_text_from_uploads()
    if not full_text:
        return "No resume content found."
        
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize this professional profile based on skills and achievements for a showcase project."),
        ("human", "{text}")
    ])
    chain = prompt | llm
    return chain.invoke({"text": full_text[:20000]}).content
