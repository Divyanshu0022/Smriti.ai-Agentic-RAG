import os
import json
from datetime import datetime
from dotenv import load_dotenv
from utils.profile_audit import _get_sheets_service, SPREADSHEET_ID

# Load environment variables
load_dotenv()

def debug_connection():
    print("🚀 Starting Google Sheets Debug...")
    print(f"📍 Spreadsheet ID: {SPREADSHEET_ID}")
    
    try:
        # 1. Test Authentication
        print("🔐 Authenticating with Google APIs...")
        service = _get_sheets_service()
        sheet = service.spreadsheets()
        print("✅ Authentication Successful!")

        # 2. Test Get Sheet Metadata (Verifies access)
        print("🔍 Verifying Sheet access and 'Sheet1' existence...")
        metadata = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_names = [s.get('properties', {}).get('title') for s in metadata.get('sheets', [])]
        print(f"📋 Found Tabs: {', '.join(sheet_names)}")
        
        if "Sheet1" not in sheet_names:
            print("❌ ERROR: Your spreadsheet does not have a tab named 'Sheet1'. Please create one or update the code.")
            return

        # 3. Attempt Append
        print("📝 Attempting to append a DEBUG row...")
        test_row = [
            "DEBUG TEST", 
            "99", 
            "Debugging, Python", 
            "https://github.com", 
            "Test summary generated at " + datetime.now().strftime("%H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        body = {'values': [test_row]}
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A2",
            valueInputOption="RAW",
            body=body
        ).execute()
        
        print("✅ APPEND SUCCESSFUL!")
        print(f"📊 Result: {json.dumps(result, indent=2)}")
        print(f"🔗 View your sheet here: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

    except Exception as e:
        print("\n💥 CONNECTION FAILED 💥")
        print(f"Error Message: {str(e)}")
        print("\nPossible Causes:")
        print("- Your GOOGLE_SHEETS_ID in .env is incorrect.")
        print("- The Google Account for your Refresh Token doesn't have EDITOR access to the sheet.")
        print("- The Google Sheets API is not enabled in your Google Cloud Console.")

if __name__ == "__main__":
    debug_connection()
