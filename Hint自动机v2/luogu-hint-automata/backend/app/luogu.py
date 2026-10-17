from __future__ import annotations

import re
from html import unescape
from typing import Any

import httpx

from app.cache import get_problem_cache, set_problem_cache
from app.config import settings
from app.models import ProblemContent, SolutionSummary

PROBLEM_URL = "https://www.luogu.com.cn/problem/{problem_id}"
SOLUTION_LIST_URL = "https://www.luogu.com.cn/problem/solution/{problem_id}"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) LuoguHintAutomata/1.0 (+https://github.com/)",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.luogu.com.cn/",
    "x-luogu-type": "content-only",
}


def normalize_problem_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value.strip())
    if not re.fullmatch(r"[A-Za-z]\w*", cleaned):
        raise ValueError("题号格式不正确，应为 P1001、CF1234A 等格式。")
    return cleaned.upper()


def _clean_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"<br\s*/?>", "\n", value)
    value = re.sub(r"</p>", "\n\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = unescape(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _extract_json(text: str, endpoint: str) -> dict[str, Any]:
    """从 content-only 响应中提取 JSON。"""
    match = re.search(r"window\.additionalData\s*=\s*({.*?})\s*</script>", text, re.S)
    if match:
        return json.loads(match.group(1))
    payload = re.sub(r"^[\s\S]*?(\{)", r"\1", text, count=1)
    payload = re.sub(r"([\s\S]*\})(?:[\s\S]*)", r"\1", payload, count=1)
    return json.loads(payload)


def _fallback_scrape(problem_id: str) -> ProblemContent:
    """解析网页：题面、题解列表。题解全文在公开页面不可用时仅保存链接。"""
    timeout = httpx.Timeout(settings.luogu_timeout, connect=10.0)
    headers = dict(DEFAULT_HEADERS, Referer=f"{PROBLEM_URL.format(problem_id=problem_id)}")
    page_text = ""
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        problem_resp = client.get(PROBLEM_URL.format(problem_id=problem_id))
        problem_resp.raise_for_status()
        page_text = problem_resp.text
        solution_resp = client.get(SOLUTION_LIST_URL.format(problem_id=problem_id))
        solution_text = solution_resp.text if solution_resp.status_code == 200 else ""
    title = _parse_title(page_text)
    statement = _clean_text(_parse_main_text(page_text))
    summaries = _parse_solution_links(solution_text or page_text)
    full_texts: list[str] = []
    return ProblemContent(
        problem_id=problem_id,
        title=title or problem_id,
        statement=statement,
        solution_summaries=summaries,
        solution_texts=full_texts,
        source="luogu-fallback",
        truncated=len(statement) > 20000,
    )


def _parse_title(text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if match:
        return _clean_text(match.group(1).replace("- 洛谷", "").replace("| 洛谷", ""))[:160]
    return ""


def _parse_main_text(text: str) -> str:
    match = re.search(r'<div[^>]+?data-fetch-state="fetched"[^>]*>(.*?)</div>\s*</div>', text, re.S | re.I)
    if match:
        return match.group(1)
    marker = "window.additionalData"
    if marker in text:
        return text[text.index(marker) :][:20000]
    return text


def _parse_solution_links(text: str) -> list[SolutionSummary]:
    summaries: list[SolutionSummary] = []
    seen: set[str] = set()
    for match in re.finditer(r"/problem/solution/\d+/(\d+)", text):
        identifier = match.group(1)
        if identifier in seen:
            continue
        seen.add(identifier)
        context = text[max(0, match.start() - 500) : match.end() + 500]
        title_match = re.search(r"<[^>]+>([^<]{4,120})</[^>]+>", context)
        title = _clean_text(title_match.group(1)) if title_match else f"题解 {identifier}"
        summaries.append(
            SolutionSummary(
                solution_id=identifier,
                title=title[:120],
                votes=0,
                excerpt="需要登录后抓取全文。",
            )
        )
        if len(summaries) >= 10:
            break
    return summaries


def fetch_problem(problem_id: str) -> ProblemContent:
    problem_id = normalize_problem_id(problem_id)
    cached = get_problem_cache(problem_id)
    if cached:
        return ProblemContent(**cached, fetched_at=cached.get("fetched_at", None) or None)
    try:
        content = _fallback_scrape(problem_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ValueError(f"未找到题目 {problem_id}，请检查题号。") from exc
        raise ValueError("暂时无法访问洛谷，请稍后重试。") from exc
    except httpx.HTTPError as exc:
        raise ValueError("网络请求失败，请检查运行环境或稍后重试。") from exc

    payload = content.model_dump(mode="json")
    set_problem_cache(problem_id, payload)
    return content
