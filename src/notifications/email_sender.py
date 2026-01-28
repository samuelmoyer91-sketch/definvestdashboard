"""Email sender for Defense Capital Tracker digest.

Uses Gmail SMTP with App Password for sending HTML email digests
with HMAC-signed approve/reject action links.
"""

import os
import hmac
import hashlib
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DigestItem:
    """Item to include in digest email."""
    item_id: int
    title: str
    company: Optional[str]
    deal_amount: Optional[str]
    deal_type: Optional[str]
    sectors: Optional[str]
    summary: Optional[str]
    url: str
    relevance_score: Optional[float]


# Token expiry: 24 hours
TOKEN_EXPIRY_SECONDS = 24 * 60 * 60


def generate_action_token(item_id: int, action: str) -> str:
    """Generate HMAC-signed token for email action links.

    Args:
        item_id: Database ID of the item
        action: Either 'approve' or 'reject'

    Returns:
        Signed token string: {item_id}:{action}:{timestamp}:{signature}
    """
    secret = os.environ.get('EMAIL_ACTION_SECRET', 'dev-secret-change-me')
    timestamp = int(time.time())

    message = f"{item_id}:{action}:{timestamp}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16]  # Truncate for shorter URLs

    return f"{item_id}:{action}:{timestamp}:{signature}"


def verify_action_token(token: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """Verify HMAC-signed action token.

    Args:
        token: Token string from email link

    Returns:
        Tuple of (is_valid, item_id, action, error_message)
    """
    secret = os.environ.get('EMAIL_ACTION_SECRET', 'dev-secret-change-me')

    try:
        parts = token.split(':')
        if len(parts) != 4:
            return False, None, None, "Invalid token format"

        item_id, action, timestamp_str, provided_sig = parts

        item_id = int(item_id)
        timestamp = int(timestamp_str)

        # Check expiry
        if time.time() - timestamp > TOKEN_EXPIRY_SECONDS:
            return False, item_id, action, "Token expired"

        # Verify signature
        message = f"{item_id}:{action}:{timestamp}"
        expected_sig = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]

        if not hmac.compare_digest(provided_sig, expected_sig):
            return False, None, None, "Invalid signature"

        if action not in ('approve', 'reject'):
            return False, None, None, "Invalid action"

        return True, item_id, action, None

    except (ValueError, TypeError) as e:
        return False, None, None, f"Token parse error: {e}"


def build_email_html(items: List[DigestItem], base_url: str) -> str:
    """Build HTML email content with deal cards and action links.

    Args:
        items: List of DigestItem objects to include
        base_url: Base URL for action links (e.g., https://app.railway.app)

    Returns:
        HTML string for email body
    """
    cards_html = ""

    for item in items:
        approve_token = generate_action_token(item.item_id, 'approve')
        reject_token = generate_action_token(item.item_id, 'reject')

        approve_url = f"{base_url}/api/action?token={approve_token}"
        reject_url = f"{base_url}/api/action?token={reject_token}"
        detail_url = f"{base_url}/item/{item.item_id}"

        # Format sectors for display
        sectors_display = ""
        if item.sectors:
            sectors_list = item.sectors.split(',')
            sectors_display = " ".join([f'<span style="background:#e3f2fd;padding:2px 6px;border-radius:3px;font-size:11px;margin-right:4px;">{s.strip()}</span>' for s in sectors_list[:3]])

        # Relevance indicator
        relevance_indicator = ""
        if item.relevance_score:
            color = "#4caf50" if item.relevance_score >= 0.5 else "#ff9800" if item.relevance_score >= 0.3 else "#f44336"
            relevance_indicator = f'<span style="color:{color};font-size:11px;">●</span>'

        cards_html += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:16px;background:#fafafa;">
            <div style="margin-bottom:8px;">
                {relevance_indicator}
                <strong style="font-size:14px;">{item.company or 'Unknown Company'}</strong>
                {f'<span style="color:#1976d2;margin-left:8px;">{item.deal_amount}</span>' if item.deal_amount else ''}
            </div>
            <div style="font-size:13px;color:#333;margin-bottom:8px;">
                {item.title[:100]}{'...' if len(item.title) > 100 else ''}
            </div>
            <div style="margin-bottom:12px;">
                {sectors_display}
            </div>
            {f'<div style="font-size:12px;color:#666;margin-bottom:12px;">{item.summary[:200]}...</div>' if item.summary and len(item.summary) > 0 else ''}
            <div style="display:flex;gap:8px;">
                <a href="{approve_url}" style="background:#4caf50;color:white;padding:8px 16px;text-decoration:none;border-radius:4px;font-size:13px;">✓ Approve</a>
                <a href="{reject_url}" style="background:#f44336;color:white;padding:8px 16px;text-decoration:none;border-radius:4px;font-size:13px;">✗ Reject</a>
                <a href="{detail_url}" style="background:#2196f3;color:white;padding:8px 16px;text-decoration:none;border-radius:4px;font-size:13px;">View Details</a>
            </div>
        </div>
        """

    triage_url = f"{base_url}/"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;">
        <div style="background:white;padding:24px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <h1 style="color:#1a237e;font-size:20px;margin-bottom:8px;">Defense Capital Tracker</h1>
            <p style="color:#666;font-size:14px;margin-bottom:24px;">
                {len(items)} new item{'s' if len(items) != 1 else ''} ready for triage
            </p>

            {cards_html}

            <div style="margin-top:24px;padding-top:16px;border-top:1px solid #e0e0e0;text-align:center;">
                <a href="{triage_url}" style="color:#1976d2;text-decoration:none;font-size:13px;">
                    Open full triage interface →
                </a>
            </div>

            <div style="margin-top:16px;font-size:11px;color:#999;text-align:center;">
                Action links expire in 24 hours.
            </div>
        </div>
    </body>
    </html>
    """

    return html


