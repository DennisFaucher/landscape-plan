import os
import uuid
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from PIL import Image

from database import get_db
from models import Plant
from plant_id import identify_plant
from config import UPLOADS_DIR, THUMBNAILS_DIR, TEMP_DIR
from jinja import get_templates

router    = APIRouter()
templates = get_templates()

THUMB_SIZE = (150, 150)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_thumbnail(src: str, dst: str):
    with Image.open(src) as img:
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        img.save(dst, "JPEG", quality=85)


def _ensure_dirs():
    for d in (UPLOADS_DIR, THUMBNAILS_DIR, TEMP_DIR):
        os.makedirs(d, exist_ok=True)


def _safe_int(v):
    try:
        return int(v) if v not in (None, "", "None", "null") else None
    except Exception:
        return None


def _safe_float(v):
    try:
        return float(v) if v not in (None, "", "None", "null") else None
    except Exception:
        return None


def _safe_bool(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("true", "1", "yes", "on")


def _parse_array(v: str) -> str:
    """Normalize a value to a JSON array string.
    Accepts either an existing JSON array or a comma-separated string."""
    if not v or str(v).strip() in ("", "[]", "null"):
        return "[]"
    v = str(v).strip()
    if v.startswith("["):
        try:
            return json.dumps(json.loads(v))
        except Exception:
            pass
    items = [x.strip() for x in v.split(",") if x.strip()]
    return json.dumps(items)


def _parse_json_obj(v: str, default="[]") -> str:
    """Keep a JSON value as-is, or return default."""
    if not v or str(v).strip() in ("", "null"):
        return default
    try:
        json.loads(v)
        return v
    except Exception:
        return default


def _plant_kwargs(form) -> dict:
    """Extract all Plant fields from a form multidict."""
    return dict(
        common_name=form.get("common_name", ""),
        scientific_name=form.get("scientific_name", ""),
        trefle_id=_safe_int(form.get("trefle_id")),
        trefle_slug=form.get("trefle_slug", ""),
        family=form.get("family", ""),
        family_common_name=form.get("family_common_name", ""),
        genus=form.get("genus", ""),
        year=_safe_int(form.get("year")),
        author=form.get("author", ""),
        bibliography=form.get("bibliography", ""),
        status=form.get("status", ""),
        rank=form.get("rank", ""),
        duration=_parse_array(form.get("duration", "")),
        edible=_safe_bool(form.get("edible")),
        edible_part=_parse_array(form.get("edible_part", "")),
        vegetable=_safe_bool(form.get("vegetable")),
        observations=form.get("observations", ""),
        trefle_image_url=form.get("trefle_image_url", ""),
        synonyms=form.get("synonyms", ""),
        image_flower=form.get("image_flower", ""),
        image_leaf=form.get("image_leaf", ""),
        image_habit=form.get("image_habit", ""),
        image_fruit=form.get("image_fruit", ""),
        image_bark=form.get("image_bark", ""),
        image_other=form.get("image_other", ""),
        distribution_native=_parse_json_obj(form.get("distribution_native"), "[]"),
        flower_color=_parse_array(form.get("flower_color", "")),
        flower_conspicuous=_safe_bool(form.get("flower_conspicuous")),
        foliage_texture=form.get("foliage_texture", ""),
        foliage_color=_parse_array(form.get("foliage_color", "")),
        leaf_retention=_safe_bool(form.get("leaf_retention")),
        fruit_conspicuous=_safe_bool(form.get("fruit_conspicuous")),
        fruit_color=_parse_array(form.get("fruit_color", "")),
        fruit_shape=form.get("fruit_shape", ""),
        seed_persistence=_safe_bool(form.get("seed_persistence")),
        ligneous_type=form.get("ligneous_type", ""),
        growth_form=form.get("growth_form", ""),
        growth_habit=form.get("growth_habit", ""),
        growth_rate=form.get("growth_rate", ""),
        average_height_cm=_safe_int(form.get("average_height_cm")),
        maximum_height_cm=_safe_int(form.get("maximum_height_cm")),
        nitrogen_fixation=form.get("nitrogen_fixation", ""),
        shape_and_orientation=form.get("shape_and_orientation", ""),
        toxicity=form.get("toxicity", ""),
        description=form.get("description", ""),
        sowing=form.get("sowing", ""),
        days_to_harvest=_safe_int(form.get("days_to_harvest")),
        ph_minimum=_safe_float(form.get("ph_minimum")),
        ph_maximum=_safe_float(form.get("ph_maximum")),
        light=_safe_int(form.get("light")),
        atmospheric_humidity=_safe_int(form.get("atmospheric_humidity")),
        growth_months=_parse_array(form.get("growth_months", "")),
        bloom_months=_parse_array(form.get("bloom_months", "")),
        fruit_months=_parse_array(form.get("fruit_months", "")),
        row_spacing_cm=_safe_int(form.get("row_spacing_cm")),
        spread_cm=_safe_int(form.get("spread_cm")),
        minimum_precipitation_mm=_safe_int(form.get("minimum_precipitation_mm")),
        maximum_precipitation_mm=_safe_int(form.get("maximum_precipitation_mm")),
        minimum_root_depth_cm=_safe_int(form.get("minimum_root_depth_cm")),
        minimum_temperature_deg_c=_safe_float(form.get("minimum_temperature_deg_c")),
        maximum_temperature_deg_c=_safe_float(form.get("maximum_temperature_deg_c")),
        soil_nutriments=_safe_int(form.get("soil_nutriments")),
        soil_salinity=_safe_int(form.get("soil_salinity")),
        soil_texture=_safe_int(form.get("soil_texture")),
        soil_humidity=_safe_int(form.get("soil_humidity")),
        notes=form.get("notes", ""),
    )


def _save_image(file) -> tuple[str, str]:
    """Save an uploaded file; return (image_path, thumbnail_path)."""
    _ensure_dirs()
    final_name = f"{uuid.uuid4()}.jpg"
    final_path = os.path.join(UPLOADS_DIR, final_name)
    thumb_path = os.path.join(THUMBNAILS_DIR, final_name)

    with open(final_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    with Image.open(final_path) as img:
        img.convert("RGB").save(final_path, "JPEG", quality=90)
    _make_thumbnail(final_path, thumb_path)
    return f"/data/uploads/{final_name}", f"/data/thumbnails/{final_name}"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/plants")
def plants_list(request: Request, db: Session = Depends(get_db)):
    plants = db.query(Plant).order_by(Plant.common_name).all()
    return templates.TemplateResponse("plants/list.html", {
        "request": request, "plants": plants,
    })


@router.get("/plants/upload")
def upload_page(request: Request):
    return templates.TemplateResponse("plants/upload.html", {"request": request})


@router.post("/plants/upload")
async def upload_image(request: Request, file: UploadFile = File(...)):
    _ensure_dirs()
    temp_id  = str(uuid.uuid4())
    ext      = Path(file.filename).suffix.lower() or ".jpg"
    temp_path = os.path.join(TEMP_DIR, f"{temp_id}{ext}")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    if ext not in (".jpg", ".jpeg"):
        with Image.open(temp_path) as img:
            jpg = os.path.join(TEMP_DIR, f"{temp_id}.jpg")
            img.convert("RGB").save(jpg, "JPEG", quality=90)
            os.remove(temp_path)
    return RedirectResponse(url=f"/plants/crop/{temp_id}", status_code=303)


@router.get("/plants/crop/{temp_id}")
def crop_page(request: Request, temp_id: str):
    temp_file = _find_temp(temp_id)
    if not temp_file:
        raise HTTPException(404, "Temporary image not found")
    return templates.TemplateResponse("plants/crop.html", {
        "request": request,
        "temp_id": temp_id,
        "temp_url": f"/data/temp/{Path(temp_file).name}",
    })


@router.post("/plants/crop/{temp_id}")
async def save_crop(request: Request, temp_id: str):
    form = await request.form()
    temp_file = _find_temp(temp_id)
    if not temp_file:
        raise HTTPException(404, "Temporary image not found")
    x, y = float(form.get("x", 0)), float(form.get("y", 0))
    w, h = float(form.get("width", 0)), float(form.get("height", 0))
    with Image.open(temp_file) as img:
        img.crop((int(x), int(y), int(x + w), int(y + h))).convert("RGB").save(
            temp_file, "JPEG", quality=90
        )
    return RedirectResponse(url=f"/plants/identify/{temp_id}", status_code=303)


@router.get("/plants/identify/{temp_id}")
async def identify_page(request: Request, temp_id: str):
    temp_file = _find_temp(temp_id)
    if not temp_file:
        raise HTTPException(404, "Temporary image not found")
    result      = await identify_plant(temp_file)
    suggestions = result.get("suggestions", [])
    return templates.TemplateResponse("plants/identify.html", {
        "request":     request,
        "temp_id":     temp_id,
        "temp_url":    f"/data/temp/{Path(temp_file).name}",
        "suggestions": suggestions,
        "error":       result.get("error"),
    })


@router.post("/plants/identify/{temp_id}")
async def confirm_plant(request: Request, temp_id: str, db: Session = Depends(get_db)):
    temp_file = _find_temp(temp_id)
    if not temp_file:
        raise HTTPException(404, "Temporary image not found")
    form   = await request.form()
    kwargs = _plant_kwargs(form)

    _ensure_dirs()
    final_name = f"{uuid.uuid4()}.jpg"
    final_path = os.path.join(UPLOADS_DIR, final_name)
    thumb_path = os.path.join(THUMBNAILS_DIR, final_name)
    shutil.move(temp_file, final_path)
    _make_thumbnail(final_path, thumb_path)
    kwargs["image_path"]     = f"/data/uploads/{final_name}"
    kwargs["thumbnail_path"] = f"/data/thumbnails/{final_name}"

    plant = Plant(**kwargs)
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return RedirectResponse(url=f"/plants/{plant.id}", status_code=303)


@router.get("/plants/new")
def new_plant_form(request: Request):
    return templates.TemplateResponse("plants/detail.html", {
        "request": request, "plant": None, "action": "/plants/new",
    })


@router.post("/plants/new")
async def create_plant_manual(request: Request, db: Session = Depends(get_db)):
    form   = await request.form()
    kwargs = _plant_kwargs(form)
    file   = form.get("file")
    if file and hasattr(file, "filename") and file.filename:
        kwargs["image_path"], kwargs["thumbnail_path"] = _save_image(file)
    plant = Plant(**kwargs)
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return RedirectResponse(url=f"/plants/{plant.id}", status_code=303)


@router.get("/plants/{plant_id}")
def plant_detail(request: Request, plant_id: int, db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if not plant:
        raise HTTPException(404, "Plant not found")
    return templates.TemplateResponse("plants/detail.html", {
        "request": request, "plant": plant, "action": f"/plants/{plant_id}",
    })


@router.post("/plants/{plant_id}")
async def update_plant(request: Request, plant_id: int, db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if not plant:
        raise HTTPException(404, "Plant not found")
    form   = await request.form()
    kwargs = _plant_kwargs(form)
    file   = form.get("file")
    if file and hasattr(file, "filename") and file.filename:
        kwargs["image_path"], kwargs["thumbnail_path"] = _save_image(file)
    else:
        kwargs["image_path"]     = plant.image_path
        kwargs["thumbnail_path"] = plant.thumbnail_path
    for k, v in kwargs.items():
        setattr(plant, k, v)
    db.commit()
    return RedirectResponse(url=f"/plants/{plant_id}", status_code=303)


@router.post("/plants/{plant_id}/delete")
def delete_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if not plant:
        raise HTTPException(404, "Plant not found")
    db.delete(plant)
    db.commit()
    return RedirectResponse(url="/plants", status_code=303)


@router.get("/api/plants")
def api_plants(db: Session = Depends(get_db)):
    plants = db.query(Plant).order_by(Plant.common_name).all()
    return [
        {
            "id":             p.id,
            "common_name":    p.common_name,
            "scientific_name": p.scientific_name,
            "thumbnail_path": p.thumbnail_path,
            "image_path":     p.image_path,
        }
        for p in plants
    ]


def _find_temp(temp_id: str) -> str | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = os.path.join(TEMP_DIR, f"{temp_id}{ext}")
        if os.path.exists(path):
            return path
    return None
