"""Telegram bot handler for Defense Capital Tracker.

Handles:
- URL submissions from forwarded messages
- /start and /status commands
- Webhook updates from Telegram

The bot extracts URLs from messages and queues them for processing.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database import RawItem, get_session


# URL extraction regex
URL_PATTERN = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*',
    re.IGNORECASE
)


def extract_urls(text: str) -> list:
    """Extract URLs from message text.

    Args:
        text: Message text to search

    Returns:
        List of URL strings found
    """
    if not text:
        return []
    return URL_PATTERN.findall(text)


def is_authorized_user(user_id: int) -> bool:
    """Check if user is authorized to submit articles.

    Args:
        user_id: Telegram user ID

    Returns:
        True if authorized (or no restriction set)
    """
    allowed_users = os.environ.get('TELEGRAM_ALLOWED_USERS', '')
    if not allowed_users:
        # No restriction - allow all
        return True

    allowed_ids = [int(uid.strip()) for uid in allowed_users.split(',') if uid.strip()]
    return user_id in allowed_ids


def add_url_to_queue(url: str, title: Optional[str] = None, source: str = 'telegram') -> tuple:
    """Add URL to the processing queue.

    Args:
        url: Article URL to add
        title: Optional title for the article
        source: Source identifier

    Returns:
        Tuple of (success: bool, message: str, item_id: Optional[int])
    """
    session = get_session()

    try:
        # Check if URL already exists
        existing = session.query(RawItem).filter_by(url=url).first()
        if existing:
            return False, f"URL already in database (ID: {existing.id})", existing.id

        # Create new item
        item = RawItem(
            url=url,
            title=title or f"Telegram submission: {url[:50]}...",
            rss_summary="Submitted via Telegram bot",
            feed_source=source,
            date_found=datetime.utcnow(),
            status='new'
        )
        session.add(item)
        session.commit()

        return True, f"Added to queue (ID: {item.id})", item.id

    except Exception as e:
        session.rollback()
        return False, f"Database error: {e}", None

    finally:
        session.close()


def get_queue_status() -> Dict[str, int]:
    """Get current processing queue status.

    Returns:
        Dict with counts for each status
    """
    session = get_session()

    try:
        from sqlalchemy import func
        from src.database import ArticleContent, AIExtraction, MasterItem, RejectedItem

        total = session.query(RawItem).count()
        new = session.query(RawItem).filter_by(status='new').count()
        scraped = session.query(ArticleContent).filter_by(scrape_success=True).count()
        with_ai = session.query(AIExtraction).filter_by(summary_complete=True).count()
        approved = session.query(MasterItem).count()
        rejected = session.query(RejectedItem).count()

        return {
            'total': total,
            'new': new,
            'scraped': scraped,
            'with_ai_summary': with_ai,
            'approved': approved,
            'rejected': rejected,
            'pending_triage': scraped - approved - rejected
        }

    finally:
        session.close()


def handle_telegram_update(update: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming Telegram webhook update.

    Args:
        update: Telegram update object (dict)

    Returns:
        Response dict with 'text' to send back
    """
    message = update.get('message', {})
    text = message.get('text', '')
    chat_id = message.get('chat', {}).get('id')
    user_id = message.get('from', {}).get('id')
    username = message.get('from', {}).get('username', 'unknown')

    if not chat_id:
        return {'ok': True}

    # Check authorization
    if not is_authorized_user(user_id):
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': "⛔ Unauthorized. Contact the admin to get access."
        }

    # Handle commands
    if text.startswith('/start'):
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': (
                "🛡️ *Defense Capital Tracker Bot*\n\n"
                "Forward me articles or send URLs to add them to the triage queue.\n\n"
                "Commands:\n"
                "/status - View queue stats\n"
                "/help - Show this message"
            ),
            'parse_mode': 'Markdown'
        }

    if text.startswith('/status'):
        status = get_queue_status()
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': (
                "📊 *Queue Status*\n\n"
                f"📥 New items: {status['new']}\n"
                f"📄 Scraped: {status['scraped']}\n"
                f"🤖 With AI summary: {status['with_ai_summary']}\n"
                f"⏳ Pending triage: {status['pending_triage']}\n"
                f"✅ Approved: {status['approved']}\n"
                f"❌ Rejected: {status['rejected']}\n"
                f"📚 Total: {status['total']}"
            ),
            'parse_mode': 'Markdown'
        }

    if text.startswith('/help'):
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': (
                "🛡️ *Defense Capital Tracker Bot*\n\n"
                "Forward me articles or send URLs to add them to the triage queue.\n\n"
                "Commands:\n"
                "/status - View queue stats\n"
                "/help - Show this message"
            ),
            'parse_mode': 'Markdown'
        }

    # Extract URLs from message
    urls = extract_urls(text)

    # Also check for URLs in forwarded message entities
    entities = message.get('entities', [])
    for entity in entities:
        if entity.get('type') == 'url':
            offset = entity.get('offset', 0)
            length = entity.get('length', 0)
            url = text[offset:offset + length]
            if url and url not in urls:
                urls.append(url)

    # Check caption for forwarded messages with media
    caption = message.get('caption', '')
    if caption:
        urls.extend(extract_urls(caption))

    if not urls:
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': "No URLs found in message. Forward an article or send a URL directly."
        }

    # Process each URL
    results = []
    for url in urls[:5]:  # Limit to 5 URLs per message
        success, msg, item_id = add_url_to_queue(url, source=f'telegram:{username}')
        emoji = "✅" if success else "⚠️"
        results.append(f"{emoji} {msg}")

    return {
        'method': 'sendMessage',
        'chat_id': chat_id,
        'text': '\n'.join(results)
    }


async def send_telegram_message(chat_id: int, text: str, parse_mode: str = None) -> bool:
    """Send a message via Telegram Bot API.

    Args:
        chat_id: Telegram chat ID
        text: Message text
        parse_mode: Optional 'Markdown' or 'HTML'

    Returns:
        True if successful
    """
    import httpx

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False


def register_webhook(webhook_url: str) -> bool:
    """Register webhook URL with Telegram.

    Args:
        webhook_url: Full URL for webhook endpoint

    Returns:
        True if successful
    """
    import requests

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{token}/setWebhook"
    response = requests.post(url, json={'url': webhook_url})

    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            print(f"Webhook registered: {webhook_url}")
            return True
        else:
            print(f"Webhook registration failed: {result.get('description')}")
            return False
    else:
        print(f"Webhook registration failed: HTTP {response.status_code}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Telegram bot utilities")
    parser.add_argument("--register-webhook", type=str, help="Register webhook URL")
    parser.add_argument("--status", action="store_true", help="Show queue status")

    args = parser.parse_args()

    if args.register_webhook:
        register_webhook(args.register_webhook)
    elif args.status:
        status = get_queue_status()
        print("Queue Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    else:
        parser.print_help()