def send_digest_email(items: List[DigestItem], base_url: Optional[str] = None) -> bool:
    """Send digest email with pending items.

    Requires environment variables:
        GMAIL_ADDRESS: Gmail address to send from
        GMAIL_APP_PASSWORD: Gmail app password (16 chars)
        DIGEST_RECIPIENT: Email address to send to
        APP_BASE_URL: Base URL for action links (optional, overridden by base_url param)

    Args:
        items: List of DigestItem objects to include
        base_url: Override for APP_BASE_URL env var

    Returns:
        True if email sent successfully, False otherwise
    """
    if not items:
        print("No items to send in digest")
        return True

    gmail_address = os.environ.get('GMAIL_ADDRESS')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
    recipient = os.environ.get('DIGEST_RECIPIENT')
    base_url = base_url or os.environ.get('APP_BASE_URL', 'http://localhost:8000')

    if not all([gmail_address, gmail_password, recipient]):
        print("Missing email configuration. Required: GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DIGEST_RECIPIENT")
        return False

    # Build email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Defense Tracker: {len(items)} new item{'s' if len(items) != 1 else ''} for review"
    msg['From'] = gmail_address
    msg['To'] = recipient

    # Plain text fallback
    plain_text = f"Defense Capital Tracker: {len(items)} new items ready for triage.\n\n"
    for item in items:
        plain_text += f"- {item.company or 'Unknown'}: {item.title[:80]}\n"
    plain_text += f"\nOpen triage interface: {base_url}/"

    # HTML version
    html_content = build_email_html(items, base_url)

    msg.attach(MIMEText(plain_text, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, recipient, msg.as_string())

        print(f"Digest email sent to {recipient} with {len(items)} items")
        return True

    except smtplib.SMTPAuthenticationError:
        print("Gmail authentication failed. Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD")
        return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


if __name__ == "__main__":
    # Test with sample data
    test_items = [
        DigestItem(
            item_id=1,
            title="Anduril raises $1.5B Series F",
            company="Anduril Industries",
            deal_amount="$1.5B",
            deal_type="Series F",
            sectors="AI/ML,Autonomous Systems",
            summary="Defense tech company Anduril has raised a massive Series F round to expand its AI-powered defense systems.",
            url="https://example.com/anduril",
            relevance_score=0.85
        ),
        DigestItem(
            item_id=2,
            title="Shield AI acquires drone startup",
            company="Shield AI",
            deal_amount="$200M",
            deal_type="Acquisition",
            sectors="Autonomous Systems,Aerospace",
            summary="Shield AI continues expansion with acquisition of autonomous drone technology company.",
            url="https://example.com/shieldai",
            relevance_score=0.72
        ),
    ]

    print("Testing email HTML generation...")
    html = build_email_html(test_items, "http://localhost:8000")
    print(f"Generated {len(html)} chars of HTML")

    print("\nTesting token generation/verification...")
    token = generate_action_token(123, 'approve')
    print(f"Token: {token}")

    valid, item_id, action, error = verify_action_token(token)
    print(f"Verified: valid={valid}, item_id={item_id}, action={action}")
