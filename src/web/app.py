"""FastAPI web application for triage and dashboard."""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from fastapi import FastAPI, Request, Form, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import sys
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, MasterItem, RejectedItem, Investor, DealInvestor, ApiUsageLog, get_session, sync_turso
from src.utils.investor_parser import parse_investors, slugify

_TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours

def verify_action_token(token: str):
    """Verify HMAC-signed approve/reject token from email action links."""
    secret = os.environ.get('EMAIL_ACTION_SECRET', 'dev-secret-change-me')
    try:
        parts = token.split(':')
        if len(parts) != 4:
            return False, None, None, "Invalid token format"
        item_id_str, action, timestamp_str, provided_sig = parts
        item_id = int(item_id_str)
        timestamp = int(timestamp_str)
        if time.time() - timestamp > _TOKEN_EXPIRY:
            return False, item_id, action, "Token expired"
        message = f"{item_id}:{action}:{timestamp}"
        expected_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(provided_sig, expected_sig):
            return False, None, None, "Invalid signature"
        if action not in ('approve', 'reject'):
            return False, None, None, "Invalid action"
        return True, item_id, action, None
    except (ValueError, TypeError) as e:
        return False, None, None, f"Token parse error: {e}"

app = FastAPI(title="Defense Capital Tracker")


# =============================================================================
# HTTP Basic Auth Middleware
# =============================================================================

_UNPROTECTED_PATHS = {'/health', '/api/telegram-webhook'}

class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _UNPROTECTED_PATHS:
            return await call_next(request)

        username = os.environ.get('TRIAGE_USERNAME', '')
        password = os.environ.get('TRIAGE_PASSWORD', '')

        # Skip auth if credentials not configured (local dev)
        if not username or not password:
            return await call_next(request)

        auth = request.headers.get('Authorization', '')
        unauthorized = Response(
            'Unauthorized',
            status_code=401,
            headers={'WWW-Authenticate': 'Basic realm="Defense Capital Triage"'},
        )

        if not auth.startswith('Basic '):
            return unauthorized

        try:
            decoded = base64.b64decode(auth[6:]).decode('utf-8')
            req_user, req_pass = decoded.split(':', 1)
        except Exception:
            return unauthorized

        user_ok = secrets.compare_digest(req_user, username)
        pass_ok = secrets.compare_digest(req_pass, password)
        if not (user_ok and pass_ok):
            return unauthorized

        return await call_next(request)

app.add_middleware(BasicAuthMiddleware)


# =============================================================================
# Database Dependency
# =============================================================================

def _safe_url(url: str):
    """Accept only http/https URLs; return None for anything else (e.g. javascript:)."""
    url = url.strip()
    if url.startswith(('http://', 'https://')):
        return url
    return None


