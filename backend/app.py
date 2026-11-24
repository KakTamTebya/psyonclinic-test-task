from datetime import datetime, timezone
import os
from pathlib import Path
from threading import Lock

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from matching import reconcile
from sources import SourceError, load_sources


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = FastAPI(title="Сверка врачей", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
)
snapshot = None
refresh_lock = Lock()


def comparison(refresh=False):
    global snapshot
    previous = snapshot
    with refresh_lock:
        if snapshot is not None and (not refresh or snapshot is not previous):
            return snapshot
        try:
            (api, api_pages), (catalog, catalog_pages) = load_sources(os.getenv("MEDICAL_API_KEY"))
        except SourceError as exc:
            return JSONResponse({"error": str(exc), "previous": snapshot}, status_code=503)
        snapshot = {
            "rows": reconcile(api, catalog),
            "apiCount": len(api), "catalogCount": len(catalog),
            "apiPages": api_pages, "catalogPages": catalog_pages,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        return snapshot


@app.get("/api/comparison")
def get_comparison():
    return comparison()


@app.post("/api/refresh")
def refresh_comparison():
    return comparison(refresh=True)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
