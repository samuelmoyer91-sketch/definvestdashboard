"""FastAPI web application for triage and dashboard."""

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, MasterItem, RejectedItem, get_session

app = FastAPI(title="Defense Capital Tracker")


# =============================================================================
# Health & API Endpoints for Cloud Deployment
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway/container orchestration."""
    try:
        session = get_session()
        # Quick DB connectivity test
        session.execute("SELECT 1")
        session.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/api/action")
async def email_action(request: Request, token: str = Query(...)):
    """Handle approve/reject actions from email links.

    Token format: {item_id}:{action}:{timestamp}:{signature}
    """
    from src.notifications.email_sender import verify_action_token

    valid, item_id, action, error = verify_action_token(token)

    if not valid:
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Action Failed</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#f44336;">❌ Action Failed</h1>
                <p>{error or 'Invalid token'}</p>
                <p><a href="/">Return to triage interface</a></p>
            </body>
            </html>
            """,
            status_code=400
        )

    session = get_session()

    try:
        # Check item exists
        item = session.query(RawItem).filter_by(id=item_id).first()
        if not item:
            return HTMLResponse(
                content="""
                <html>
                <head><title>Item Not Found</title></head>
                <body style="font-family:sans-serif;text-align:center;padding:50px;">
                    <h1 style="color:#ff9800;">⚠️ Item Not Found</h1>
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

            return HTMLResponse(
                content=f"""
                <html>
                <head><title>Approved</title></head>
                <body style="font-family:sans-serif;text-align:center;padding:50px;">
                    <h1 style="color:#4caf50;">✅ Approved</h1>
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

            return HTMLResponse(
                content=f"""
                <html>
                <head><title>Rejected</title></head>
                <body style="font-family:sans-serif;text-align:center;padding:50px;">
                    <h1 style="color:#f44336;">❌ Rejected</h1>
                    <p><strong>{item.title[:80]}...</strong></p>
                    <p>Removed from triage queue.</p>
                    <p><a href="/">Return to triage</a></p>
                </body>
                </html>
                """
            )

    finally:
        session.close()


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
        print(f"Telegram webhook error: {e}")
        return JSONResponse(content={'ok': True})

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page showing triage queue."""
    session = get_session()

    # Get items that:
    # 1. Have been successfully scraped
    # 2. Are not yet in master list
    # 3. Have not been rejected
    items = session.query(RawItem).join(
        ArticleContent, RawItem.id == ArticleContent.item_id
    ).filter(
        ArticleContent.scrape_success == True,
        ~RawItem.id.in_(
            session.query(MasterItem.item_id)
        ),
        ~RawItem.id.in_(
            session.query(RejectedItem.item_id)
        )
    ).order_by(
        RawItem.published_date.desc()
    ).limit(50).all()

    # Add article content and AI extraction to each item
    for item in items:
        item.article_content = session.query(ArticleContent).filter_by(item_id=item.id).first()
        item.ai_extraction = session.query(AIExtraction).filter_by(item_id=item.id).first()

    total_items = len(items)
    master_count = session.query(MasterItem).count()

    session.close()

    return templates.TemplateResponse("triage.html", {
        "request": request,
        "items": items,
        "total_items": total_items,
        "master_count": master_count
    })


@app.get("/item/{item_id}", response_class=HTMLResponse)
async def view_item(request: Request, item_id: int):
    """View full item details."""
    session = get_session()

    item = session.query(RawItem).filter_by(id=item_id).first()
    article = session.query(ArticleContent).filter_by(item_id=item_id).first()
    ai_extraction = session.query(AIExtraction).filter_by(item_id=item_id).first()
    master = session.query(MasterItem).filter_by(item_id=item_id).first()

    session.close()

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
    company: str = Form(""),
    investors: str = Form(""),
    investment_amount: str = Form(""),
    transaction_type: str = Form(""),
    capital_sources: list[str] = Form([]),
    sectors: list[str] = Form([]),
    location: str = Form(""),
    summary: str = Form(""),
    notes: str = Form(""),
    # OLD fields for backward compatibility
    deal_type: str = Form(""),
    capital_type: str = Form(""),
    sector: str = Form(""),
    project_type: str = Form("")
):
    """Accept item and add to master list."""
    session = get_session()

    # Check if already in master
    existing = session.query(MasterItem).filter_by(item_id=item_id).first()

    if not existing:
        master = MasterItem(
            item_id=item_id,
            company=company if company else None,
            investors=investors if investors else None,
            investment_amount=investment_amount if investment_amount else None,
            # NEW fields
            transaction_type=transaction_type if transaction_type else None,
            capital_sources=",".join(capital_sources) if capital_sources else None,
            sectors=",".join(sectors) if sectors else None,
            # OLD fields (for backward compatibility)
            deal_type=deal_type if deal_type else None,
            capital_type=capital_type if capital_type else None,
            sector=sector if sector else None,
            project_type=project_type if project_type else None,
            location=location if location else None,
            summary=summary if summary else None,
            human_notes=notes if notes else None,
            published=False
        )
        session.add(master)
        session.commit()

    session.close()

    return RedirectResponse(url="/", status_code=303)


@app.post("/reject/{item_id}")
async def reject_item(item_id: int):
    """Reject item and remove from triage queue."""
    session = get_session()

    # Check if already rejected
    existing = session.query(RejectedItem).filter_by(item_id=item_id).first()

    if not existing:
        rejected = RejectedItem(item_id=item_id)
        session.add(rejected)
        session.commit()

    session.close()

    return RedirectResponse(url="/", status_code=303)


@app.get("/master", response_class=HTMLResponse)
async def master_list(request: Request):
    """View master list of accepted items."""
    from src.database import AIExtraction

    session = get_session()

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

    session.close()

    return templates.TemplateResponse("master.html", {
        "request": request,
        "items": master_items
    })


@app.get("/rejected", response_class=HTMLResponse)
async def rejected_list(request: Request):
    """View rejected items."""
    session = get_session()

    rejected_items = session.query(RejectedItem).join(
        RawItem, RejectedItem.item_id == RawItem.id
    ).order_by(
        RejectedItem.rejected_at.desc()
    ).all()

    # Add raw item data and pipeline status
    for rejected in rejected_items:
        rejected.raw_item = session.query(RawItem).filter_by(id=rejected.item_id).first()
        rejected.article_content = session.query(ArticleContent).filter_by(item_id=rejected.item_id).first()

    session.close()

    return templates.TemplateResponse("rejected.html", {
        "request": request,
        "items": rejected_items
    })


@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    """Show statistics."""
    from sqlalchemy import func

    session = get_session()

    total_raw = session.query(RawItem).count()
    total_scraped = session.query(ArticleContent).filter_by(scrape_success=True).count()
    total_master = session.query(MasterItem).count()

    feed_counts = session.query(
        RawItem.feed_source,
        func.count(RawItem.id)
    ).group_by(RawItem.feed_source).all()

    session.close()

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "total_raw": total_raw,
        "total_scraped": total_scraped,
        "total_master": total_master,
        "feed_counts": feed_counts
    })




if __name__ == "__main__":
    import uvicorn
    import os

    # Change to project root
    os.chdir(Path(__file__).parent.parent.parent)

    uvicorn.run(app, host="127.0.0.1", port=8000)
