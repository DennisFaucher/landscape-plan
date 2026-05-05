"""
Runtime settings stored in /data/settings.json.
Values here override .env for credentials that the user configures through the UI.
"""
import json
import os
from config import DATA_DIR

_SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


def load() -> dict:
    try:
        with open(_SETTINGS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    current = load()
    current.update(data)
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)


def get(key: str, default: str = "") -> str:
    return load().get(key, default)


def google_client_id() -> str:
    return get("google_client_id")


def google_client_secret() -> str:
    return get("google_client_secret")


def google_configured() -> bool:
    return bool(google_client_id() and google_client_secret())
