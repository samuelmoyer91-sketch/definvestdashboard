"""Web scraper for extracting full article content."""

import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path
import json
import time
from urllib.parse import urlparse, parse_qs, unquote

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, get_session

PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_config(config_path='config/feeds.json'):
    """Load scraping configuration."""
    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with open(path, 'r') as f:
        return json.load(f)


def extract_real_url_from_google_redirect(google_url):
    """Extract the actual article URL from a Google Alerts redirect URL.

    Google Alerts URLs look like:
    https://www.google.com/url?rct=j&sa=t&url=https://example.com/article&ct=ga&...

    This function extracts: https://example.com/article

    Note: Google News RSS URLs (news.google.com/articles/...) are handled
    separately in scrape_article() via HTTP redirect following.
    """
    try:
        parsed = urlparse(google_url)

        # Google Alerts redirect: /url?...url=...
        if 'google.com' in parsed.netloc and '/url' in parsed.path:
            params = parse_qs(parsed.query)
            if 'url' in params:
                real_url = params['url'][0]
                return unquote(real_url)

        return google_url

    except Exception as e:
        print(f"  ⚠ Warning: Could not parse URL: {e}")
        return google_url


# Full browser headers for sites that block basic scrapers (Google News, paywalls)
_BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def scrape_article(url, config):
    """Scrape full article content from URL."""
    # Extract real URL from Google Alerts redirect if needed
    original_url = url
    url = extract_real_url_from_google_redirect(url)

    if url != original_url:
        print(f"  → Extracted real URL from Google redirect")
        print(f"     {url[:80]}...")

    # Google News RSS URLs (news.google.com/articles/...) redirect to the real
    # article but block non-browser user agents. Use full browser headers so
    # allow_redirects=True lands us on the actual source page.
    is_google_news = 'news.google.com' in url
    headers = _BROWSER_HEADERS if is_google_news else {'User-Agent': config['scraping']['user_agent']}

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=config['scraping']['timeout_seconds'],
            allow_redirects=True
        )

        # Log where Google News redirected us
        if is_google_news and response.url != url:
            print(f"  → Google News redirected to: {response.url[:80]}...")

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"

        # Parse HTML
        soup = BeautifulSoup(response.content, 'lxml')

        # Check for JavaScript redirect (Google Alert redirect pages)
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if meta_refresh and meta_refresh.get('content'):
            # Extract the actual URL from meta refresh
            content = meta_refresh.get('content')
            if 'url=' in content:
                actual_url = content.split('url=')[1]
                print(f"  → Following meta refresh to: {actual_url[:60]}...")

                # Fetch the actual article
                response = requests.get(
                    actual_url,
                    headers=headers,
                    timeout=config['scraping']['timeout_seconds']
                )

                if response.status_code != 200:
                    return None, f"HTTP {response.status_code} (redirected)"

                soup = BeautifulSoup(response.content, 'lxml')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        if not text.strip():
            return None, "empty_content"

        return {
            'html': str(soup),
            'clean_text': text,
            'success': True,
            'error': None
        }, None

    except requests.Timeout:
        return None, "Timeout"
    except requests.RequestException as e:
        return None, f"Request error: {str(e)}"
    except Exception as e:
        return None, f"Parse error: {str(e)}"


def scrape_pending_items(limit=None, delay=1.0):
    """Scrape articles for items that haven't been scraped yet."""
    config = load_config()
    session = get_session()

    # Get items without article content
    query = session.query(RawItem).filter(
        ~RawItem.id.in_(
            session.query(ArticleContent.item_id)
        )
    ).filter(
        RawItem.status == 'new'
    )

    if limit:
        query = query.limit(limit)

    items = query.all()

    print("=" * 80)
    print(f"SCRAPING ARTICLES ({len(items)} items)")
    print("=" * 80)
    print()

    success_count = 0
    error_count = 0

    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] Scraping: {item.title[:60]}...")

        # Scrape the article
        result, error = scrape_article(item.url, config)

        if result:
            # Save to database
            article = ArticleContent(
                item_id=item.id,
                html=result['html'],
                clean_text=result['clean_text'],
                scrape_success=True,
                error_message=None
            )
            session.add(article)

            # Update raw item status
            item.status = 'scraped'

            success_count += 1
            print(f"  ✓ Success ({len(result['clean_text'])} chars)")

        else:
            # Save error to database
            article = ArticleContent(
                item_id=item.id,
                html=None,
                clean_text=None,
                scrape_success=False,
                error_message=error
            )
            session.add(article)

            # Update raw item status
            item.status = 'failed'

            error_count += 1
            print(f"  ✗ Failed: {error}")

        session.commit()

        # Delay between requests
        if i < len(items):
            time.sleep(delay)

    print()
    print("=" * 80)
    print(f"SUMMARY: {success_count} successful, {error_count} failed")
    print("=" * 80)

    session.close()

    return success_count, error_count


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    # Default: scrape all pending items (AI summary step has its own limit)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    scrape_pending_items(limit=limit)
