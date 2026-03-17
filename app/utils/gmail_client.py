import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.utils.settings import settings

GMAIL_CREDENTIALS_FILE = "credential.json"
GMAIL_TOKEN_FILE = "token.json"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_service():
    """Authenticate and return a Gmail API service object."""
    creds = None

    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)



def fetch_email(service,max_results=3):
    """Fetch last 10 emails from inbox. Returns list of parsed email dicts."""
    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        full_msg = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()
        emails.append(_parse_email(full_msg))

    return emails

FIRST_RUN_CAP = settings.FIRST_MONITOR_CAP

 
def fetch_emails_since_last_processed(service, batch_size: int = 20) -> list:
    """
    Fetch all inbox emails (read or unread) since the last AI-Processed email.
 
    Two modes depending on whether AI-Processed label exists in Gmail:
 
    First run (label not yet applied to any email):
        No boundary to stop at — cap at FIRST_RUN_CAP (50) to avoid
        walking the entire inbox history on a fresh setup.
 
    Subsequent runs (label exists):
        Page through inbox newest-first and stop the moment we hit
        the first AI-Processed email. Fetches both read and unread.
 
    Timeline example (newest → oldest):
        email E  — new, read          → fetched
        email D  — new, unread        → fetched
        email C  — new, read          → fetched
        email B  — AI-Processed       → STOP
        email A  — AI-Processed       → never reached
 
    Args:
        service:    Authenticated Gmail API service
        batch_size: IDs per page for the list call (max 500).
 
    Returns:
        List of parsed email dicts, newest-first.
    """
    ai_label_id = ensure_label(service)
    is_first_run = not _has_any_processed_email(service, ai_label_id)
 
    if is_first_run:
        print(f"First run detected — capping at {FIRST_RUN_CAP} emails.")
 
    emails = []
    page_token = None
    stop = False
 
    while not stop:
        kwargs = {
            "userId":     "me",
            "labelIds":   ["INBOX"],
            "maxResults": batch_size,
        }
        if page_token:
            kwargs["pageToken"] = page_token
 
        response = service.users().messages().list(**kwargs).execute()
        messages = response.get("messages", [])
 
        if not messages:
            break
 
        for msg in messages:
            # First-run cap — stop once we hit the limit
            if is_first_run and len(emails) >= FIRST_RUN_CAP:
                stop = True
                break
 
            full_msg = service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
 
            msg_label_ids = full_msg.get("labelIds", [])
            if ai_label_id in msg_label_ids:
                stop = True   # hit the boundary — stop fetching
                break
 
            emails.append(_parse_email(full_msg))
 
        if stop:
            break
 
        page_token = response.get("nextPageToken")
        if not page_token:
            break
 
    return emails
 
 
def _has_any_processed_email(service, ai_label_id: str) -> bool:
    """
    Check if any email in the inbox already has the AI-Processed label.
    One lightweight list call — no full message fetch needed.
    Returns True if at least one processed email exists (not first run).
    """
    response = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", ai_label_id],
        maxResults=1,
    ).execute()
    return bool(response.get("messages"))
 
def _parse_email(message):
    """Extract useful fields from a raw Gmail message."""
    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
 
    body = ""
    payload = message["payload"]
 
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
 
    return {
        "id": message["id"],
        "thread_id": message["threadId"],
        "subject": headers.get("Subject", "(no subject)"),
        "sender": headers.get("From", ""),
        "recipient": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "body": body.strip(),
        "snippet": message.get("snippet", ""),
    }
 
 
def save_draft(service, to: str, subject: str, body: str, thread_id: str = None):
    """Save a reply as a Gmail draft."""
    message = MIMEMultipart()
    message["To"] = to
    message["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    message.attach(MIMEText(body, "plain"))
 
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id
 
    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return draft["id"]
 
 
def mark_as_read(service, message_id: str):
    """Mark an email as read after processing."""
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()
 
# ── Label helpers ─────────────────────────────────────────────────────────────
 
AI_PROCESSED_LABEL = "AI-Processed"
 
 
def ensure_label(service) -> str:
    """
    Get the label ID for AI_PROCESSED_LABEL.
    Creates the label in Gmail if it doesn't exist yet.
    Returns the label ID string.
 
    Safe to call on every run — Gmail deduplicates by name.
    """
    existing = service.users().labels().list(userId="me").execute()
    for label in existing.get("labels", []):
        if label["name"] == AI_PROCESSED_LABEL:
            return label["id"]
 
    # Label doesn't exist yet — create it
    created = service.users().labels().create(
        userId="me",
        body={
            "name": AI_PROCESSED_LABEL,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
    ).execute()
    return created["id"]
 
 
def apply_label(service, message_id: str, label_id: str) -> None:
    """
    Apply a label to a single Gmail message.
    Kept for single-message use. For bulk use apply_label_bulk().
    """
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()
 
 
def apply_label_bulk(service, message_ids: list, label_id: str) -> None:
    """
    Apply a label to multiple messages in ONE API call using batchModify.
    Replaces the per-email loop — 50 emails = 1 request instead of 50.
 
    Gmail batchModify limit: 1000 message IDs per call.
    We chunk automatically so any size list is safe.
    """
    CHUNK_SIZE = 1000
    for i in range(0, len(message_ids), CHUNK_SIZE):
        chunk = message_ids[i : i + CHUNK_SIZE]
        service.users().messages().batchModify(
            userId="me",
            body={
                "ids":         chunk,
                "addLabelIds": [label_id],
            },
        ).execute()