import os
from dotenv import load_dotenv

load_dotenv("/app/.env")

DATA_DIR = os.getenv("DATA_DIR", "/data")
USERS_FILE = os.getenv("USERS_FILE", "/app/.users")
SECRET_KEY = os.getenv("SECRET_KEY", "landscape-planner-change-me-2024")

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]

PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY", "")
PLANT_ID_URL = "https://api.plant.id/v3/identification"

# PlantNet — free 500 queries/day, sign up at https://my.plantnet.org
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY", "")

# Which provider to use: "plantnet" (default, free) or "plantid"
PLANT_ID_PROVIDER = os.getenv("PLANT_ID_PROVIDER", "plantnet")

# Trefle — free plant database, sign up at https://trefle.io
TREFLE_API_KEY = os.getenv("TREFLE_API_KEY", "")

UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
CANVAS_STATE_FILE = os.path.join(DATA_DIR, "canvas_state.json")
GOOGLE_TOKENS_DIR = os.path.join(DATA_DIR, "google_tokens")
DATABASE_URL = f"sqlite:///{DATA_DIR}/plants.db"
