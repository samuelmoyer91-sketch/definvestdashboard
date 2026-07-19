"""IST demo app — FastAPI sub-app with branded login and static assets."""

import os
import secrets
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from src.web.ist_data import PEOPLE, PUBLICATIONS, SPONSORS, FOCUS_AREAS, TAGLINE, MISSION

ist_app = FastAPI(title="IST Demo")

# Session middleware for cookie-based login
secret_key = os.environ.get('IST_SECRET_KEY', 'dev-insecure-key-only')
ist_app.add_middleware(SessionMiddleware, secret_key=secret_key, https_only=False)

# Templates
templates = Jinja2Templates(directory="src/web/templates/ist")

# Static files
ist_app.mount("/static", StaticFiles(directory="src/web/static"), name="static")


# Auth dependency — redirects to login if not authenticated
def require_auth(request: Request):
    """Guard for protected routes — returns None if authed, else raises 307 to /login."""
    if os.environ.get('IST_DEMO_PASSWORD') and not request.session.get('authed'):
        root = request.scope.get('root_path', '')
        raise HTTPException(307, headers={'Location': f'{root}/login'})


# Helper to inject root_path into all template contexts (for dual mounting)
def template_context(request: Request, **kwargs):
    """Inject root_path for link rewriting in templates."""
    ctx = {"request": request, "root": request.scope.get('root_path', '')}
    ctx.update(kwargs)
    return ctx


# Public routes
@ist_app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Branded IST login page."""
    return templates.TemplateResponse("login.html", template_context(request))


@ist_app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    """Verify password and set session."""
    demo_password = os.environ.get('IST_DEMO_PASSWORD')

    # If no password configured (local dev), skip auth
    if not demo_password:
        request.session['authed'] = True
        root = request.scope.get('root_path', '')
        return RedirectResponse(url=f"{root}/", status_code=303)

    # Compare using constant-time function
    if secrets.compare_digest(password, demo_password):
        request.session['authed'] = True
        root = request.scope.get('root_path', '')
        return RedirectResponse(url=f"{root}/", status_code=303)

    # Wrong password — re-render with error
    root = request.scope.get('root_path', '')
    return templates.TemplateResponse(
        "login.html",
        template_context(request, error="Incorrect password"),
        status_code=401
    )


@ist_app.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    root = request.scope.get('root_path', '')
    return RedirectResponse(url=f"{root}/login", status_code=303)


# Protected routes
@ist_app.get("/", response_class=HTMLResponse)
async def home(request: Request, _=Depends(require_auth)):
    """Home page — photo hero, tagline, sponsor strip, featured publications."""
    return templates.TemplateResponse(
        "home.html",
        template_context(request, tagline=TAGLINE, sponsors=SPONSORS, featured=PUBLICATIONS[:3])
    )


@ist_app.get("/publications", response_class=HTMLResponse)
async def publications(request: Request, _=Depends(require_auth)):
    """Filterable publications repository."""
    return templates.TemplateResponse(
        "publications.html",
        template_context(
            request,
            publications=PUBLICATIONS,
            focus_areas=FOCUS_AREAS,
            types=["Report", "Brief", "Insight"],
            topics=list(dict.fromkeys(p["topic"] for p in PUBLICATIONS))
        )
    )


@ist_app.get("/people", response_class=HTMLResponse)
async def people(request: Request, _=Depends(require_auth)):
    """Leadership, Research Fellows, Visiting Scholars."""
    return templates.TemplateResponse(
        "people.html",
        template_context(request, people=PEOPLE)
    )


@ist_app.get("/podcast", response_class=HTMLResponse)
async def podcast(request: Request, _=Depends(require_auth)):
    """Podcast page."""
    return templates.TemplateResponse("podcast.html", template_context(request))


@ist_app.get("/conference", response_class=HTMLResponse)
async def conference(request: Request, _=Depends(require_auth)):
    """Annual flagship conference."""
    return templates.TemplateResponse("conference.html", template_context(request))


@ist_app.get("/about", response_class=HTMLResponse)
async def about(request: Request, _=Depends(require_auth)):
    """Mission, focus areas, sponsors, about IST."""
    return templates.TemplateResponse(
        "about.html",
        template_context(request, mission=MISSION, focus_areas=FOCUS_AREAS, sponsors=SPONSORS)
    )
