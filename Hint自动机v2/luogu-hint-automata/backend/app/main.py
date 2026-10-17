from __future__ import annotations

import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.analysis import build_corpus, select_solutions
from app.cache import get_hint_cache, set_hint_cache
from app.config import settings
from app.demo import demo_problem
from app.llm import build_demo_answer, generate_hint
from app.luogu import fetch_problem
from app.models import (
    HintRequest,
    HintResponse,
    ProblemMeta,
)
from app.prompts import LEVEL_RULES, render_markdown, review

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
VERSION = "2.0.0"

app = FastAPI(
    title="洛谷 Hint 自动机",
    description="渐进式、反剧透的洛谷题目提示生成服务",
    version=VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_request_log: deque[float] = deque(maxlen=1000)


def _check_rate_limit() -> None:
    now = time.time()
    while _request_log and now - _request_log[0] > 60:
        _request_log.popleft()
    if len(_request_log) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")
    _request_log.append(now)


def _verify_api_key(request: Request) -> None:
    required = settings.demo_api_key
    if not required:
        return
    token = request.headers.get("X-API-Key", "")
    if token != required:
        raise HTTPException(status_code=401, detail="缺少或无效的接口密钥。")


@app.exception_handler(HTTPException)
async def _http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": VERSION,
        "luogu_enabled": settings.luogu_enabled,
        "model": settings.llm_model,
        "levels": settings.hint_levels,
        "deployed_url": settings.app_url,
    }


@app.get("/api/levels")
async def list_levels() -> dict:
    return {
        "levels": [
            {
                "id": key,
                "name": value["name"],
                "goal": value["goal"],
                "next_level": value["next_level"],
            }
            for key, value in LEVEL_RULES.items()
        ]
    }


@app.get("/api/problem/{problem_id}")
async def get_problem_meta(problem_id: str, request: Request) -> ProblemMeta:
    _check_rate_limit()
    _verify_api_key(request)
    content = fetch_problem(problem_id)
    return ProblemMeta(
        problem_id=content.problem_id,
        title=content.title,
        difficulty=content.difficulty,
        tags=content.tags,
        solution_count=len(content.solution_summaries),
        has_full_text=bool(content.solution_texts),
        demo=False,
    )


@app.post("/api/hint", response_model=HintResponse)
async def create_hint(request: HintRequest, web_request: Request) -> HintResponse:
    _check_rate_limit()
    _verify_api_key(web_request)
    level = request.level if request.level in LEVEL_RULES else "concept"
    problem_id = request.problem_id.strip()
    if not problem_id:
        raise HTTPException(status_code=400, detail="题号不能为空。")

    cached = get_hint_cache(request)
    if cached:
        return HintResponse(**cached)

    if settings.luogu_enabled:
        try:
            content = fetch_problem(problem_id)
            demo = False
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            content = demo_problem(problem_id)
            demo = True
    else:
        content = demo_problem(problem_id)
        demo = True

    sources = [item.model_dump(mode="json") for item in select_solutions(content, 5)]
    corpus = build_corpus(content, settings.max_solution_details)
    model_name = settings.llm_model

    try:
        hint = await generate_hint(
            problem_id=content.problem_id,
            title=content.title,
            level=level,
            mode=request.mode,
            corpus=corpus,
            student_note=request.student_note,
            model_name=model_name,
        )
    except Exception:  # noqa: BLE001
        hint = build_demo_answer(level, content.title, content.statement, sources)
        demo = True

    safety = review(hint["raw"], level)
    answer = render_markdown(
        type("R", (), {
            "summary": hint["summary"],
            "hints": hint["hints"],
            "check_questions": hint["check_questions"],
        })(),
        level,
        sources,
    )

    response = HintResponse(
        problem_id=content.problem_id,
        title=content.title,
        level=level,
        mode=request.mode,
        model=model_name,
        answer=answer,
        suggested_next_level=LEVEL_RULES[level]["next_level"],
        sources=sources,
        safety=safety,
        demo=demo,
        cached=False,
    )
    payload = response.model_dump(mode="json")
    set_hint_cache(request, payload)
    return response


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def create_app() -> FastAPI:
    return app