def get_db():
    """FastAPI dependency: yield a DB session and close it when done."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# Startup Migration — ensures schema is current on deploy
# =============================================================================

@app.on_event("startup")
async def sync_replica_on_startup():
    """Sync the Turso replica on startup so reads are fresh."""
    try:
        get_session().close()  # Initializes engine + first sync
        sync_turso()
        logger.info("Startup Turso sync complete")
    except Exception as e:
        logger.warning(f"Startup sync failed (will retry on first request): {e}")


@app.on_event("startup")
async def register_telegram_webhook_on_startup():
    """Re-register Telegram webhook on every deploy so URL changes self-heal."""
    domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not domain or not token:
        logger.info("Skipping Telegram webhook registration (env vars not set)")
        return
    try:
        from src.notifications.telegram_bot import register_webhook
        webhook_url = f"https://{domain}/api/telegram-webhook"
        success = register_webhook(webhook_url)
        if success:
            logger.info(f"Telegram webhook registered: {webhook_url}")
        else:
            logger.warning("Telegram webhook registration failed")
    except Exception as e:
        logger.warning(f"Telegram webhook registration error: {e}")


@app.on_event("startup")
async def run_startup_migrations():
    """Check for and apply any missing schema changes.

    SQLAlchemy's create_all() handles new tables (investors, deal_investors)
    but won't ALTER existing tables. This adds missing columns.
    """
    from sqlalchemy import text as sa_text
    from src.database.models import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        # Check if title column exists on master_list
        try:
            conn.execute(sa_text("SELECT title FROM master_list LIMIT 1"))
        except Exception:
            logger.info("Adding title column to master_list...")
            conn.execute(sa_text("ALTER TABLE master_list ADD COLUMN title TEXT"))
            conn.commit()
            logger.info("title column added successfully")

        # Check if title column exists on ai_extractions
        try:
            conn.execute(sa_text("SELECT title FROM ai_extractions LIMIT 1"))
        except Exception:
            logger.info("Adding title column to ai_extractions...")
            conn.execute(sa_text("ALTER TABLE ai_extractions ADD COLUMN title TEXT"))
            conn.commit()
            logger.info("ai_extractions.title column added successfully")

        # Check if source_url column exists on master_list
        try:
            conn.execute(sa_text("SELECT source_url FROM master_list LIMIT 1"))
        except Exception:
            logger.info("Adding source_url column to master_list...")
            conn.execute(sa_text("ALTER TABLE master_list ADD COLUMN source_url TEXT"))
            conn.commit()
            logger.info("source_url column added successfully")

        # Check if additional_source_url column exists on master_list
        try:
            conn.execute(sa_text("SELECT additional_source_url FROM master_list LIMIT 1"))
        except Exception:
            logger.info("Adding additional_source_url column to master_list...")
            conn.execute(sa_text("ALTER TABLE master_list ADD COLUMN additional_source_url TEXT"))
            conn.commit()
            logger.info("additional_source_url column added successfully")

        # Check if geolocation columns exist on master_list
        for col, typedef in [("latitude", "REAL"), ("longitude", "REAL"), ("congressional_district", "TEXT")]:
            try:
                conn.execute(sa_text(f"SELECT {col} FROM master_list LIMIT 1"))
            except Exception:
                logger.info(f"Adding {col} column to master_list...")
                conn.execute(sa_text(f"ALTER TABLE master_list ADD COLUMN {col} {typedef}"))
                conn.commit()
                logger.info(f"master_list.{col} column added successfully")

        # Check if deal_status column exists on ai_extractions
        try:
            conn.execute(sa_text("SELECT deal_status FROM ai_extractions LIMIT 1"))
        except Exception:
            logger.info("Adding deal_status column to ai_extractions...")
            conn.execute(sa_text("ALTER TABLE ai_extractions ADD COLUMN deal_status TEXT"))
            conn.commit()
            logger.info("ai_extractions.deal_status column added successfully")

        # Add performance indexes (CREATE INDEX IF NOT EXISTS is idempotent)
        indexes = [
            ("idx_raw_items_status", "raw_items", "status"),
            ("idx_raw_items_published_date", "raw_items", "published_date"),
            ("idx_deal_investors_investor_id", "deal_investors", "investor_id"),
            ("idx_deal_investors_master_item_id", "deal_investors", "master_item_id"),
        ]
        for idx_name, table, col in indexes:
            conn.execute(sa_text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})"))
        conn.commit()
        logger.info("Performance indexes verified")


# =============================================================================
# Global Exception Handler
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a styled error page instead of raw 500."""
    logger.error(f"Unhandled error on {request.url.path}: {type(exc).__name__}: {exc}")
    return HTMLResponse(
        content=f"""
        <html>
        <head><title>Server Error</title></head>
        <body style="font-family:sans-serif;text-align:center;padding:50px;">
            <h1 style="color:#f44336;">Server Error</h1>
            <p><strong>{type(exc).__name__}</strong>: {exc}</p>
            <p style="color:#666;font-size:0.9em;">Check Railway logs for full traceback.</p>
            <p><a href="/">Return to home</a></p>
        </body>
        </html>
        """,
        status_code=500
    )


