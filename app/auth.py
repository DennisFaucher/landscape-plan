from fastapi import Request
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from config import USERS_FILE, SECRET_KEY

ALGORITHM = "HS256"


def load_users() -> dict:
    users = {}
    try:
        with open(USERS_FILE) as f:
            for line in f:
                line = line.strip()
                if line and ":" in line:
                    username, password = line.split(":", 1)
                    users[username.strip()] = password.strip()
    except FileNotFoundError:
        pass
    return users


def authenticate_user(username: str, password: str):
    users = load_users()
    stored = users.get(username)
    if stored is None:
        return None
    if password == stored:
        return username
    return None


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
