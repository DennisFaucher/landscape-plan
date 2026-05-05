import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from database import init_db
from auth import authenticate_user, create_access_token, get_current_user, SECRET_KEY, ALGORITHM
from routers import plants, canvas, google_photos
from config import DATA_DIR
from jinja import get_templates

app = FastAPI(title="Landscape Planner")


class AuthMiddleware(BaseHTTPMiddleware):
    EXEMPT = {"/login", "/favicon.ico"}
    EXEMPT_PREFIXES = ("/static", "/data")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.EXEMPT or any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/login")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if not payload.get("sub"):
                return RedirectResponse(url="/login")
            request.state.username = payload["sub"]
        except JWTError:
            return RedirectResponse(url="/login")

        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.on_event("startup")
def startup():
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "thumbnails"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "temp"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "google_tokens"), exist_ok=True)
    init_db()


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

templates = get_templates()

app.include_router(plants.router)
app.include_router(canvas.router)
app.include_router(google_photos.router)


@app.get("/")
def root():
    return RedirectResponse(url="/plants")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))

    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password",
        }, status_code=401)

    token = create_access_token(username)
    response = RedirectResponse(url="/plants", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=86400 * 7)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response
