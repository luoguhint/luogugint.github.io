import hashlib
import json
import time
from pathlib import Path

from app.config import settings
from app.models import HintRequest

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _key(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def get_problem_cache(problem_id: str) -> dict | None:
    target = CACHE_DIR / "problem" / f"{problem_id.upper()}.json"
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    age_hours = (time.time() - payload.get("stored_at", 0)) / 3600
    if age_hours > settings.cache_hours:
        return None
    return payload["data"]


def set_problem_cache(problem_id: str, data: dict) -> None:
    directory = CACHE_DIR / "problem"
    _ensure_dir(directory)
    target = directory / f"{problem_id.upper()}.json"
    payload = {"stored_at": time.time(), "data": data}
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _hint_key(request: HintRequest) -> str:
    raw = f"{request.problem_id}|{request.level}|{request.mode}|{request.student_note}"
    return _key(raw)


def get_hint_cache(request: HintRequest) -> dict | None:
    target = CACHE_DIR / "hint" / f"{_hint_key(request)}.json"
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    age_hours = (time.time() - payload.get("stored_at", 0)) / 3600
    if age_hours > settings.cache_hours:
        return None
    return payload["data"]


def set_hint_cache(request: HintRequest, data: dict) -> None:
    directory = CACHE_DIR / "hint"
    _ensure_dir(directory)
    target = directory / f"{_hint_key(request)}.json"
    payload = {"stored_at": time.time(), "data": data}
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
