"""
Local FastAPI server for the personal streaming site bridge.
Serves JSON metadata, cached posters, and direct .mp4/.mkv file paths.
Runs on http://127.0.0.1:8765 as a background daemon thread.
"""

import json
import socket
import sys
import threading
import os
import secrets
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import COVERS_DIR, LOCAL_API_HOST, LOCAL_API_PORT
from app.config import API_ACCESS_TOKEN
ALLOWED_API_ORIGINS=[value.strip() for value in os.getenv('ALLOWED_API_ORIGINS','').split(',') if value.strip() and value.strip()!='*']

def public_payload(value):
    if isinstance(value,list):return [public_payload(item) for item in value]
    if isinstance(value,dict):return {key:public_payload(item) for key,item in value.items() if key not in ('root_folder_path','season_folder_path','scan_root','user_notes','user_rating','metadata_json')}
    return value

# FastAPI app
api = FastAPI(
    title="Anime Library API",
    description="Personal streaming site bridge for Anime Library & Storage Manager",
    version="1.0.0",
)
# Alias for standard ASGI servers
app = api

# Allow CORS for local streaming site
api.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_API_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Authorization","X-API-Token"],
)

@api.middleware('http')
async def protect_api(request,call_next):
    if LOCAL_API_HOST not in ('127.0.0.1','::1','localhost') and not API_ACCESS_TOKEN:
        return JSONResponse({'detail':'Non-loopback API requires API_ACCESS_TOKEN'},status_code=503)
    origin=request.headers.get('origin')
    local_origin=str(request.base_url).rstrip('/')
    if origin and origin not in [local_origin,*ALLOWED_API_ORIGINS]:
        return JSONResponse({'detail':'Origin is not allowed'},status_code=403)
    if API_ACCESS_TOKEN and request.method!='OPTIONS':
        supplied=request.headers.get('authorization','')
        token=supplied[7:] if supplied.startswith('Bearer ') else request.headers.get('x-api-token','')
        if not secrets.compare_digest(token.encode(),API_ACCESS_TOKEN.encode()):return JSONResponse({'detail':'Authentication required'},status_code=401)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    return response



# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@api.get("/api/library")
async def get_library(
    sort_by: str = Query("display_title", description="Sort field"),
    sort_order: str = Query("ASC", pattern="^(ASC|DESC|asc|desc)$", description="ASC or DESC"),
    search: str = Query("", description="Search query"),
    watch_status: Optional[str] = Query(None),
    storage_state: Optional[str] = Query(None),
):
    """Get all franchises with optional filtering and sorting."""
    franchises = db.get_series_library(
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        watch_status=watch_status,
        storage_state=storage_state,
    )
    # Parse genres for JSON output
    for f in franchises:
        f.pop("metadata_json", None)
        try:
            f["genres"] = json.loads(f.get("genres", "[]"))
        except (json.JSONDecodeError, TypeError):
            f["genres"] = []
    return public_payload(franchises)


@api.get("/api/franchise/{franchise_id}")
async def get_franchise(franchise_id: int):
    """Get a single franchise with its seasons."""
    franchise = franchise_payload(franchise_id)
    if not franchise:
        raise HTTPException(status_code=404, detail="Franchise not found")
    return public_payload(franchise)


def franchise_payload(franchise_id: int):
    """One serializer shared by the API endpoint and desktop JSON inspector."""
    franchise = db.get_series(franchise_id)
    if not franchise:
        return None
    try:
        franchise["genres"] = json.loads(franchise.get("genres") or "[]")
    except (ValueError, TypeError):
        franchise["genres"] = []
    seasons = db.get_series_seasons(franchise_id)
    for season in seasons:
        try:
            season["video_files"] = json.loads(season.get("video_files_json") or "[]")
        except (ValueError, TypeError):
            season["video_files"] = []
    franchise["seasons"] = seasons
    from app.core.library_health import episode_inventory, movie_inventory
    franchise["episode_coverage"] = episode_inventory(seasons)
    try:
        media = json.loads(franchise.get("metadata_json") or "null")
    except (TypeError, ValueError):
        media = None
    franchise["movie_inventory"] = movie_inventory(seasons, media)
    franchise["updates"] = [
        {"title": part.partition(" — ")[0], "status": part.partition(" — ")[2]}
        for part in (franchise.get("update_details") or "").split(" | ") if part.strip()
    ]
    # Provider data has its own source in the inspector; avoid a giant JSON string.
    franchise.pop("metadata_json", None)
    return franchise


