import json
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from config import CANVAS_STATE_FILE
from jinja import get_templates

router    = APIRouter()
templates = get_templates()


@router.get("/canvas")
def canvas_page(request: Request):
    return templates.TemplateResponse("canvas/index.html", {"request": request})


@router.get("/api/canvas/state")
def get_canvas_state():
    if os.path.exists(CANVAS_STATE_FILE):
        with open(CANVAS_STATE_FILE) as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content={"objects": [], "background": ""})


@router.post("/api/canvas/state")
async def save_canvas_state(request: Request):
    body = await request.json()
    os.makedirs(os.path.dirname(CANVAS_STATE_FILE), exist_ok=True)
    with open(CANVAS_STATE_FILE, "w") as f:
        json.dump(body, f)
    return JSONResponse(content={"status": "saved"})
