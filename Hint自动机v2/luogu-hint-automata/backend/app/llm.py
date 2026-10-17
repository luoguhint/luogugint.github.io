import json
from typing import Any

import httpx

from app.config import settings
from app.prompts import LEVEL_RULES, build_user_prompt, parse_hint

DEFAULT_TIMEOUT = 120.0


async def generate_hint(
    *,
    problem_id: str,
    title: str,
    level: str,
    mode: str,
    corpus: str,
    student_note: str,
    model_name: str,
    previous_answer: str | None = None,
) -> dict[str, Any]:
    system_prompt = _system_prompt(level)
    user_prompt = build_user_prompt(
        problem_id=problem_id,
        title=title,
        level=level,
        mode=mode,
        corpus=corpus,
        student_note=student_note,
        previous_answer=previous_answer,
    )
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request_timeout = httpx.Timeout(settings.llm_timeout or DEFAULT_TIMEOUT, connect=15.0)
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    async with httpx.AsyncClient(timeout=request_timeout, headers=headers) as client:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    raw = data["choices"][0]["message"]["content"]
    result = parse_hint(raw)
    return {
        "summary": result.summary,
        "hints": result.hints,
        "check_questions": result.check_questions,
        "raw": result.raw,
    }


def _system_prompt(level: str) -> str:
    rules = LEVEL_RULES.get(level, LEVEL_RULES["concept"])
    return (
        "你是算法竞赛辅导 Hint 生成器，必须以 JSON 输出。"
        f"当前档位：{rules['name']}。上限：{rules['ceiling']}"
        "禁止完整题解、禁止完整代码、禁止直接给出样例答案。回答中文。"
    )


def build_demo_answer(level: str, title: str, statement: str, sources: list[dict]) -> dict[str, Any]:
    keywords = _extract_keywords(statement)
    return {
        "summary": f"演示模式：尚未接入真实模型；以下是基于《{title}》题面的关键词提示。",
        "hints": [
            "请在后端配置 OPENAI 兼容的 LLM_BASE_URL、LLM_API_KEY 与 LLM_MODEL。",
            f"当前档位【{LEVEL_RULES[level]['name']}】：{LEVEL_RULES[level]['goal']}。",
            "可先尝试从这些关键词出发思考：" + "、".join(keywords[:6]) + "。",
        ],
        "check_questions": [
            "你能把输入数据抽象成什么对象或结构？",
            "如果不考虑复杂度，最朴素的做法需要维护什么？",
        ],
        "raw": json.dumps({"demo": True, "level": level, "keywords": keywords}, ensure_ascii=False),
        "sources": sources,
    }


def _extract_keywords(statement: str) -> list[str]:
    words = ["约束条件", "输入输出", "样例", "数据范围"]
    found = [word for word in words if word in statement]
    return found or ["输入规模", "答案性质", "状态定义"]
