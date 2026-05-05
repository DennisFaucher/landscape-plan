from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import app_settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_MESSAGES = {
    "google_not_configured": "Configure your Google OAuth credentials below to enable Google Photos import.",
    "saved": "Settings saved.",
}


@router.get("/settings")
def settings_page(request: Request, msg: str = ""):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "google_client_id": app_settings.google_client_id(),
            "google_client_secret": app_settings.google_client_secret(),
            "google_configured": app_settings.google_configured(),
            "message": _MESSAGES.get(msg, ""),
        },
    )


@router.post("/settings")
async def save_settings(
    request: Request,
    google_client_id: str = Form(""),
    google_client_secret: str = Form(""),
):
    app_settings.save(
        {
            "google_client_id": google_client_id.strip(),
            "google_client_secret": google_client_secret.strip(),
        }
    )
    return RedirectResponse(url="/settings?msg=saved", status_code=303)
