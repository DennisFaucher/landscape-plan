"""
Plant identification + enrichment pipeline.

Step 1 — Identify:  PlantNet (default) or Plant.id
Step 2 — Enrich:   Trefle.io (structured botanical database, free API token required)
"""

import json
import base64
import asyncio
import httpx
from config import (
    PLANT_ID_API_KEY, PLANT_ID_URL,
    PLANTNET_API_KEY, PLANT_ID_PROVIDER,
    TREFLE_API_KEY,
)

_TREFLE_BASE = "https://trefle.io/api/v1"


def _str(val) -> str:
    """Safely extract a plain string from a value that might be an object or list."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("name") or val.get("title") or str(val)
    if isinstance(val, list):
        return ", ".join(_str(x) for x in val)
    return str(val)


def _first_url(images_list: list) -> str:
    for img in (images_list or []):
        url = img.get("image_url") or img.get("url") or ""
        if url:
            return url
    return ""


def _cm(obj):
    return (obj or {}).get("cm")


def _mm(obj):
    return (obj or {}).get("mm")


def _deg_c(obj):
    return (obj or {}).get("deg_c")


def _jlist(val) -> str:
    return json.dumps(val) if val else "[]"


async def _fetch_trefle(scientific_name: str) -> dict:
    """Return a flat dict of all Trefle fields, or {} on failure / no key."""
    if not TREFLE_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{_TREFLE_BASE}/plants/search",
                params={"q": scientific_name, "token": TREFLE_API_KEY},
            )
        if r.status_code != 200:
            return {}
        results = r.json().get("data") or []
        if not results:
            return {}

        slug = results[0].get("slug") or str(results[0].get("id", ""))

        async with httpx.AsyncClient(timeout=10) as client:
            dr = await client.get(
                f"{_TREFLE_BASE}/plants/{slug}",
                params={"token": TREFLE_API_KEY},
            )
        if dr.status_code != 200:
            return {}

        plant   = dr.json().get("data") or {}
        species = plant.get("main_species") or {}
        growth  = species.get("growth") or {}
        specs   = species.get("specifications") or {}
        flower  = species.get("flower") or {}
        foliage = species.get("foliage") or {}
        fruit   = species.get("fruit_or_seed") or {}
        images  = species.get("images") or {}
        dists   = (species.get("distributions") or {})

        synonyms_raw = species.get("synonyms") or []
        synonyms_text = "; ".join(
            s.get("name", "") + (f" ({s['author']})" if s.get("author") else "")
            for s in synonyms_raw if s.get("name")
        )

        native_zones = [z.get("name", "") for z in (dists.get("native") or [])]

        return {
            # ── Core / taxonomy ──────────────────────────────────────────────
            "trefle_id":          plant.get("id"),
            "trefle_slug":        plant.get("slug", ""),
            "common_name":        _str(plant.get("common_name") or species.get("common_name")),
            "scientific_name":    _str(species.get("scientific_name") or plant.get("scientific_name")),
            "family":             _str(plant.get("family") or species.get("family")),
            "family_common_name": _str(plant.get("family_common_name") or species.get("family_common_name")),
            "genus":              _str(plant.get("genus") or species.get("genus")),
            "year":               species.get("year"),
            "author":             species.get("author", ""),
            "bibliography":       species.get("bibliography", ""),
            "status":             species.get("status", ""),
            "rank":               species.get("rank", ""),
            "duration":           _jlist(species.get("duration")),
            "edible":             species.get("edible"),
            "edible_part":        _jlist(species.get("edible_part")),
            "vegetable":          species.get("vegetable"),
            "observations":       (species.get("observations") or "").strip(),
            "trefle_image_url":   plant.get("image_url", ""),
            "synonyms":           synonyms_text,
            # ── Images ───────────────────────────────────────────────────────
            "image_flower": _first_url(images.get("flower")),
            "image_leaf":   _first_url(images.get("leaf")),
            "image_habit":  _first_url(images.get("habit")),
            "image_fruit":  _first_url(images.get("fruit")),
            "image_bark":   _first_url(images.get("bark")),
            "image_other":  _first_url(images.get("other")),
            # ── Distributions ────────────────────────────────────────────────
            "distribution_native": json.dumps(native_zones),
            # ── Flower ───────────────────────────────────────────────────────
            "flower_color":       _jlist(flower.get("color")),
            "flower_conspicuous": flower.get("conspicuous"),
            # ── Foliage ──────────────────────────────────────────────────────
            "foliage_texture": foliage.get("texture", ""),
            "foliage_color":   _jlist(foliage.get("color")),
            "leaf_retention":  foliage.get("leaf_retention"),
            # ── Fruit / Seed ─────────────────────────────────────────────────
            "fruit_conspicuous": fruit.get("conspicuous"),
            "fruit_color":       _jlist(fruit.get("color")),
            "fruit_shape":       fruit.get("shape", ""),
            "seed_persistence":  fruit.get("seed_persistence"),
            # ── Specifications ───────────────────────────────────────────────
            "ligneous_type":        specs.get("ligneous_type", ""),
            "growth_form":          specs.get("growth_form", ""),
            "growth_habit":         specs.get("growth_habit", ""),
            "growth_rate":          specs.get("growth_rate", ""),
            "average_height_cm":    _cm(specs.get("average_height")),
            "maximum_height_cm":    _cm(specs.get("maximum_height")),
            "nitrogen_fixation":    specs.get("nitrogen_fixation", ""),
            "shape_and_orientation": specs.get("shape_and_orientation", ""),
            "toxicity":             specs.get("toxicity", ""),
            # ── Growth ───────────────────────────────────────────────────────
            "description":               (growth.get("description") or "").strip(),
            "sowing":                    (growth.get("sowing") or "").strip(),
            "days_to_harvest":           growth.get("days_to_harvest"),
            "ph_minimum":                growth.get("ph_minimum"),
            "ph_maximum":                growth.get("ph_maximum"),
            "light":                     growth.get("light"),
            "atmospheric_humidity":      growth.get("atmospheric_humidity"),
            "growth_months":             _jlist(growth.get("growth_months")),
            "bloom_months":              _jlist(growth.get("bloom_months")),
            "fruit_months":              _jlist(growth.get("fruit_months")),
            "row_spacing_cm":            _cm(growth.get("row_spacing")),
            "spread_cm":                 _cm(growth.get("spread")),
            "minimum_precipitation_mm":  _mm(growth.get("minimum_precipitation")),
            "maximum_precipitation_mm":  _mm(growth.get("maximum_precipitation")),
            "minimum_root_depth_cm":     _cm(growth.get("minimum_root_depth")),
            "minimum_temperature_deg_c": _deg_c(growth.get("minimum_temperature")),
            "maximum_temperature_deg_c": _deg_c(growth.get("maximum_temperature")),
            "soil_nutriments":           growth.get("soil_nutriments"),
            "soil_salinity":             growth.get("soil_salinity"),
            "soil_texture":              growth.get("soil_texture"),
            "soil_humidity":             growth.get("soil_humidity"),
        }
    except Exception:
        return {}


# ── PlantNet ──────────────────────────────────────────────────────────────────

async def _identify_plantnet(image_path: str) -> dict:
    if not PLANTNET_API_KEY:
        return {"error": "PlantNet API key not set. Add PLANTNET_API_KEY to .env"}

    url = (
        "https://my-api.plantnet.org/v2/identify/all"
        f"?api-key={PLANTNET_API_KEY}&lang=en&include-related-images=true"
    )
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            files={"images": ("plant.jpg", image_bytes, "image/jpeg")},
            data={"organs": ["auto"]},
        )

    if resp.status_code == 200:
        return {"_provider": "plantnet", **resp.json()}
    if resp.status_code == 404:
        return {"error": "No plant match found. Fill in the details manually."}
    return {"error": f"PlantNet API error {resp.status_code}: {resp.text[:200]}"}


async def _extract_plantnet(raw: dict) -> list[dict]:
    results  = (raw.get("results") or [])[:5]
    tasks    = []
    entries  = []

    for r in results:
        species         = r.get("species") or {}
        scientific_name = species.get("scientificNameWithoutAuthor", "")
        common_names    = species.get("commonNames") or []
        similar = []
        for img in (r.get("images") or [])[:2]:
            u       = img.get("url", "")
            url_str = u.get("m") or u.get("o") or "" if isinstance(u, dict) else u
            if url_str:
                similar.append(url_str)

        entries.append({
            "scientific_name": scientific_name,
            "common_name":     common_names[0] if common_names else "",
            "probability":     round(r.get("score", 0) * 100, 1),
            "similar_images":  similar,
        })
        tasks.append(_fetch_trefle(scientific_name))

    trefle_data = await asyncio.gather(*tasks)
    suggestions = []
    for entry, trefle in zip(entries, trefle_data):
        merged = {**entry, **trefle}
        # Keep PlantNet name if Trefle returned a different/empty one
        if not merged.get("common_name"):
            merged["common_name"] = entry["common_name"]
        if not merged.get("scientific_name"):
            merged["scientific_name"] = entry["scientific_name"]
        suggestions.append(merged)
    return suggestions


# ── Plant.id ──────────────────────────────────────────────────────────────────

async def _identify_plantid(image_path: str) -> dict:
    if not PLANT_ID_API_KEY:
        return {"error": "Plant.id API key not set. Add PLANT_ID_API_KEY to .env"}

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            PLANT_ID_URL,
            headers={"Api-Key": PLANT_ID_API_KEY, "Content-Type": "application/json"},
            json={
                "images": [image_data],
                "similar_images": True,
                "details": "common_names,taxonomy,description,similar_images",
            },
        )

    if resp.status_code == 200:
        return {"_provider": "plantid", **resp.json()}
    return {"error": f"Plant.id API error {resp.status_code}: {resp.text[:200]}"}


async def _extract_plantid(raw: dict) -> list[dict]:
    results = (raw.get("result", {}).get("classification", {}).get("suggestions") or [])[:5]
    tasks   = []
    entries = []

    for s in results:
        details         = s.get("details") or {}
        common_names    = details.get("common_names") or []
        scientific_name = s.get("name", "")
        similar = [si.get("url") for si in (s.get("similar_images") or [])[:2]]

        entries.append({
            "scientific_name": scientific_name,
            "common_name":     common_names[0] if common_names else "",
            "probability":     round(s.get("probability", 0) * 100, 1),
            "similar_images":  similar,
        })
        tasks.append(_fetch_trefle(scientific_name))

    trefle_data = await asyncio.gather(*tasks)
    suggestions = []
    for entry, trefle in zip(entries, trefle_data):
        merged = {**entry, **trefle}
        if not merged.get("common_name"):
            merged["common_name"] = entry["common_name"]
        if not merged.get("scientific_name"):
            merged["scientific_name"] = entry["scientific_name"]
        suggestions.append(merged)
    return suggestions


# ── Public API ────────────────────────────────────────────────────────────────

async def identify_plant(image_path: str) -> dict:
    provider = PLANT_ID_PROVIDER.lower()
    if provider == "plantid":
        raw = await _identify_plantid(image_path)
        if "error" in raw:
            return raw
        return {"suggestions": await _extract_plantid(raw)}

    raw = await _identify_plantnet(image_path)
    if "error" in raw:
        return raw
    return {"suggestions": await _extract_plantnet(raw)}