# =============================================================================
# Health & API Endpoints for Cloud Deployment
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway/container orchestration."""
    return {"status": "healthy"}


@app.get("/api/diagnostics")
async def diagnostics():
    """Diagnostics endpoint to check env vars, DB connection, and record counts."""
    required_vars = ["TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN", "ANTHROPIC_API_KEY"]
    env_status = {var: bool(os.environ.get(var)) for var in required_vars}

    db_ok = False
    db_error = None
    counts = {}
    try:
        diag_session = get_session()
        try:
            counts = {
                "raw_items": diag_session.query(RawItem).count(),
                "articles": diag_session.query(ArticleContent).count(),
                "ai_extractions": diag_session.query(AIExtraction).count(),
                "master_list": diag_session.query(MasterItem).count(),
                "rejected": diag_session.query(RejectedItem).count(),
            }
            db_ok = True
        finally:
            diag_session.close()
    except Exception as e:
        db_error = f"{type(e).__name__}: {e}"
        logger.error(f"Diagnostics DB check failed: {db_error}")

    overall = "healthy" if db_ok and all(env_status.values()) else "unhealthy"

    return {
        "overall": overall,
        "env_vars": env_status,
        "database": {"connected": db_ok, "error": db_error},
        "counts": counts,
    }


@app.get("/api/action")
async def email_action(request: Request, token: str = Query(...), session=Depends(get_db)):
    """Handle approve/reject actions from email links.

    Token format: {item_id}:{action}:{timestamp}:{signature}
    """
    valid, item_id, action, error = verify_action_token(token)

    if not valid:
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Action Failed</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#f44336;">Action Failed</h1>
                <p>{error or 'Invalid token'}</p>
                <p><a href="/">Return to triage interface</a></p>
            </body>
            </html>
            """,
            status_code=400
        )

    # Check item exists
    item = session.query(RawItem).filter_by(id=item_id).first()
    if not item:
        return HTMLResponse(
            content="""
            <html>
            <head><title>Item Not Found</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#ff9800;">Item Not Found</h1>
                <p>This item may have already been processed.</p>
                <p><a href="/">Return to triage interface</a></p>
            </body>
            </html>
            """,
            status_code=404
        )

    if action == 'approve':
        # Check if already approved
        existing = session.query(MasterItem).filter_by(item_id=item_id).first()
        if not existing:
            # Get AI extraction for default values
            extraction = session.query(AIExtraction).filter_by(item_id=item_id).first()

            master = MasterItem(
                item_id=item_id,
                company=extraction.company if extraction else None,
                investors=extraction.investors if extraction else None,
                investment_amount=extraction.deal_amount if extraction else None,
                transaction_type=extraction.transaction_type if extraction else None,
                capital_sources=extraction.capital_sources if extraction else None,
                sectors=extraction.sectors if extraction else None,
                summary=extraction.strategic_significance if extraction else None,
                human_notes="Approved via email",
                published=False
            )
            session.add(master)
            session.commit()
            sync_turso()

        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Approved</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#4caf50;">Approved</h1>
                <p><strong>{item.title[:80]}...</strong></p>
                <p>Added to master list for publication.</p>
                <p><a href="/item/{item_id}">View details</a> | <a href="/">Return to triage</a></p>
            </body>
            </html>
            """
        )

    elif action == 'reject':
        # Check if already rejected
        existing = session.query(RejectedItem).filter_by(item_id=item_id).first()
        if not existing:
            rejected = RejectedItem(
                item_id=item_id,
                rejection_reason="Rejected via email"
            )
            session.add(rejected)
            session.commit()
            sync_turso()

        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Rejected</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#f44336;">Rejected</h1>
                <p><strong>{item.title[:80]}...</strong></p>
                <p>Removed from triage queue.</p>
                <p><a href="/">Return to triage</a></p>
            </body>
            </html>
            """
        )