@api.get("/api/franchise/{franchise_id}/seasons")
async def get_seasons(franchise_id: int):
    """Get seasons for a franchise."""
    seasons = db.get_seasons_for_franchise(franchise_id)
    for s in seasons:
        try:
            s["video_files"] = json.loads(s.get("video_files_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            s["video_files"] = []
    return public_payload(seasons)


@api.get("/api/cover/{franchise_id}")
async def get_cover(franchise_id: int):
    """Serve a cached poster image."""
    franchise = db.get_franchise(franchise_id)
    if not franchise or not franchise.get("cover_filename"):
        raise HTTPException(status_code=404, detail="Cover not found")

    cover_path = (COVERS_DIR / franchise["cover_filename"]).resolve()
    try:cover_path.relative_to(COVERS_DIR.resolve())
    except ValueError:raise HTTPException(status_code=403,detail='Invalid cover path')
    if not cover_path.is_file():
        raise HTTPException(status_code=404, detail="Cover file missing")

    return FileResponse(str(cover_path), media_type="image/jpeg")


@api.get("/api/video/{season_id}/{filename:path}")
async def serve_video(season_id: int, filename: str):
    """Serve a video file directly for streaming."""
    season = db.get_season(season_id)
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    folder = season.get("season_folder_path")
    if not folder:
        raise HTTPException(status_code=404, detail="Season folder not set")

    # Reject path traversal
    if ".." in Path(filename).parts or Path(filename).is_absolute() or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    indexed = json.loads(season.get("video_files_json") or "[]")
    if filename not in indexed:
        raise HTTPException(status_code=404, detail="Video is not indexed for this season")
    folder_path = Path(folder).resolve()
    video_path = (folder_path / filename).resolve()

    # Ensure path stays within season folder
    try:
        video_path.relative_to(folder_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: outside season directory")

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found")

    # Determine media type
    ext = video_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".webm": "video/webm",
        ".ts": "video/mp2t",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(str(video_path), media_type=media_type)


@api.get("/api/health")
async def health_check():
    """Health status endpoint."""
    return {
        "status": "healthy",
        "service": "AnimeVault Local Streaming Bridge",
        "port": _bound_port,
    }


@api.get("/api/stats")
async def get_stats():
    """Get library statistics."""
    return db.get_library_stats()


@api.get("/api/updates")
async def get_updates():
    """Get franchises with new updates (sequels, airing)."""
    franchises = db.get_all_franchises()
    updates = [f for f in franchises if f.get("has_new_update")]
    for franchise in updates:
        franchise.pop("metadata_json", None)
    return public_payload(updates)



# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------
_server_thread: Optional[threading.Thread] = None
_server_instance: Optional[uvicorn.Server] = None
_bound_port: Optional[int] = None


def api_base_url():
    if _bound_port is None:
        return None
    host = f"[{LOCAL_API_HOST}]" if ":" in LOCAL_API_HOST else LOCAL_API_HOST
    return f"http://{host}:{_bound_port}"


def start_server():
    """Reserve a port before starting Uvicorn, using a free port if needed."""
    global _server_thread, _server_instance, _bound_port
    if LOCAL_API_HOST not in ('127.0.0.1','::1','localhost') and not API_ACCESS_TOKEN:return None
    if _server_thread and _server_thread.is_alive():
        return api_base_url()

    family = socket.AF_INET6 if ":" in LOCAL_API_HOST else socket.AF_INET
    listener = socket.socket(family, socket.SOCK_STREAM)
    if sys.platform == "win32":
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        try:
            listener.bind((LOCAL_API_HOST, LOCAL_API_PORT))
        except OSError:
            listener.bind((LOCAL_API_HOST, 0))
        listener.listen()
    except OSError:
        listener.close()
        return None

    _bound_port = listener.getsockname()[1]
    config = uvicorn.Config(
        api,
        host=LOCAL_API_HOST,
        port=_bound_port,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    instance = uvicorn.Server(config)
    _server_instance = instance

    def run():
        try:
            instance.run(sockets=[listener])
        finally:
            listener.close()

    _server_thread = threading.Thread(target=run, daemon=True, name="FastAPI-Server")
    _server_thread.start()
    return api_base_url()


def stop_server():
    """Gracefully stop the streaming bridge and release its socket."""
    global _server_instance, _server_thread, _bound_port
    if _server_instance:
        _server_instance.should_exit = True
    if _server_thread and _server_thread.is_alive():
        _server_thread.join(timeout=2)
        if _server_thread.is_alive():
            return
    _server_instance = _server_thread = _bound_port = None
