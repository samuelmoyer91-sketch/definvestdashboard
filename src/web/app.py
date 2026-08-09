"""FastAPI web application for triage and dashboard."""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import contextvars
import secrets
import time
from collections import deque
from fastapi import BackgroundTasks, FastAPI, Request, Form, Query, Depends
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


# Railway's logs are not reachable from a dev machine without a live CLI
# token, and during the accept-latency hunt that turned every warning the app
# was emitting into a dead end — including the ones that would have named the
# cause. Keep the recent warnings in memory and serve them from
# /api/diagnostics so they can be read from anywhere.
class _RecentLogHandler(logging.Handler):
    def __init__(self, capacity=100):
        super().__init__(level=logging.WARNING)
        self.records = deque(maxlen=capacity)

    def emit(self, record):
        try:
            self.records.append({
                "at": datetime.utcfromtimestamp(record.created).isoformat(timespec="seconds"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage()[:500],
            })
        except Exception:
            pass  # logging must never break a request


_recent_logs = _RecentLogHandler()
logging.getLogger().addHandler(_recent_logs)

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, MasterItem, RejectedItem, Investor, DealInvestor, ApiUsageLog, get_session, sync_turso
from src.database.models import (_reset_turso_connection, set_interactive_mode,
                                 keepalive as db_keepalive, SPLIT_FRAGMENT)
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
# Whole-request timing
# =============================================================================
#
# The per-phase timers inside accept/reject start on the FIRST LINE OF THE
# HANDLER BODY, which makes them blind to most of a request. Sam reports
# 10-15s clicks while those timers report ~76ms, and they would report ~76ms
# either way. Everything below happens before the handler body runs and was
# never measured:
#
#   - Depends(get_db) -> get_session(), which acquires the DB connection.
#     StaticPool holds exactly ONE connection for the whole process, so a
#     request can block here waiting for whatever is using it.
#   - BasicAuthMiddleware, and reading/parsing the form body.
#   - Time queued on the event loop. Every route is `async def` doing blocking
#     SQLAlchemy I/O, so one slow request stalls the loop for all others.
#
# This middleware wraps the entire ASGI call, so total_ms covers everything
# the app is responsible for. pre_handler_ms is the gap the old timers could
# not see. A large pre_handler_ms with a small handler total means the app is
# WAITING (connection or event loop), not working — a different bug entirely
# from a slow query, and it needs a different fix.
#
# Written as pure ASGI rather than BaseHTTPMiddleware, which adds its own
# task-and-queue overhead per request and would pollute the measurement.

_req_ctx: contextvars.ContextVar = contextvars.ContextVar("req_ctx", default=None)

# Requests currently in flight. StaticPool gives the whole process a SINGLE
# DB connection, so the keepalive ping must never fire while a request is
# using it — two callers on one libsql connection is not safe. The keepalive
# only needs to run when nothing else is talking to the database anyway,
# which is precisely when the stream would otherwise be going stale.
_inflight = 0
_TIMED_PREFIXES = ("/accept/", "/reject/", "/master/")


# ---------------------------------------------------------------------------
# Statement-level SQL timing
# ---------------------------------------------------------------------------
# Phase timings said accept spends ~2s in "investors" and ~1s in "commit", but
# a phase is still an aggregate. Cutting accept from 9 write statements to 4
# changed the total by nothing, which means the per-statement model was wrong:
# either executemany still costs a round trip per row, or the statements are
# not where the time goes at all.
#
# A reject is one INSERT plus a commit and reliably takes ~1000ms, of which
# ~990ms is the commit phase. If the INSERT itself turns out to be ~5ms, then
# the entire cost is the transaction commit reaching the Turso primary, and
# statement count was never the lever. That is the question this answers.
#
# Records the SQL text (schema only, truncated) and duration. NEVER the bound
# parameters — those carry deal content.
_stmt_log = deque(maxlen=400)


def _install_sql_timing():
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        try:
            context._pcd_t0 = time.perf_counter()
        except Exception:
            pass

    @event.listens_for(Engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        t0 = getattr(context, "_pcd_t0", None)
        if t0 is None:
            return
        rec = {
            "verb": statement.strip().split(None, 1)[0].upper()[:12],
            "ms": round((time.perf_counter() - t0) * 1000, 1),
            "rows": (len(parameters) if executemany and parameters is not None else 1),
            "sql": " ".join(statement.split())[:70],
        }
        _stmt_log.append(rec)
        ctx = _req_ctx.get()
        if ctx is not None:
            ctx.setdefault("stmts", []).append(rec)


_install_sql_timing()


def _sql_summary():
    """Median/slowest per SQL verb over recent statements.

    The comparison that matters: if SELECTs are ~1ms (local replica) and
    INSERTs are also ~1ms while whole requests take a second, the cost is the
    commit round trip, not the statements.
    """
    by_verb = {}
    for r in _stmt_log:
        by_verb.setdefault(r["verb"], []).append(r["ms"])
    out = {}
    for verb, vals in by_verb.items():
        s = sorted(vals)
        out[verb] = {"n": len(s), "median_ms": s[len(s) // 2], "slowest_ms": s[-1]}
    return out


class RequestTimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        ctx = {"t0": time.perf_counter(), "path": scope.get("path", ""),
               "method": scope.get("method", ""), "phases": None, "kind": None,
               "session_ms": None, "handler_start": None, "ttfb_ms": None}
        _req_ctx.set(ctx)

        async def send_wrapper(message):
            if message["type"] == "http.response.start" and ctx["ttfb_ms"] is None:
                ctx["ttfb_ms"] = round((time.perf_counter() - ctx["t0"]) * 1000, 1)
            await send(message)

        global _inflight
        _inflight += 1
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            _inflight -= 1
            total = round((time.perf_counter() - ctx["t0"]) * 1000, 1)
            path = ctx["path"]
            if any(path.startswith(p) for p in _TIMED_PREFIXES) or ctx["kind"]:
                pre = (round((ctx["handler_start"] - ctx["t0"]) * 1000, 1)
                       if ctx["handler_start"] else None)
                stmts = ctx.get("stmts") or []
                entry = {
                    "kind": ctx["kind"] or path.strip("/").split("/")[0] or "request",
                    "at": datetime.utcnow().isoformat(timespec="seconds"),
                    "total_ms": total,
                    "ttfb_ms": ctx["ttfb_ms"],
                    "pre_handler_ms": pre,
                    "session_ms": ctx["session_ms"],
                    "phases": ctx["phases"] or {},
                    # How much of the request is actually spent inside SQL
                    # statements. If this is a small fraction of total_ms, the
                    # time is going to the commit round trip instead.
                    "sql_count": len(stmts),
                    "sql_total_ms": round(sum(x["ms"] for x in stmts), 1),
                    "sql_slowest": sorted(stmts, key=lambda x: -x["ms"])[:6],
                }
                _accept_timings.append(entry)
                logger.info(
                    "TIMING %s total=%sms pre_handler=%sms session=%sms phases=%s",
                    entry["kind"], total, pre, ctx["session_ms"], entry["phases"])


app.add_middleware(RequestTimingMiddleware)


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
    """FastAPI dependency: yield a DB session and close it when done.

    get_session() is timed because it runs BEFORE the handler body and was
    therefore invisible to the per-phase timers. StaticPool keeps a single
    connection for the process, so this is where a request blocks when
    something else holds it — a prime suspect for clicks that take seconds
    while the handler itself measures tens of milliseconds.
    """
    t0 = time.perf_counter()
    session = get_session()
    ctx = _req_ctx.get()
    if ctx is not None:
        ctx["session_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    try:
        yield session
    finally:
        session.close()


_last_sync_time: float = 0
_SYNC_INTERVAL = 300  # seconds (5 minutes)
_pending_sync: bool = False
_last_sync_ms: float = 0.0

_STARTED_AT_TS = time.time()
_STARTED_AT = datetime.utcnow().isoformat(timespec="seconds")


def mark_dirty():
    """Note that we wrote something, without paying for a sync right now.

    Accept and reject used to call sync_turso() on every single click. That
    is a network round trip to the Turso primary against a 100MB+ database,
    and it sat on the critical path of every triage action — which is why
    both buttons have always felt slow, accept worse than reject only
    because it does more work on top. Nothing needs the replica refreshed
    the instant a card is accepted: the UI removes the card client-side, and
    the next page render calls sync_if_stale(), which now syncs immediately
    when this flag is set. Reads therefore stay correct while clicks get out
    of the sync business entirely.
    """
    global _pending_sync
    _pending_sync = True


def sync_if_stale():
    """Sync the replica if we have unsynced writes, or it has gone stale."""
    global _last_sync_time, _pending_sync, _last_sync_ms
    now = time.time()
    if _pending_sync or now - _last_sync_time > _SYNC_INTERVAL:
        t0 = time.perf_counter()
        sync_turso()
        _last_sync_ms = round((time.perf_counter() - t0) * 1000, 1)
        _last_sync_time = time.time()
        _pending_sync = False
        logger.info("TIMING sync total=%sms", _last_sync_ms)

# =============================================================================
# Startup Migration — ensures schema is current on deploy
# =============================================================================

@app.on_event("startup")
async def enable_interactive_db_mode():
    """Short sync-retry backoff for this process — see models.BATCH_BACKOFF.

    A web request must never sit in a 5s or 10s time.sleep() waiting for a
    replica sync; that blocks the event loop and the user just watches a
    card refuse to disappear.
    """
    set_interactive_mode(True)
    logger.info("DB interactive mode enabled (short sync-retry backoff)")


@app.on_event("startup")
async def start_db_keepalive():
    """Ping the DB every 30s so Turso never expires the stream.

    Turso drops an idle Hrana stream server-side. When that happens the next
    request pays for the reconnect: probe fails, connection resets, rebuild
    runs reconnect + sync. Sam reads each triage item for well over the 60s
    idle threshold, so nearly every accept was a candidate for that penalty
    while rapid-fire rejects escaped it — which matches the reported
    accept-vs-reject asymmetry. Keeping the stream warm moves that cost off
    the click path entirely.
    """
    async def loop():
        while True:
            await asyncio.sleep(30)
            if _inflight:
                continue  # never share the single connection with a live request
            try:
                # to_thread: the libsql call is blocking, and this must not
                # stall the event loop it is meant to be protecting.
                await asyncio.to_thread(db_keepalive)
            except Exception as e:
                logger.warning(f"Keepalive task error: {e}")

    asyncio.create_task(loop())
    logger.info("DB keepalive started (30s)")


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

        # Soft-delete columns on master_list (see MasterItem.removed_at).
        #
        # Uses PRAGMA rather than the try-SELECT-except-ALTER pattern above,
        # and VERIFIES the result. The first cut of this used that pattern,
        # logged "added successfully" on Railway, and left the columns absent
        # — every page then 500'd with "no such column: master_list.removed_at".
        # DDL issued here does not reliably reach the Turso primary, so the
        # real fix is scripts/migrate_soft_delete.py run from GitHub Actions.
        # This block stays as a best effort for local/SQLite, but it must not
        # claim success it cannot confirm.
        try:
            present = {r[1] for r in conn.execute(
                sa_text("PRAGMA table_info(master_list)")).fetchall()}
            for col, typedef in [("removed_at", "DATETIME"), ("removed_reason", "TEXT")]:
                if col in present:
                    continue
                logger.info(f"Adding {col} column to master_list...")
                conn.execute(sa_text(f"ALTER TABLE master_list ADD COLUMN {col} {typedef}"))
                conn.commit()

            after = {r[1] for r in conn.execute(
                sa_text("PRAGMA table_info(master_list)")).fetchall()}
            missing = [c for c, _ in [("removed_at", None), ("removed_reason", None)]
                       if c not in after]
            if missing:
                logger.error(
                    "SCHEMA: master_list is missing %s after migration. The app "
                    "WILL 500 on the master list, map, stats and dup pages. Fix: "
                    "gh workflow run migrate.yml", missing)
            else:
                logger.info("master_list soft-delete columns verified present")
        except Exception as e:
            logger.error(f"SCHEMA: soft-delete migration failed: {e}")

        # Check if deal_status column exists on ai_extractions
        try:
            conn.execute(sa_text("SELECT deal_status FROM ai_extractions LIMIT 1"))
        except Exception:
            logger.info("Adding deal_status column to ai_extractions...")
            conn.execute(sa_text("ALTER TABLE ai_extractions ADD COLUMN deal_status TEXT"))
            conn.commit()
            logger.info("ai_extractions.deal_status column added successfully")

        # Check if capital_deployment column exists on ai_extractions
        try:
            conn.execute(sa_text("SELECT capital_deployment FROM ai_extractions LIMIT 1"))
        except Exception:
            logger.info("Adding capital_deployment column to ai_extractions...")
            conn.execute(sa_text("ALTER TABLE ai_extractions ADD COLUMN capital_deployment TEXT"))
            conn.commit()
            logger.info("ai_extractions.capital_deployment column added successfully")

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

    # Backstop for a Turso stream dying mid-request (get_session's idle probe
    # handles the common overnight case, but a stream can also expire between
    # the probe and the query). Drop the cached connection so the next request
    # rebuilds it, instead of every subsequent request failing until redeploy.
    if 'stream not found' in str(exc).lower() or 'hrana' in str(exc).lower():
        logger.warning("Turso stream error — resetting connection so the next request reconnects.")
        try:
            _reset_turso_connection()
        except Exception as reset_err:
            logger.error(f"Failed to reset Turso connection: {reset_err}")
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

def _timing_summary():
    """Per-action medians, split into waiting vs working.

    pre_handler_ms is time the request spent before the handler body ran —
    connection acquisition, middleware, event-loop queueing. If that dwarfs
    handler_total, the app is blocked, not busy.
    """
    out = {}
    for kind in ("accept", "reject"):
        items = [t for t in _accept_timings if t["kind"] == kind]
        if not items:
            continue
        tot = sorted(t["total_ms"] for t in items)
        pre = sorted(t["pre_handler_ms"] for t in items if t.get("pre_handler_ms") is not None)
        ses = sorted(t["session_ms"] for t in items if t.get("session_ms") is not None)
        slowest = max(items, key=lambda t: t["total_ms"])
        out[kind] = {
            "n": len(items),
            "median_total_ms": tot[len(tot) // 2],
            "slowest_total_ms": tot[-1],
            "median_pre_handler_ms": pre[len(pre) // 2] if pre else None,
            "median_session_ms": ses[len(ses) // 2] if ses else None,
            "slowest": {
                "total_ms": slowest["total_ms"],
                "pre_handler_ms": slowest.get("pre_handler_ms"),
                "session_ms": slowest.get("session_ms"),
                "phases": slowest.get("phases"),
            },
        }
    return out


@app.get("/health")
async def health_check():
    """Health check for Railway, plus enough to answer two questions from
    outside the auth wall: which commit is actually serving, and how long
    triage actions are taking.

    /health is the only unauthenticated route, and during the schema outage
    it returned 200 the whole time — a green health check proved nothing.
    Reporting the running commit makes "did the deploy land?" answerable
    instead of assumed, and the timing medians make "is it still slow?"
    answerable without asking Sam to open devtools.

    Deliberately limited to operational metadata: commit sha, uptime, and
    action durations. No deal content, no counts of the data itself, nothing
    that isn't already implied by the site being up.
    """
    summary = _timing_summary()

    return {
        "status": "healthy",
        "commit": (os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "unknown")[:8],
        "started_at": _STARTED_AT,
        "uptime_s": round(time.time() - _STARTED_AT_TS),
        "last_sync_ms": _last_sync_ms,
        "pending_sync": _pending_sync,
        "timings": summary or None,
        # Per-request sequence, not just medians: a one-off 15s reconnect on
        # the first click after a deploy and a recurring one look identical in
        # a median. Durations only — no deal content.
        "recent": [
            {k: t.get(k) for k in
             ("kind", "at", "total_ms", "pre_handler_ms", "session_ms", "phases",
              "sql_count", "sql_total_ms", "sql_slowest")}
            for t in list(_accept_timings)[-12:]
        ],
        "sql_by_verb": _sql_summary(),
    }


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

    recent = list(_accept_timings)

    return {
        "overall": overall,
        "env_vars": env_status,
        "database": {"connected": db_ok, "error": db_error},
        "counts": counts,
        # Where triage time actually goes. total_ms is the WHOLE request;
        # pre_handler_ms is the part spent before the handler body ran
        # (connection acquisition, middleware, event-loop queueing). A big
        # pre_handler_ms means blocked, not busy.
        "timings": {
            **_timing_summary(),
            "recent": recent[-15:],
        },
        # Recent WARNING/ERROR lines. Reconnects and failed syncs show up
        # here, which is what makes a latency spike explainable instead of
        # merely visible.
        "recent_warnings": list(_recent_logs.records)[-25:],
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


# Marker appended to RawItem.relevance_flags when Sam confirms a flagged item
# is NOT a duplicate (so it stays in the main queue on future loads). Reusing
# the existing TEXT column avoids a schema change.
DEDUP_KEEP_MARKER = "dedup_keep"


# How many triage cards to render per page load. Each card is a full form
# (~40 inputs), so this is the main driver of how snappy triage feels.
TRIAGE_PAGE_SIZE = 20


# Accept has felt slow since the system was first built — long before the
# dedup or pagination work — and the card only disappears once the server
# answers, so the wait is server-side. Rather than guess again, time each
# phase and keep the last N so the numbers can be read off /api/diagnostics.
# Also emitted as a Server-Timing header, which browser devtools graphs for
# free on the Network tab.
_accept_timings = deque(maxlen=50)


class _Phases:
    """Stopwatch that records elapsed ms between mark() calls."""

    def __init__(self):
        self._t0 = time.perf_counter()
        self._last = self._t0
        self.marks = []
        # Tell the timing middleware when the handler body actually began, so
        # it can report how long the request spent getting here.
        ctx = _req_ctx.get()
        if ctx is not None:
            ctx["handler_start"] = self._t0

    def mark(self, name):
        now = time.perf_counter()
        self.marks.append((name, round((now - self._last) * 1000, 1)))
        self._last = now

    @property
    def total_ms(self):
        return round((time.perf_counter() - self._t0) * 1000, 1)

    def header(self):
        """Server-Timing header value, e.g. 'lookup;dur=3.2, commit;dur=812.0'."""
        parts = [f"{n};dur={ms}" for n, ms in self.marks]
        ctx = _req_ctx.get()
        if ctx is not None:
            if ctx.get("session_ms") is not None:
                parts.insert(0, f"session;dur={ctx['session_ms']}")
            if ctx.get("handler_start"):
                pre = round((ctx["handler_start"] - ctx["t0"]) * 1000, 1)
                parts.insert(0, f"prehandler;dur={pre}")
        parts.append(f"handler;dur={self.total_ms}")
        return ", ".join(parts)

    def record(self, kind):
        """Hand the phase breakdown to the middleware, which owns the ring
        buffer — it is the only place that sees the whole request."""
        phases = dict(self.marks)
        phases["handler_total"] = self.total_ms
        ctx = _req_ctx.get()
        if ctx is not None:
            ctx["phases"] = phases
            ctx["kind"] = kind
        return phases


def _triage_action_response(request: Request, phases=None):
    """Response for accept/reject.

    The triage UI calls these with fetch() and removes the card itself, so the
    body is discarded — but fetch follows redirects by default, which meant a
    303 to "/" made the server render and ship the WHOLE queue page on every
    click, only for the browser to throw it away. Return 204 to those callers
    instead. item_detail.html posts a real <form> and still needs the redirect.
    """
    headers = {"Server-Timing": phases.header()} if phases else None
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return Response(status_code=204, headers=headers)
    return RedirectResponse(url="/", status_code=303, headers=headers)


def active_master(session):
    """Master-list query excluding soft-deleted deals.

    Every user-facing view of the master list must go through this, or removed
    duplicates reappear somewhere. Deliberately NOT used for lookups by
    item_id during accept — those must still see removed rows so re-accepting
    an item updates the existing row instead of creating a second one.
    """
    return session.query(MasterItem).filter(MasterItem.removed_at.is_(None))


def _triage_queue_items(session):
    """Base triage-queue query, shared by the main queue (/) and the
    Possible Duplicates page. Returns RawItem rows with .article_content and
    .ai_extraction attached. Centralizing this keeps the two views in sync."""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    # Get items that:
    # 1. Have been successfully scraped
    # 2. Are not yet in master list
    # 3. Have not been rejected
    # 4. Were not screened out by AI title filter
    # 5. Are not Contract/Award transaction type (routine contracts/SBIR auto-filtered)
    # 6. Have not been AI-extracted to all-Unknown stub (failed scrapes summarized as empty)
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
        # Exclude IPOs (0% accept rate — filings are not capital deployment events)
        ~((AIExtraction.transaction_type != None) & (AIExtraction.transaction_type == 'IPO')),
        # Exclude speculative deals (rumors, plans, "considering", "seeks", etc.)
        ~((AIExtraction.deal_status != None) & (AIExtraction.deal_status == 'speculative')),
        # Exclude ownership-transfer deals with no dollar amount (no new capital signal)
        ~(
            (AIExtraction.capital_deployment != None) &
            (AIExtraction.capital_deployment == 'transfer') &
            (AIExtraction.deal_amount == None)
        ),
        # Exclude all-Unknown stub extractions (typically from failed Google News
        # redirect scrapes that returned ~11 chars of stub text — show up as empty
        # cards). Items with no AIExtraction row at all still pass through (they're
        # legitimate pending items waiting for AI summarization).
        # The all-Unknown filter hides junk from failed scrapes. It must never
        # hide a card Sam explicitly acted on: if a split's re-extraction comes
        # back empty, the card has to stay visible so the failure is obvious
        # and fixable, rather than the action appearing to do nothing.
        ~(
            (AIExtraction.id != None) &
            (RawItem.split_instruction == None) &
            func.lower(func.coalesce(AIExtraction.company, '')).in_(['unknown', 'none', '']) &
            func.lower(func.coalesce(AIExtraction.deal_amount, '')).in_(['unknown', '']) &
            func.lower(func.coalesce(AIExtraction.deal_type, '')).in_(['unknown', ''])
        )
    ).order_by(
        RawItem.published_date.desc()
    ).limit(200).all()

    for item in items:
        item.article_content = item.article
        item.ai_extraction = item.extraction
    return items


def _queue_dup_flagged_ids(session, queue_items):
    """Return the set of queue RawItem.ids that look like duplicates of an
    already-published deal or of another queue item. Pure read; uses
    dedup.find_queue_duplicates. Used to split flagged items out of the main
    queue and into the Possible Duplicates page."""
    from src.utils import dedup

    def q_dict(item):
        ext = item.ai_extraction
        return {
            'id': item.id,
            'company': (ext.company if ext else None) or item.title,
            'amount': (ext.deal_amount if ext else None),
            'date': item.published_date,
            'title': (ext.title if ext and ext.title else item.title),
            'source': item.feed_source,
            'location': (ext.location if ext else None),
            'insight': (ext.strategic_significance if ext else None),
            'group_key': f"art:{item.split_group_id}",
        }

    # RawItem is joined only for split_parent_id. Deals split out of one
    # roundup share a company and a date by construction, so without a
    # group_key they would flag each other and vanish into Possible Duplicates.
    published = [{
        'id': m.id,
        'company': m.company,
        'amount': m.investment_amount,
        'date': m.curated_at or m.published_at,
        'title': m.title or m.company,
        'source': m.source_url,
        'location': m.location,
        'group_key': f"art:{split_parent_id or m.item_id}",
    } for m, split_parent_id in (
        active_master(session)
        .join(RawItem, MasterItem.item_id == RawItem.id)
        .add_columns(RawItem.split_parent_id)
        .all()
    )]

    # Items Sam explicitly confirmed are NOT duplicates carry a marker in
    # relevance_flags; never re-flag them.
    eligible = [i for i in queue_items if DEDUP_KEEP_MARKER not in (i.relevance_flags or "")]
    result = dedup.find_queue_duplicates([q_dict(i) for i in eligible], published)
    return result['flagged_ids']


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session=Depends(get_db)):
    """Home page showing triage queue (with likely-duplicate items routed out
    to the Possible Duplicates page so they don't clutter the main flow)."""
    sync_if_stale()

    all_items = _triage_queue_items(session)
    flagged = _queue_dup_flagged_ids(session, all_items)
    items = [i for i in all_items if i.id not in flagged]

    total_items = len(items)
    master_count = active_master(session).count()

    # Render only the top of the queue. Every accept/reject redirects back
    # here, so the whole page is rebuilt on each click — and each card carries
    # a full form (~40 inputs, incl. the 22 sector checkboxes). Rendering the
    # entire queue meant ~8,000 inputs and 6MB of HTML per click, which is what
    # made triage feel slow; the cost was in the browser, not the server
    # (queries 0.09s, template 0.04s). Triage is worked top-down, so the rest
    # was never looked at. The queue re-queries on each action, so the next
    # items surface automatically as these are cleared.
    visible = items[:TRIAGE_PAGE_SIZE]

    return templates.TemplateResponse("triage.html", {
        "request": request,
        "items": visible,
        "total_items": total_items,
        "showing_count": len(visible),
        "master_count": master_count,
        "dup_count": len(flagged),
    })


@app.get("/possible-duplicates", response_class=HTMLResponse)
async def possible_duplicates(request: Request, session=Depends(get_db)):
    """Likely-duplicate triage items, grouped by the deal they duplicate.

    Read-only computation (reuses dedup.find_queue_duplicates). Each group is
    either a queue item matching an already-published deal (Type 1, shown with
    the published deal as a greyed anchor) or a cluster of queue items that look
    like the same fresh deal (Type 2). Nothing is auto-removed — Sam decides via
    [Reject as dup] / [Keep] / group-level keep-best."""
    from src.utils import dedup
    sync_if_stale()

    queue_items = _triage_queue_items(session)
    by_id = {i.id: i for i in queue_items}
    # Skip items Sam already confirmed are not duplicates
    eligible = [i for i in queue_items if DEDUP_KEEP_MARKER not in (i.relevance_flags or "")]

    def q_dict(item):
        ext = item.ai_extraction
        return {
            'id': item.id,
            'company': (ext.company if ext else None) or item.title,
            'amount': (ext.deal_amount if ext else None),
            'date': item.published_date,
            'title': (ext.title if ext and ext.title else item.title),
            'source': item.feed_source,
            'location': (ext.location if ext else None),
            'insight': (ext.strategic_significance if ext else None),
            'group_key': f"art:{item.split_group_id}",
        }

    # RawItem is joined only for split_parent_id. Deals split out of one
    # roundup share a company and a date by construction, so without a
    # group_key they would flag each other and vanish into Possible Duplicates.
    published = [{
        'id': m.id,
        'company': m.company,
        'amount': m.investment_amount,
        'date': m.curated_at or m.published_at,
        'title': m.title or m.company,
        'source': m.source_url,
        'location': m.location,
        'group_key': f"art:{split_parent_id or m.item_id}",
    } for m, split_parent_id in (
        active_master(session)
        .join(RawItem, MasterItem.item_id == RawItem.id)
        .add_columns(RawItem.split_parent_id)
        .all()
    )]

    result = dedup.find_queue_duplicates([q_dict(i) for i in eligible], published)

    # decorate each queue entry with the live URL (for "View Original")
    for g in result['groups']:
        for q in g['queue']:
            raw = by_id.get(q['id'])
            q['url'] = raw.canonical_url if raw else '#'
            q['amount_fmt'] = dedup.fmt_amount(q['amount_num'])
            q['date_fmt'] = q['date'].strftime('%Y-%m-%d') if q['date'] else '—'
        for p in g['published']:
            p['amount_fmt'] = dedup.fmt_amount(p['amount_num'])
            p['date_fmt'] = p['date'].strftime('%Y-%m-%d') if p['date'] else '—'

    return templates.TemplateResponse("possible_duplicates.html", {
        "request": request,
        "groups": result['groups'],
        "group_count": len(result['groups']),
        "flagged_count": len(result['flagged_ids']),
    })


@app.post("/split/{item_id}")
async def split_item(item_id: int, focuses: str = Form(default=""),
                     session=Depends(get_db)):
    """Re-do a roundup article as one focused deal per line of `focuses`.

    A roundup announces several deals but produces one card that mooshes them
    together. Each line here becomes a separate pass over the same article
    text, told which deal to extract. Line 1 re-focuses the ORIGINAL row in
    place; later lines each become a new raw_items row. Every pass therefore
    gets its own extraction and, once accepted, its own master_list row —
    without touching any uniqueness constraint.

    Re-extraction runs synchronously rather than in a BackgroundTask: with
    StaticPool the process has ONE database connection, and a background
    thread using it while a request is mid-query is unsafe (see the keepalive
    fix, commit 3fc8917). A synchronous call adds no concurrency — it is the
    request's own thread — at the cost of the caller waiting ~10s per deal.
    """
    # Split on semicolons as well as newlines. Listing several deals on one
    # line separated by semicolons is a natural way to write them, and taking
    # only newlines silently collapsed five deals into one unusable focus.
    import re as _re
    lines = [p.strip() for p in _re.split(r'[\n;]+', focuses or "") if p.strip()]
    if not lines:
        return RedirectResponse(url="/", status_code=303)

    original = session.query(RawItem).filter_by(id=item_id).first()
    if not original:
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    # The queue page may have been rendered before this item was accepted or
    # rejected elsewhere. Splitting a stale card wrote a focus onto a row that
    # could never appear again, which looked exactly like the split failing.
    if session.query(MasterItem).filter_by(item_id=item_id).first():
        return HTMLResponse(
            content="<h1>Already accepted</h1><p>This article has already been "
                    'accepted as a deal, so it cannot be split.</p>'
                    '<p><a href="/">Back to queue</a></p>', status_code=409)
    if session.query(RejectedItem).filter_by(item_id=item_id).first():
        return HTMLResponse(
            content="<h1>Already rejected</h1><p>This article was rejected — most "
                    "likely auto-rejected when you accepted the same company from "
                    'another source. Restore it first, then split.</p>'
                    '<p><a href="/">Back to queue</a></p>', status_code=409)

    article = session.query(ArticleContent).filter_by(item_id=item_id).first()
    if not article or not article.clean_text:
        return HTMLResponse(
            content="<h1>Cannot split</h1><p>This article has no scraped text to "
                    're-extract from.</p><p><a href="/">Back to queue</a></p>',
            status_code=400)

    # Always attach passes to the ORIGINAL article, so splitting an already
    # split row widens that article's set rather than building a chain.
    group_id = original.split_group_id
    base_url = original.canonical_url

    original.split_instruction = lines[0]
    affected = [original.id]

    # Number clones after any that already exist, so re-splitting cannot
    # collide with an existing url.
    next_n = session.query(RawItem).filter(
        RawItem.split_parent_id == group_id).count() + 2

    for focus in lines[1:]:
        clone = RawItem(
            url=f"{base_url}{SPLIT_FRAGMENT}{next_n}",
            title=original.title,
            rss_summary=original.rss_summary,
            published_date=original.published_date,
            feed_source=original.feed_source,
            # 'scraped' means the title screener and the article scraper both
            # skip it — the text is copied below, not re-fetched.
            status='scraped',
            relevance_score=original.relevance_score,
            relevance_flags=original.relevance_flags,
            split_instruction=focus,
            split_parent_id=group_id,
        )
        session.add(clone)
        session.flush()
        session.add(ArticleContent(
            item_id=clone.id,
            html=article.html,
            clean_text=article.clean_text,
            scrape_success=True,
        ))
        affected.append(clone.id)
        next_n += 1

    session.commit()

    # Failure here is non-fatal: the rows exist, and the nightly ingest picks
    # up anything without a complete extraction — correctly, because
    # split_instruction is persisted rather than passed at call time.
    try:
        from src.scraper.generate_ai_summaries import generate_summaries
        generate_summaries(item_ids=affected)
    except Exception as e:
        logger.error(f"Split re-extraction failed for {affected}: {e}")

    mark_dirty()
    return RedirectResponse(url="/", status_code=303)


@app.post("/reject-dup/{item_id}")
async def reject_duplicate(item_id: int, background_tasks: BackgroundTasks,
                           dup_of: str = Form(default=""), session=Depends(get_db)):
    """Reject a single queue item as a duplicate (from the Possible Dups page).
    Records a rejection_reason so the action is auditable."""
    existing = session.query(RejectedItem).filter_by(item_id=item_id).first()
    if not existing:
        reason = f"Duplicate of {dup_of}" if dup_of else "Duplicate (flagged pre-triage)"
        session.add(RejectedItem(item_id=item_id, rejection_reason=reason))
        session.commit()
        background_tasks.add_task(sync_turso)
    return RedirectResponse(url="/possible-duplicates", status_code=303)


@app.post("/reject-dup-group")
async def reject_duplicate_group(background_tasks: BackgroundTasks,
                                 keep_id: int = Form(...),
                                 reject_ids: str = Form(default=""),
                                 dup_of: str = Form(default=""),
                                 session=Depends(get_db)):
    """Group-level 'keep one, reject the rest'. keep_id stays in the queue;
    every id in reject_ids (comma-separated) is rejected as a duplicate."""
    ids = [int(x) for x in reject_ids.split(',') if x.strip().isdigit()]
    for rid in ids:
        if rid == keep_id:
            continue
        if not session.query(RejectedItem).filter_by(item_id=rid).first():
            reason = f"Duplicate of #{keep_id}" + (f" ({dup_of})" if dup_of else "")
            session.add(RejectedItem(item_id=rid, rejection_reason=reason))
    session.commit()
    background_tasks.add_task(sync_turso)
    return RedirectResponse(url="/possible-duplicates", status_code=303)


@app.post("/keep-dup/{item_id}")
async def keep_duplicate(item_id: int, background_tasks: BackgroundTasks, session=Depends(get_db)):
    """Mark a flagged item as NOT a duplicate so it returns to the main queue
    and stays there on future loads.

    The dup flag is computed live on every page load, so 'keep' must persist a
    decision. No schema change (per the locked design): we append a marker to
    the existing RawItem.relevance_flags TEXT column. Both the main-queue dup
    splitter and the Possible Duplicates page skip items carrying this marker."""
    raw = session.query(RawItem).filter_by(id=item_id).first()
    if raw:
        flags = raw.relevance_flags or ""
        if DEDUP_KEEP_MARKER not in flags:
            raw.relevance_flags = (flags + "," + DEDUP_KEEP_MARKER).lstrip(",")
            session.commit()
            background_tasks.add_task(sync_turso)
    return RedirectResponse(url="/possible-duplicates", status_code=303)


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
    request: Request,
    background_tasks: BackgroundTasks,
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
    phases = _Phases()
    # Check if already in master
    existing = session.query(MasterItem).filter_by(item_id=item_id).first()
    phases.mark("lookup")

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

        phases.mark("build")

        # Parse investors and create links
        _sync_investor_links(session, master)
        phases.mark("investors")

        # Auto-reject duplicate articles about the same company within 7 days
        accepted_raw = session.query(RawItem).filter_by(id=item_id).first()
        accepted_company = company.strip().lower() if company else None
        if accepted_company and accepted_raw and accepted_raw.published_date:
            from sqlalchemy import func as sa_func

            window_start = accepted_raw.published_date - timedelta(days=7)
            window_end = accepted_raw.published_date + timedelta(days=7)
            # Never auto-reject another pass over the SAME article. A roundup
            # split into several deals produces rows that share a company AND
            # a publication date — precisely what this scan treats as a
            # duplicate — so without this, accepting deal 1 would immediately
            # reject deal 2, and rejection has no undo.
            accepted_group = accepted_raw.split_group_id
            # Load candidates with their AIExtraction in one query
            candidates = (
                session.query(RawItem, AIExtraction)
                .join(AIExtraction, AIExtraction.item_id == RawItem.id)
                .filter(
                    RawItem.id != item_id,
                    sa_func.coalesce(RawItem.split_parent_id, RawItem.id) != accepted_group,
                    # An article Sam explicitly marked for splitting is
                    # deliberate work; a company-name heuristic must not
                    # discard it. This is how the first real split was lost —
                    # accepting the same company from another source rejected
                    # the roundup that was mid-split.
                    RawItem.split_instruction == None,
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

        phases.mark("autoreject_scan")

        session.commit()
        phases.mark("commit")
        # Deliberately NOT sync_turso() — see mark_dirty()
        mark_dirty()

    phases.record("accept")
    return _triage_action_response(request, phases)


@app.post("/reject/{item_id}")
async def reject_item(item_id: int, request: Request, background_tasks: BackgroundTasks, rejection_reason: str = Form(default=None), session=Depends(get_db)):
    """Reject item and remove from triage queue."""
    phases = _Phases()
    existing = session.query(RejectedItem).filter_by(item_id=item_id).first()
    phases.mark("lookup")

    if not existing:
        rejected = RejectedItem(item_id=item_id, rejection_reason=rejection_reason)
        session.add(rejected)
        session.commit()
        phases.mark("commit")
        mark_dirty()

    phases.record("reject")
    return _triage_action_response(request, phases)


@app.get("/master", response_class=HTMLResponse)
async def master_list(request: Request, session=Depends(get_db)):
    """View master list of accepted items."""
    sync_if_stale()

    master_items = active_master(session).join(
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


@app.get("/duplicates", response_class=HTMLResponse)
async def duplicates(request: Request, session=Depends(get_db)):
    """Duplicate-deal report over the master list, with in-place removal.

    Surfaces deals that look like the same underlying event (same company +
    matching amount within a time window). Each flagged row can be removed
    right here via POST /master/{id}/remove — previously the only action was
    an Edit link that bounced to /master with no way back to the row, and no
    delete existed at all. Matching logic and thresholds live in
    src/utils/dedup.py (shared with the CLI script).

    Within each cluster, entries are ranked best-source-first by the same
    _source_sort_key the triage dedup UI uses, so the top row is a real
    "keep this one" recommendation rather than just the oldest item.
    """
    from src.utils import dedup
    sync_if_stale()

    # RawItem is joined only for split_parent_id — see _queue_dup_flagged_ids.
    rows = (active_master(session)
            .join(RawItem, MasterItem.item_id == RawItem.id)
            .add_columns(RawItem.split_parent_id)
            .all())
    deals = [{
        'id': r.id,
        'company': r.company or r.title,
        'amount': r.investment_amount,
        'date': r.curated_at or r.published_at,
        'title': r.title or r.company,
        'source': r.source_url,
        'group_key': f"art:{split_parent_id or r.item_id}",
    } for r, split_parent_id in rows]

    result = dedup.find_clusters(deals)

    # Pre-format for the template (Jinja can't call our helpers easily)
    for bucket in (result['likely'], result['distinct']):
        for cluster in bucket:
            cluster['entries'].sort(key=dedup._source_sort_key)
            for i, d in enumerate(cluster['entries']):
                d['amount_fmt'] = dedup.fmt_amount(d['amount_num'])
                d['date_fmt'] = d['date'].strftime('%Y-%m-%d') if d['date'] else '—'
                d['is_flagged'] = d['id'] in cluster['flagged_ids']
                # Best-ranked entry in a genuine dup cluster is the keeper
                d['is_keeper'] = (i == 0 and bool(cluster['flagged_ids']))

    removed_count = session.query(MasterItem).filter(
        MasterItem.removed_at.isnot(None)
    ).count()

    return templates.TemplateResponse("duplicates.html", {
        "request": request,
        "likely": result['likely'],
        "distinct": result['distinct'],
        "overcount_fmt": dedup.fmt_amount(result['overcount']),
        "scanned": len(deals),
        "removed_count": removed_count,
        "window_days": dedup.WINDOW_DAYS,
        "tolerance_pct": int(dedup.AMOUNT_TOLERANCE * 100),
    })


@app.post("/master/{master_id}/remove")
async def remove_master_item(master_id: int, request: Request,
                             reason: str = Form(default="duplicate"),
                             session=Depends(get_db)):
    """Soft-delete a published deal (default use: a duplicate).

    Sets removed_at rather than deleting the row. Dedup matching is a
    heuristic — 5% amount tolerance over a 30-day window will occasionally
    flag two genuinely separate raises — so removal has to be reversible.
    Undo lives at /removed.
    """
    master = session.query(MasterItem).filter_by(id=master_id).first()
    if not master:
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    if master.removed_at is None:
        master.removed_at = datetime.utcnow()
        master.removed_reason = reason or "duplicate"
        session.commit()
        # Clearing a dup cluster means many clicks in a row — keep the sync
        # off the click path, same as accept/reject. See mark_dirty().
        mark_dirty()

    # The report page removes the row client-side; a plain form gets a redirect.
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return Response(status_code=204)
    return RedirectResponse(url="/duplicates", status_code=303)


@app.post("/master/{master_id}/restore")
async def restore_master_item(master_id: int, session=Depends(get_db)):
    """Undo a soft delete, putting the deal back on the dashboard."""
    master = session.query(MasterItem).filter_by(id=master_id).first()
    if not master:
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    master.removed_at = None
    master.removed_reason = None
    session.commit()
    mark_dirty()   # next page render syncs; see mark_dirty()
    return RedirectResponse(url="/removed", status_code=303)


@app.get("/removed", response_class=HTMLResponse)
async def removed_list(request: Request, session=Depends(get_db)):
    """Deals soft-deleted from the dashboard, newest first, with Restore."""
    sync_if_stale()
    items = session.query(MasterItem).filter(
        MasterItem.removed_at.isnot(None)
    ).order_by(MasterItem.removed_at.desc()).all()

    return templates.TemplateResponse("removed.html", {
        "request": request,
        "items": items,
    })


@app.get("/rejected", response_class=HTMLResponse)
async def rejected_list(request: Request, session=Depends(get_db)):
    """View rejected items."""
    sync_if_stale()

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

    sync_if_stale()

    total_raw = session.query(RawItem).count()
    total_scraped = session.query(ArticleContent).filter_by(scrape_success=True).count()
    total_master = active_master(session).count()

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

    sync_if_stale()

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
    sync_if_stale()

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
    # Only pay for the DELETE when there is something to delete. On accept the
    # master row was created moments ago and never has links, so this was a
    # wasted network round trip on every single accept. Reads come from the
    # local replica and are cheap; writes go to the Turso primary and cost
    # ~0.8s each in production.
    if old_links:
        session.query(DealInvestor).filter_by(master_item_id=master.id).delete()

    if not master.investors:
        # Update counts for removed investors only
        _update_investor_deal_counts(session, affected_investor_ids)
        return

    parsed = parse_investors(master.investors)
    now = datetime.utcnow()

    # Resolve every investor first, then flush ONCE. Flushing inside the loop
    # made SQLAlchemy emit a separate INSERT per investor interleaved with a
    # separate INSERT per link — six round trips for three investors. Batching
    # lets it use executemany: one INSERT for the new investors, one for the
    # links. Looking them up in a single IN query replaces N SELECTs too.
    wanted = [(slugify(name), name, is_lead) for name, is_lead in parsed]
    by_slug = {}
    if wanted:
        for inv in session.query(Investor).filter(
                Investor.slug.in_([s for s, _, _ in wanted])).all():
            by_slug[inv.slug] = inv

    from sqlalchemy import insert

    new_rows, pending_new = [], set()
    for slug, name, is_lead in wanted:
        investor = by_slug.get(slug)
        if investor is None:
            if slug not in pending_new:
                new_rows.append({"name": name, "slug": slug, "deal_count": 0,
                                 "first_seen": now, "last_seen": now})
                pending_new.add(slug)
        elif investor.last_seen is None or now > investor.last_seen:
            investor.last_seen = now

    # Insert new investors as one executemany, then read their ids back.
    # session.add() per investor needs RETURNING id, which forces a statement
    # each. Trading N writes for one extra read is strongly favourable here:
    # reads hit the local replica, writes go over the network to the Turso
    # primary at roughly 0.8s apiece.
    if new_rows:
        session.execute(insert(Investor), new_rows)
        for inv in session.query(Investor).filter(
                Investor.slug.in_(list(pending_new))).all():
            by_slug[inv.slug] = inv

    resolved = [(by_slug[slug], is_lead) for slug, _, is_lead in wanted
                if by_slug.get(slug) is not None]

    # Core insert rather than session.add() per link: the ORM path appends
    # RETURNING id to each row, which forces one statement per link even
    # though nothing ever reads those ids back. A values list is a single
    # executemany — one round trip instead of one per investor.
    if resolved:
        from sqlalchemy import insert
        rows = []
        for investor, is_lead in resolved:
            affected_investor_ids.add(investor.id)
            rows.append({
                "master_item_id": master.id,
                "investor_id": investor.id,
                "is_lead": is_lead,
            })
        session.execute(insert(DealInvestor), rows)

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
    mark_dirty()   # next page render syncs; see mark_dirty()

    return RedirectResponse(url="/master", status_code=303)


@app.get("/investors", response_class=HTMLResponse)
async def investors_list(request: Request, session=Depends(get_db)):
    """View all investors sorted by deal count."""
    sync_if_stale()

    investors = session.query(Investor).order_by(
        Investor.deal_count.desc(),
        Investor.name.asc()
    ).all()

    total_investors = len(investors)
    total_with_investors = active_master(session).filter(
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
    sync_if_stale()

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
    """Parse investment amount string to a USD float for aggregation.

    Delegates to the shared dedup.parse_amount so currency conversion (non-USD
    -> USD via fixed rates) and parsing logic live in ONE place. Kept as a thin
    wrapper so existing call sites are unchanged.
    """
    from src.utils.dedup import parse_amount
    return parse_amount(amount_str)


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
    items = active_master(session).filter(
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
    all_items = active_master(session).filter(
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


@app.get("/map", response_class=HTMLResponse)
async def map_view(request: Request, session=Depends(get_db)):
    """Interactive map of geocoded master list deals."""
    sync_if_stale()
    items = active_master(session).filter(
        MasterItem.latitude != None
    ).order_by(MasterItem.curated_at.desc()).all()

    features = []
    for item in items:
        raw = item.raw_item
        features.append({
            "lat": item.latitude,
            "lng": item.longitude,
            "company": item.company or "",
            "title": item.title or "",
            "amount": item.investment_amount or "",
            "district": item.congressional_district or "",
            "location": item.location or "",
            "sectors": item.sectors or "",
            "url": item.source_url or (raw.url if raw else ""),
        })

    return templates.TemplateResponse("map.html", {
        "request": request,
        "features_json": json.dumps(features),
        "count": len(features),
    })


# =============================================================================
# IST Demo App Dispatcher (by Host header + fallback path)
# =============================================================================

from starlette.applications import Starlette
from starlette.routing import Host, Mount
from src.web.ist import ist_app

# Dispatch by host or path:
# - thinktankpreview.capitalfordefense.com → ist_app
# - /thinktank/* (local dev) → ist_app
# - everything else → triage app (default)
application = Starlette(
    routes=[
        Host("thinktankpreview.capitalfordefense.com", app=ist_app),
        Mount("/thinktank", app=ist_app),
        Mount("/", app=app),
    ]
)


if __name__ == "__main__":
    import uvicorn

    # Change to project root
    os.chdir(Path(__file__).parent.parent.parent)

    uvicorn.run(app, host="127.0.0.1", port=8000)