@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram bot updates."""
    from src.notifications.telegram_bot import handle_telegram_update

    try:
        update = await request.json()
        response = handle_telegram_update(update)

        # If response has a method, it's a Telegram API response format
        if response.get('method'):
            return JSONResponse(content=response)
        else:
            return JSONResponse(content={'ok': True})

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return JSONResponse(content={'ok': True})

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session=Depends(get_db)):
    """Home page showing triage queue."""
    from sqlalchemy.orm import joinedload

    # Get items that:
    # 1. Have been successfully scraped
    # 2. Are not yet in master list
    # 3. Have not been rejected
    # 4. Were not screened out by AI title filter
    # 5. Are not Contract/Award transaction type (routine contracts/SBIR auto-filtered)
    items = session.query(RawItem).join(
        ArticleContent, RawItem.id == ArticleContent.item_id
    ).outerjoin(
        AIExtraction, RawItem.id == AIExtraction.item_id
    ).options(
        joinedload(RawItem.article),
        joinedload(RawItem.extraction)
    ).filter(
        ArticleContent.scrape_success == True,
        RawItem.status != 'ai_screened_out',
        ~RawItem.id.in_(
            session.query(MasterItem.item_id)
        ),
        ~RawItem.id.in_(
            session.query(RejectedItem.item_id)
        ),
        # Exclude routine Contract/Award items (SBIR, grants, procurement)
        ~((AIExtraction.transaction_type != None) & (AIExtraction.transaction_type == 'Contract/Award')),
        # Exclude speculative deals (rumors, plans, "considering", "seeks", etc.)
        ~((AIExtraction.deal_status != None) & (AIExtraction.deal_status == 'speculative'))
    ).order_by(
        RawItem.published_date.desc()
    ).limit(200).all()

    # Map relationships to the attribute names templates expect
    for item in items:
        item.article_content = item.article
        item.ai_extraction = item.extraction

    total_items = len(items)
    master_count = session.query(MasterItem).count()

    return templates.TemplateResponse("triage.html", {
        "request": request,
        "items": items,
        "total_items": total_items,
        "master_count": master_count
    })


@app.get("/item/{item_id}", response_class=HTMLResponse)
async def view_item(request: Request, item_id: int, session=Depends(get_db)):
    """View full item details."""
    item = session.query(RawItem).filter_by(id=item_id).first()
    article = session.query(ArticleContent).filter_by(item_id=item_id).first()
    ai_extraction = session.query(AIExtraction).filter_by(item_id=item_id).first()
    master = session.query(MasterItem).filter_by(item_id=item_id).first()

    return templates.TemplateResponse("item_detail.html", {
        "request": request,
        "item": item,
        "article": article,
        "ai_extraction": ai_extraction,
        "master": master
    })



@app.post("/accept/{item_id}")
async def accept_item(
    item_id: int,
    title: str = Form(""),
    company: str = Form(""),
    investors: str = Form(""),
    investment_amount: str = Form(""),
    capital_source: list[str] = Form([]),
    sectors: list[str] = Form([]),
    location: str = Form(""),
    summary: str = Form(""),
    notes: str = Form(""),
    source_url: str = Form(""),
    additional_source_url: str = Form(""),
    session=Depends(get_db),
):
    """Accept item and add to master list."""
    # Check if already in master
    existing = session.query(MasterItem).filter_by(item_id=item_id).first()

    if not existing:
        # Format investment amount with $ prefix
        formatted_amount = None
        if investment_amount:
            clean = investment_amount.replace(',', '').strip()
            if clean:
                formatted_amount = f"${investment_amount.strip()}"

        master = MasterItem(
            item_id=item_id,
            title=title if title else None,
            company=company if company else None,
            investors=investors if investors else None,
            investment_amount=formatted_amount,
            # Capital source (multi-select, stored as comma-separated in capital_sources column)
            capital_sources=",".join(capital_source) if capital_source else None,
            sectors=",".join(sectors) if sectors else None,
            location=location if location else None,
            summary=summary if summary else None,
            human_notes=notes if notes else None,
            source_url=_safe_url(source_url),
            additional_source_url=_safe_url(additional_source_url),
            published=False
        )
        session.add(master)
        session.flush()  # Get master.id for investor links

        # Parse investors and create links
        _sync_investor_links(session, master)

        # Auto-reject duplicate articles about the same company within 7 days
        accepted_raw = session.query(RawItem).filter_by(id=item_id).first()
        accepted_company = company.strip().lower() if company else None
        if accepted_company and accepted_raw and accepted_raw.published_date:
            window_start = accepted_raw.published_date - timedelta(days=7)
            window_end = accepted_raw.published_date + timedelta(days=7)
            # Load candidates with their AIExtraction in one query
            candidates = (
                session.query(RawItem, AIExtraction)
                .join(AIExtraction, AIExtraction.item_id == RawItem.id)
                .filter(
                    RawItem.id != item_id,
                    RawItem.status == 'scraped',
                    RawItem.published_date >= window_start,
                    RawItem.published_date <= window_end,
                )
                .all()
            )
            if candidates:
                candidate_ids = [c.id for c, _ in candidates]
                # Fetch already-handled IDs in two bulk queries instead of N*2
                accepted_ids = {
                    r.item_id for r in session.query(MasterItem.item_id)
                    .filter(MasterItem.item_id.in_(candidate_ids)).all()
                }
                rejected_ids = {
                    r.item_id for r in session.query(RejectedItem.item_id)
                    .filter(RejectedItem.item_id.in_(candidate_ids)).all()
                }
                handled_ids = accepted_ids | rejected_ids
                for candidate, ai in candidates:
                    if (ai and ai.company and ai.company.strip().lower() == accepted_company
                            and candidate.id not in handled_ids):
                        candidate.status = 'rejected'
                        session.add(RejectedItem(
                            item_id=candidate.id,
                            rejection_reason=f"Duplicate — {company} already accepted from another source"
                        ))

        session.commit()
        sync_turso()  # Push write to Turso cloud

    return RedirectResponse(url="/", status_code=303)


@app.post("/reject/{item_id}")
async def reject_item(item_id: int, session=Depends(get_db)):
    """Reject item and remove from triage queue."""
    # Check if already rejected
    existing = session.query(RejectedItem).filter_by(item_id=item_id).first()

    if not existing:
        rejected = RejectedItem(item_id=item_id)
        session.add(rejected)
        session.commit()
        sync_turso()  # Push write to Turso cloud

    return RedirectResponse(url="/", status_code=303)


@app.get("/master", response_class=HTMLResponse)
async def master_list(request: Request, session=Depends(get_db)):
    """View master list of accepted items."""
    sync_turso()

    master_items = session.query(MasterItem).join(
        RawItem, MasterItem.item_id == RawItem.id
    ).order_by(
        MasterItem.curated_at.desc()
    ).all()

    # Add raw item data and pipeline status
    for master in master_items:
        master.raw_item = session.query(RawItem).filter_by(id=master.item_id).first()
        master.article_content = session.query(ArticleContent).filter_by(item_id=master.item_id).first()
        master.ai_extraction = session.query(AIExtraction).filter_by(item_id=master.item_id).first()

    return templates.TemplateResponse("master.html", {
        "request": request,
        "items": master_items
    })


@app.get("/rejected", response_class=HTMLResponse)
async def rejected_list(request: Request, session=Depends(get_db)):
    """View rejected items."""
    sync_turso()

    rejected_items = session.query(RejectedItem).join(
        RawItem, RejectedItem.item_id == RawItem.id
    ).order_by(
        RejectedItem.rejected_at.desc()
    ).all()

    # Add raw item data and pipeline status
    for rejected in rejected_items:
        rejected.raw_item = session.query(RawItem).filter_by(id=rejected.item_id).first()
        rejected.article_content = session.query(ArticleContent).filter_by(item_id=rejected.item_id).first()

    return templates.TemplateResponse("rejected.html", {
        "request": request,
        "items": rejected_items
    })


@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request, session=Depends(get_db)):
    """Show statistics."""
    from sqlalchemy import func

    sync_turso()

    total_raw = session.query(RawItem).count()
    total_scraped = session.query(ArticleContent).filter_by(scrape_success=True).count()
    total_master = session.query(MasterItem).count()

    feed_counts = session.query(
        RawItem.feed_source,
        func.count(RawItem.id)
    ).group_by(RawItem.feed_source).all()

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "total_raw": total_raw,
        "total_scraped": total_scraped,
        "total_master": total_master,
        "feed_counts": feed_counts
    })




@app.get("/costs", response_class=HTMLResponse)
async def costs(request: Request, session=Depends(get_db)):
    """Show API cost tracking and infrastructure costs."""
    from sqlalchemy import func
    from datetime import timedelta

    sync_turso()

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rolling_30 = now - timedelta(days=30)

    # MTD totals
    mtd_rows = session.query(
        ApiUsageLog.run_type,
        func.sum(ApiUsageLog.cost_usd),
        func.sum(ApiUsageLog.input_tokens),
        func.sum(ApiUsageLog.output_tokens),
        func.sum(ApiUsageLog.items_processed),
    ).filter(ApiUsageLog.logged_at >= month_start).group_by(ApiUsageLog.run_type).all()

    mtd_by_type = {r[0]: {"cost": r[1] or 0, "input": r[2] or 0, "output": r[3] or 0, "items": r[4] or 0} for r in mtd_rows}
    mtd_total = sum(v["cost"] for v in mtd_by_type.values())

    # 30-day rolling totals
    rolling_rows = session.query(
        func.sum(ApiUsageLog.cost_usd),
    ).filter(ApiUsageLog.logged_at >= rolling_30).first()
    rolling_total = rolling_rows[0] or 0

    # Daily breakdown — last 30 days
    daily_rows = session.query(
        func.date(ApiUsageLog.logged_at),
        ApiUsageLog.run_type,
        func.sum(ApiUsageLog.cost_usd),
        func.sum(ApiUsageLog.items_processed),
    ).filter(
        ApiUsageLog.logged_at >= rolling_30
    ).group_by(func.date(ApiUsageLog.logged_at), ApiUsageLog.run_type).order_by(func.date(ApiUsageLog.logged_at).desc()).all()

    # Pivot daily rows into {date: {screener: cost, summarizer: cost}}
    daily = {}
    for date_str, run_type, cost, items in daily_rows:
        if date_str not in daily:
            daily[date_str] = {}
        daily[date_str][run_type] = {"cost": cost or 0, "items": items or 0}
    daily_list = sorted(daily.items(), reverse=True)

    # Infrastructure (fixed monthly)
    infra = [
        {"name": "Railway", "cost": 5.00, "note": "Hobby plan"},
        {"name": "Turso", "cost": 0.00, "note": "Free tier"},
        {"name": "Cloudflare Pages", "cost": 0.00, "note": "Free tier"},
    ]
    infra_total = sum(i["cost"] for i in infra)

    return templates.TemplateResponse("costs.html", {
        "request": request,
        "mtd_total": mtd_total,
        "mtd_by_type": mtd_by_type,
        "rolling_total": rolling_total,
        "infra": infra,
        "infra_total": infra_total,
        "all_in_mtd": mtd_total + infra_total,
        "daily_list": daily_list,
    })


@app.get("/excluded", response_class=HTMLResponse)
async def excluded_list(request: Request, session=Depends(get_db)):
    """View items silently excluded from triage (title-screened out or Contract/Award)."""
    sync_turso()

    screened_out_items = session.query(RawItem).filter(
        RawItem.status == 'ai_screened_out',
        ~RawItem.id.in_(session.query(MasterItem.item_id)),
        ~RawItem.id.in_(session.query(RejectedItem.item_id)),
    ).order_by(RawItem.published_date.desc()).all()

    contract_items = session.query(RawItem).join(
        AIExtraction, RawItem.id == AIExtraction.item_id
    ).filter(
        AIExtraction.transaction_type == 'Contract/Award',
        RawItem.status != 'ai_screened_out',
        ~RawItem.id.in_(session.query(MasterItem.item_id)),
        ~RawItem.id.in_(session.query(RejectedItem.item_id)),
    ).order_by(RawItem.published_date.desc()).all()

    for item in contract_items:
        item.ai_extraction = session.query(AIExtraction).filter_by(item_id=item.id).first()

    return templates.TemplateResponse("excluded.html", {
        "request": request,
        "screened_out_items": screened_out_items,
        "contract_items": contract_items,
    })


@app.post("/restore/{item_id}")
async def restore_item(item_id: int, session=Depends(get_db)):
    """Restore an excluded item back to the triage queue."""
    raw = session.query(RawItem).filter_by(id=item_id).first()
    if not raw:
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    if raw.status == 'ai_screened_out':
        raw.status = 'scraped'
        session.commit()
        sync_turso()
    else:
        # Restore Contract/Award item by clearing its transaction_type
        ai = session.query(AIExtraction).filter_by(item_id=item_id).first()
        if ai:
            ai.transaction_type = None
            session.commit()
            sync_turso()

    return RedirectResponse(url="/excluded", status_code=303)


def _update_investor_deal_counts(session, investor_ids):
    """Update deal_count for a set of investor IDs using a single grouped query."""
    if not investor_ids:
        return
    from sqlalchemy import func
    counts = dict(
        session.query(DealInvestor.investor_id, func.count(DealInvestor.id))
        .filter(DealInvestor.investor_id.in_(investor_ids))
        .group_by(DealInvestor.investor_id)
        .all()
    )
    investors = session.query(Investor).filter(Investor.id.in_(investor_ids)).all()
    for investor in investors:
        investor.deal_count = counts.get(investor.id, 0)


def _sync_investor_links(session, master):
    """Parse master.investors text, get-or-create Investor records, create DealInvestor links.

    Deletes existing links first (for edit use case), then recreates.
    """
    # Track investors that need deal_count updates
    affected_investor_ids = set()

    # Get existing links before deleting (to update their counts later)
    old_links = session.query(DealInvestor).filter_by(master_item_id=master.id).all()
    for link in old_links:
        affected_investor_ids.add(link.investor_id)
    session.query(DealInvestor).filter_by(master_item_id=master.id).delete()

    if not master.investors:
        # Update counts for removed investors only
        _update_investor_deal_counts(session, affected_investor_ids)
        return

    parsed = parse_investors(master.investors)
    now = datetime.utcnow()

    for name, is_lead in parsed:
        slug = slugify(name)
        investor = session.query(Investor).filter_by(slug=slug).first()
        if not investor:
            investor = Investor(
                name=name,
                slug=slug,
                deal_count=0,
                first_seen=now,
                last_seen=now,
            )
            session.add(investor)
            session.flush()

        if investor.last_seen is None or now > investor.last_seen:
            investor.last_seen = now

        affected_investor_ids.add(investor.id)

        link = DealInvestor(
            master_item_id=master.id,
            investor_id=investor.id,
            is_lead=is_lead,
        )
        session.add(link)

    # Update deal counts only for affected investors
    _update_investor_deal_counts(session, affected_investor_ids)


@app.get("/edit/{master_id}", response_class=HTMLResponse)
async def edit_item(master_id: int):
    """Redirect to master list — inline edit is now on /master."""
    return RedirectResponse(url="/master", status_code=303)


@app.post("/edit/{master_id}")
async def save_edit(
    master_id: int,
    title: str = Form(""),
    company: str = Form(""),
    investors: str = Form(""),
    investment_amount: str = Form(""),
    capital_source: list[str] = Form([]),
    sectors: list[str] = Form([]),
    location: str = Form(""),
    summary: str = Form(""),
    notes: str = Form(""),
    source_url: str = Form(""),
    additional_source_url: str = Form(""),
    session=Depends(get_db),
):
    """Save edits to an accepted deal."""
    master = session.query(MasterItem).filter_by(id=master_id).first()
    if not master:
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    # Format investment amount with $ prefix
    formatted_amount = None
    if investment_amount:
        clean = investment_amount.replace(',', '').strip()
        if clean:
            formatted_amount = f"${investment_amount.strip()}"

    master.title = title if title else None
    master.company = company if company else None
    master.investors = investors if investors else None
    master.investment_amount = formatted_amount
    master.capital_sources = ",".join(capital_source) if capital_source else None
    master.sectors = ",".join(sectors) if sectors else None
    master.location = location if location else None
    master.summary = summary if summary else None
    master.human_notes = notes if notes else None
    master.source_url = _safe_url(source_url)
    master.additional_source_url = _safe_url(additional_source_url)

    # Re-sync investor links
    _sync_investor_links(session, master)

    session.commit()
    sync_turso()

    return RedirectResponse(url="/master", status_code=303)


@app.get("/investors", response_class=HTMLResponse)
async def investors_list(request: Request, session=Depends(get_db)):
    """View all investors sorted by deal count."""
    sync_turso()

    investors = session.query(Investor).order_by(
        Investor.deal_count.desc(),
        Investor.name.asc()
    ).all()

    total_investors = len(investors)
    total_with_investors = session.query(MasterItem).filter(
        MasterItem.investors != None,
        MasterItem.investors != ''
    ).count()

    return templates.TemplateResponse("investors.html", {
        "request": request,
        "investors": investors,
        "total_investors": total_investors,
        "total_with_investors": total_with_investors,
    })


@app.post("/investors/{investor_id}/delete")
async def delete_investor(investor_id: int, session=Depends(get_db)):
    """Delete an investor and all their deal links."""
    investor = session.query(Investor).filter_by(id=investor_id).first()
    if investor:
        session.query(DealInvestor).filter_by(investor_id=investor_id).delete()
        session.delete(investor)
        session.commit()
        sync_turso()
    return RedirectResponse(url="/investors", status_code=303)


@app.get("/investors/{slug}", response_class=HTMLResponse)
async def investor_detail(request: Request, slug: str, session=Depends(get_db)):
    """Drill-down page for a single investor."""
    sync_turso()

    investor = session.query(Investor).filter_by(slug=slug).first()
    if not investor:
        return HTMLResponse(content="<h1>Investor not found</h1>", status_code=404)

    # Get all deals for this investor with deal info
    links = session.query(DealInvestor).filter_by(investor_id=investor.id).all()

    deals = []
    for link in links:
        master = session.query(MasterItem).filter_by(id=link.master_item_id).first()
        if not master:
            continue
        raw = session.query(RawItem).filter_by(id=master.item_id).first()
        deals.append({
            "master": master,
            "raw": raw,
            "is_lead": link.is_lead,
        })

    # Sort by curated_at desc
    deals.sort(key=lambda d: d["master"].curated_at or datetime.min, reverse=True)

    return templates.TemplateResponse("investor_detail.html", {
        "request": request,
        "investor": investor,
        "deals": deals,
    })


def _parse_amount(amount_str):
    """Parse investment amount string to a float for aggregation.

    Handles: "$15,300,000", "$300M", "$4.7B", "$500K", None
    Returns None if unparseable.
    """
    if not amount_str:
        return None
    clean = amount_str.replace('$', '').replace(',', '').strip()
    if not clean:
        return None
    import re
    match = re.match(r'^([\d.]+)\s*([KMBT])', clean, re.IGNORECASE)
    if match:
        num = float(match.group(1))
        suffix = match.group(2).upper()
        multipliers = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}
        return num * multipliers.get(suffix, 1)
    try:
        return float(clean)
    except ValueError:
        return None


def _format_amount(value):
    """Format a numeric amount as a readable string like $1.2B or $300M."""
    if value is None or value == 0:
        return None
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.0f}M"
    if value >= 1e3:
        return f"${value / 1e3:.0f}K"
    return f"${value:,.0f}"


@app.get("/sectors", response_class=HTMLResponse)
async def sectors_list(request: Request, session=Depends(get_db)):
    """View deal activity by sector/technology."""
    items = session.query(MasterItem).filter(
        MasterItem.sectors != None,
        MasterItem.sectors != ''
    ).order_by(MasterItem.curated_at.desc()).all()

    # Aggregate by sector
    from collections import defaultdict
    sector_data = defaultdict(lambda: {
        'count': 0, 'total_value': 0, 'companies': [], 'last_seen': None
    })

    for item in items:
        for sector in item.sectors.split(','):
            sector = sector.strip()
            if not sector:
                continue
            data = sector_data[sector]
            data['count'] += 1
            amount = _parse_amount(item.investment_amount)
            if amount:
                data['total_value'] += amount
            if item.company and item.company not in data['companies']:
                data['companies'].append(item.company)
            if data['last_seen'] is None or (item.curated_at and item.curated_at > data['last_seen']):
                data['last_seen'] = item.curated_at

    # Build sorted list
    sectors = []
    for name, data in sorted(sector_data.items(), key=lambda x: x[1]['count'], reverse=True):
        sectors.append({
            'name': name,
            'count': data['count'],
            'total_value': _format_amount(data['total_value']),
            'companies': data['companies'][:3],
            'last_seen': data['last_seen'],
        })

    return templates.TemplateResponse("sectors.html", {
        "request": request,
        "sectors": sectors,
    })


@app.get("/sectors/{sector_name}", response_class=HTMLResponse)
async def sector_deals(request: Request, sector_name: str, session=Depends(get_db)):
    """View all deals in a specific sector."""
    from urllib.parse import unquote
    sector_name = unquote(sector_name)

    # Find master items containing this sector
    all_items = session.query(MasterItem).filter(
        MasterItem.sectors != None
    ).order_by(MasterItem.curated_at.desc()).all()

    # Filter to items that contain this sector
    items = []
    for item in all_items:
        sector_list = [s.strip() for s in item.sectors.split(',')]
        if sector_name in sector_list:
            item.raw_item = session.query(RawItem).filter_by(id=item.item_id).first()
            items.append(item)

    return templates.TemplateResponse("sector_deals.html", {
        "request": request,
        "sector_name": sector_name,
        "items": items,
    })


if __name__ == "__main__":
    import uvicorn

    # Change to project root
    os.chdir(Path(__file__).parent.parent.parent)

    uvicorn.run(app, host="127.0.0.1", port=8000)
