import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .scanner import scan_directories, delete_or_quarantine
# from .security import basic_auth   # <- eliminat

app = FastAPI(title="Dir Cleaner", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ---------- Config prin variabile de mediu ----------
BASE_PATH = Path(os.getenv("BASE_PATH", "/data"))
QUARANTINE_PATH = Path(os.getenv("QUARANTINE_PATH", "/quarantine")) if os.getenv("QUARANTINE_PATH") else None
EXCLUDES = [s.strip() for s in os.getenv("EXCLUDES", "").split(",") if s.strip()]
DEFAULT_SIZE_THRESHOLD_MB = int(os.getenv("SIZE_THRESHOLD_MB", "50"))
DEFAULT_UNUSED_DAYS = int(os.getenv("UNUSED_DAYS", "90"))
DEFAULT_DEPTH = int(os.getenv("SCAN_DEPTH", "1"))
AUDIT_LOG = Path(os.getenv("AUDIT_LOG", "/var/log/dir-cleaner/audit.log"))

# Listă de surse selectabile în UI (virgulă-separate), ex.: /data/movie/,/data/series/
PATH_CHOICES = [s.strip() for s in os.getenv("PATH_CHOICES", str(BASE_PATH)).split(",") if s.strip()]

# ---------- UI ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):  # <- fără auth
    return templates.TemplateResponse("index.html", {
        "request": request,
        "base_path": str(BASE_PATH),
        "defaults": {
            "size_threshold_mb": DEFAULT_SIZE_THRESHOLD_MB,
            "unused_days": DEFAULT_UNUSED_DAYS,
            "depth": DEFAULT_DEPTH,
            "excludes": ",".join(EXCLUDES)
        },
        "path_choices": PATH_CHOICES,
    })

# ---------- API ----------
@app.get("/api/scan")
def api_scan(
    request: Request,
    path: Optional[str] = None,
    size_threshold_mb: Optional[int] = None,
    unused_days: Optional[int] = None,
    depth: Optional[int] = None,
    excludes: Optional[str] = None,
):
    base = Path(path) if path else BASE_PATH
    if not base.exists() or not base.is_dir():
        return JSONResponse({"error": f"Path invalid: {base}"}, status_code=400)

    size_th_mb = size_threshold_mb if size_threshold_mb is not None else DEFAULT_SIZE_THRESHOLD_MB
    size_threshold_bytes = size_th_mb * 1024 * 1024
    u_days = unused_days if unused_days is not None else DEFAULT_UNUSED_DAYS
    d = depth if depth is not None else DEFAULT_DEPTH
    excl = [s.strip() for s in (excludes or ",".join(EXCLUDES)).split(",") if s.strip()]

    results = scan_directories(
        base_path=base,
        excludes=excl,
        size_threshold_bytes=size_threshold_bytes,
        unused_days=u_days,
        depth=d
    )
    return {"items": results, "count": len(results)}

@app.post("/api/delete")
async def api_delete(
    request: Request,
    base_path: str = Form(None),
    action: str = Form(...),           # "quarantine" sau "delete"
    targets: List[str] = Form(...),    # listă de căi relative față de base_path
):
    base = Path(base_path) if base_path else BASE_PATH
    quarantine = QUARANTINE_PATH if action == "quarantine" else None
    resp = delete_or_quarantine(
        base_path=base,
        targets=targets,
        quarantine_path=quarantine,
        audit_log=AUDIT_LOG
    )
    return JSONResponse(resp)