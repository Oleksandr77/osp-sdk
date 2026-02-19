import gmail_client
import drive_client
import os
from datetime import datetime

def generate_briefing():
    print("Starting Daily Briefing Generation...")
    
    # 1. Get Emails
    print("\n--- Fetching Unread Emails ---")
    emails = gmail_client.list_unread_emails()
    
    # 2. Get Drive Files
    print("\n--- Fetching Recent Drive Files ---")
    files = drive_client.list_recent_files()
    
    # 3. Create Report
    report_content = f"# 📅 Daily Briefing: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    report_content += "## 📧 Emails (Unread)\n"
    if emails:
        for email in emails:
            report_content += f"- **From:** {email['sender']}\n  **Subject:** {email['subject']}\n  **Snippet:** {email['snippet']}\n\n"
    else:
        report_content += "No unread emails.\n\n"
        
    report_content += "## 📂 Recent Drive Files\n"
    if files:
        for file in files:
            report_content += f"- {file['name']} (ID: {file['id']})\n"
    else:
        report_content += "No recent files.\n"
        
    # Save report
    output_dir = "../../../07_Knowledge_Base/daily_briefings"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(report_content)
        
    print(f"\n✅ Briefing generated at: {filepath}")
    return filepath

if __name__ == '__main__':
    generate_briefing()
