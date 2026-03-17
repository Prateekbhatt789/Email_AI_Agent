from utils.gmail_client import fetch_email, fetch_unread_emails, get_gmail_service

service = get_gmail_service()
# emails= fetch_unread_emails(service)

emails= fetch_email(service,max_results=2)


for email in emails:
    # print(email)
    print(f"Email ID: {email['id']}")
    print(f"Subject: {email['subject']}")
    print(f"From: {email['sender']}")
    print(f"Date: {email['date']}")
    # print(f"Body:\n{email['body']}")
    print("-" * 40)