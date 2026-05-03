"""
Recording Studio API — Web-based pronunciation capture
======================================================
Serves the recording UI HTML and handles audio upload/download.
Recordings are stored on disk at /app/recordings/ with metadata.

Endpoints:
    GET  /record              → Recording studio HTML page
    GET  /recordings/list     → JSON list of all recordings
    GET  /recordings/file/{fn}→ Stream a recording for playback
    POST /recordings/upload   → Upload a new recording
    DELETE /recordings/delete/{fn} → Remove a recording
    GET  /recordings/download → ZIP all recordings for download

Ref: User directive 2026-05-02 (remote recording UI).
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

router = APIRouter(tags=["recordings"])

_RECORDINGS_DIR = Path(os.getenv("RECORDINGS_DIR", "/app/recordings"))
_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def _list_recordings() -> List[dict]:
    """Return all recordings with metadata."""
    results = []
    for path in sorted(_RECORDINGS_DIR.glob("*")):
        if path.is_file() and path.suffix in (".webm", ".wav", ".mp3", ".ogg"):
            meta_path = path.with_suffix(path.suffix + ".json")
            meta = {}
            if meta_path.exists():
                import json
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            results.append(
                {
                    "filename": path.name,
                    "word_id": meta.get("word_id", ""),
                    "word_text": meta.get("word_text", path.stem),
                    "section": meta.get("section", ""),
                    "size_bytes": path.stat().st_size,
                    "duration_s": meta.get("duration_s"),
                    "created_at": path.stat().st_mtime,
                }
            )
    return results


@router.get("/record", response_class=HTMLResponse)
async def recording_studio() -> str:
    """Serve the recording studio HTML page."""
    html_path = Path(__file__).parent / "static" / "record.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    raise HTTPException(status_code=404, detail="Recording UI not found")


@router.get("/recordings/list")
async def list_recordings() -> List[dict]:
    return _list_recordings()


@router.get("/recordings/file/{filename}")
async def get_recording(filename: str):
    path = _RECORDINGS_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")
    return FileResponse(path, media_type="audio/webm", filename=filename)


@router.post("/recordings/upload")
async def upload_recording(
    audio: UploadFile = File(...),
    word_id: str = Form(""),
    word_text: str = Form(""),
    section: str = Form(""),
):
    """Save an uploaded recording + metadata."""
    safe_name = f"{word_id}_{word_text.replace(' ', '_').replace('/', '_')}"[:60]
    ext = Path(audio.filename or "recording.webm").suffix
    if ext not in (".webm", ".wav", ".mp3", ".ogg"):
        ext = ".webm"

    filename = f"{safe_name}{ext}"
    filepath = _RECORDINGS_DIR / filename

    # Handle duplicates
    counter = 1
    while filepath.exists():
        filename = f"{safe_name}_{counter}{ext}"
        filepath = _RECORDINGS_DIR / filename
        counter += 1

    content = await audio.read()
    filepath.write_bytes(content)

    # Save metadata
    meta = {
        "word_id": word_id,
        "word_text": word_text,
        "section": section,
        "filename": filename,
        "size_bytes": len(content),
    }
    meta_path = filepath.with_suffix(ext + ".json")
    import json
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "ok", "filename": filename}


@router.delete("/recordings/delete/{filename}")
async def delete_recording(filename: str):
    path = _RECORDINGS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")
    path.unlink()
    meta_path = path.with_suffix(path.suffix + ".json")
    if meta_path.exists():
        meta_path.unlink()
    return {"status": "deleted"}


@router.get("/recordings/download")
async def download_all_recordings():
    """ZIP all recordings for offline download."""
    recordings = _list_recordings()
    if not recordings:
        raise HTTPException(status_code=404, detail="No recordings to download")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in recordings:
            path = _RECORDINGS_DIR / r["filename"]
            if path.exists():
                zf.write(path, arcname=r["filename"])
            meta_path = path.with_suffix(path.suffix + ".json")
            if meta_path.exists():
                zf.write(meta_path, arcname=r["filename"] + ".json")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=suryapet_recordings.zip"},
    )
