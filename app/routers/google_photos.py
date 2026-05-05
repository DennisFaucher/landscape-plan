import os
import json
import uuid
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from google_auth_oauthlib.flow import Flow
from config import GOOGLE_SCOPES, GOOGLE_TOKENS_DIR, TEMP_DIR
import app_settings
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _tokens_path(username: str) -> str:
    os.makedirs(GOOGLE_TOKENS_DIR, exist_ok=True)
    return os.path.join(GOOGLE_TOKENS_DIR, f"{username}.json")


def _load_tokens(username: str) -> dict | None:
    path = _tokens_path(username)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save_tokens(username: str, token_data: dict):
    with open(_tokens_path(username), "w") as f:
        json.dump(token_data, f)


def _redirect_uri(request: Request) -> str:
    """Auto-detect redirect URI from the incoming request."""
    return str(request.base_url).rstrip("/") + "/auth/google/callback"


def _build_flow(request: Request) -> Flow | None:
    client_id = app_settings.google_client_id()
    client_secret = app_settings.google_client_secret()
    if not client_id or not client_secret:
        return None
    redirect_uri = _redirect_uri(request)
    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri,
    )


@router.get("/auth/google")
def google_auth(request: Request):
    if not app_settings.google_configured():
        return RedirectResponse(url="/settings?msg=google_not_configured")

    flow = _build_flow(request)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    response = RedirectResponse(url=auth_url)
    response.set_cookie("oauth_state", state, httponly=True, max_age=600)
    return response


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
):
    username = get_current_user(request)
    if error or not code:
        return RedirectResponse(url="/plants/upload?google_error=access_denied")

    flow = _build_flow(request)
    if not flow:
        return RedirectResponse(url="/settings?msg=google_not_configured")

    flow.fetch_token(code=code)
    credentials = flow.credentials
    _save_tokens(
        username,
        {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes or []),
        },
    )
    return RedirectResponse(url="/plants/upload?google=connected")


@router.get("/api/google/photos")
async def list_google_photos(request: Request, page_token: str = ""):
    username = get_current_user(request)
    tokens = _load_tokens(username)
    if not tokens:
        return JSONResponse({"error": "not_connected"}, status_code=401)

    params: dict = {"pageSize": 50}
    if page_token:
        params["pageToken"] = page_token

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            "https://photoslibrary.googleapis.com/v1/mediaItems",
            headers={"Authorization": f"Bearer {tokens['token']}"},
            params=params,
        )

    if resp.status_code == 401:
        # Try to refresh the token
        refreshed = await _refresh_token(tokens)
        if refreshed:
            _save_tokens(username, refreshed)
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    "https://photoslibrary.googleapis.com/v1/mediaItems",
                    headers={"Authorization": f"Bearer {refreshed['token']}"},
                    params=params,
                )
        if resp.status_code == 401:
            return JSONResponse({"error": "token_expired"}, status_code=401)

    data = resp.json()
    items = data.get("mediaItems", [])
    photos = [
        {
            "id": item["id"],
            "filename": item.get("filename", ""),
            "baseUrl": item.get("baseUrl", "") + "=w400-h400-c",
            "fullUrl": item.get("baseUrl", "") + "=d",
        }
        for item in items
        if item.get("mimeType", "").startswith("image/")
    ]
    return JSONResponse(
        {"photos": photos, "nextPageToken": data.get("nextPageToken", "")}
    )


@router.post("/api/google/photo/import")
async def import_google_photo(request: Request):
    username = get_current_user(request)
    tokens = _load_tokens(username)
    if not tokens:
        return JSONResponse({"error": "not_connected"}, status_code=401)

    body = await request.json()
    url = body.get("url", "")
    if not url:
        return JSONResponse({"error": "No URL provided"}, status_code=400)

    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_id = str(uuid.uuid4())
    temp_path = os.path.join(TEMP_DIR, f"{temp_id}.jpg")

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(
            url, headers={"Authorization": f"Bearer {tokens['token']}"}
        )

    if resp.status_code != 200:
        return JSONResponse({"error": "Failed to download photo"}, status_code=400)

    with open(temp_path, "wb") as f:
        f.write(resp.content)

    return JSONResponse({"temp_id": temp_id, "redirect": f"/plants/crop/{temp_id}"})


async def _refresh_token(tokens: dict) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
                data={
                    "client_id": tokens.get("client_id", ""),
                    "client_secret": tokens.get("client_secret", ""),
                    "refresh_token": tokens.get("refresh_token", ""),
                    "grant_type": "refresh_token",
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            updated = dict(tokens)
            updated["token"] = data["access_token"]
            return updated
    except Exception:
        pass
    return None
