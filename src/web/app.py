"""FastAPI web application for triage and dashboard."""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, MasterItem, RejectedItem, get_session

app = FastAPI(title="Defense Capital Tracker")

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
