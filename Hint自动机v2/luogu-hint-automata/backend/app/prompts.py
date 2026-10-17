from __future__ import annotations

import json
import re
from dataclasses import dataclass

LEVEL_RULES = {
    "keyword": {
        "name": "关键词提示",
        "ceiling": "只能给出 3-6 个可能相关的知识点/关键词，绝对不能说明这些知识如何组合，更不能写算法步骤、复杂度或代码。",
        "next_level": "concept",
        "goal": "帮学习者回忆可能用到的知识，但不透露题目结构。",
    },
    "concept": {
        "name": "概念铺垫",
        "ceiling": "可以说明相关概念的定义、适用场景和一个与本题无关的示例；不得分析本题输入、条件、状态设计、转移方程或算法选择。",
        "next_level": "approach",
        "goal": "补齐知识盲区，不替用户建立本题模型。",
    },
    "approach": {
        "name": "思路方向",
        "ceiling": "可以说明数据范围暗示的复杂度、状态/答案的抽象形式和值得比较的 2-3 种思路；不得给出完整做法、伪代码、代码、样例答案或复杂度常数。",
        "next_level": "next_step",
        "goal": "让用户自己完成建模和证明，只收窄搜索空间。",
    },
    "next_step": {
        "name": "关键步骤",
        "ceiling": "可以给出当前瓶颈后的下一步、边界/特殊情况提示和复杂度上限；不得输出完整代码、题解全文或样例输出。",
        "next_level": None,
        "goal": "帮助突破卡点，同时尽量保留用户独立实现的机会。",
    },
}

SYSTEM_RULES = """你是一名严谨的算法竞赛辅导助手。你的任务是“扶一把”，而不是替用户完成题目。
请严格根据 LEVEL 要求输出中文 Markdown，控制剧透，不提供完整题解或完整代码。
输出结构固定为 JSON：{"summary":"一句话判断用户的卡点","hints":["提示1","提示2","提示3"],"check_questions":["向用户确认的两个检查问题"]}。
规则：
- hints 最多 3 条，逐条递进但不要跨越当前 LEVEL 的信息上限。
- 不出现代码块；不写可直接提交的代码；不输出样例输入输出答案。
- 如果上下文不足以判断，明确说“信息不足”，不要猜测题号或题解。
- 不要编造点赞、作者、题解来源。仅使用给定的参考材料。"""


def build_user_prompt(
    *,
    problem_id: str,
    title: str,
    level: str,
    mode: str,
    corpus: str,
    student_note: str,
    previous_answer: str | None,
) -> str:
    rules = LEVEL_RULES.get(level, LEVEL_RULES["concept"])
    student_block = student_note.strip() or "用户尚未提供当前卡点。"
    dialogue = ""
    if previous_answer:
        dialogue = f"\n上一轮提示（仅用于判断下一步，不要再复述）：\n{previous_answer[:1500]}\n"
    return f"""题目编号：{problem_id}
题目名称：{title}
提示档位：{level}（{rules['name']}）
目标：{rules['goal']}
信息上限：{rules['ceiling']}
辅导模式：{mode}
{dialogue}
学习者当前思路/卡点：
{student_block}

可参考材料（题面及已公开题解摘录）：
{corpus[:26000]}

请按 SYSTEM_RULES 输出 JSON。若 material 中缺少全文题解，请降低确定性，不要编造。"""


@dataclass
class HintResult:
    summary: str
    hints: list[str]
    check_questions: list[str]
    raw: str


def parse_hint(raw: str) -> HintResult:
    text = raw.strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return HintResult(summary=raw[:180], hints=[], check_questions=[], raw=raw)
    return HintResult(
        summary=str(data.get("summary", ""))[:300],
        hints=[str(item) for item in data.get("hints", []) if str(item).strip()][:3],
        check_questions=[str(item) for item in data.get("check_questions", []) if str(item).strip()][:2],
        raw=raw,
    )


def review(text: str, level: str) -> dict:
    """检查输出是否越级、是否含完整代码或明显答案。"""
    lowered = text.lower()
    violations: list[str] = []
    if re.search(r"```[A-Za-z]*\s*\n[\s\S]{40,}?```", text):
        violations.append("输出疑似包含代码块")
    if any(keyword in text for keyword in ["完整代码", "完整题解", "全部代码", "参考答案如下"]):
        violations.append("出现完整代码/题解表述")
    if level in {"keyword", "concept"} and any(
        phrase in text for phrase in ["时间复杂度 O(", "状态转移", "转移方程", "这道题用", "算法流程"]
    ):
        violations.append(f"{LEVEL_RULES[level]['name']}不应描述本题算法细节")
    return {
        "safe": not violations,
        "level": level,
        "violations": violations,
        "approx_chars": len(text),
        "has_code_block": "```" in text,
    }


def render_markdown(result: HintResult, level: str, sources: list[dict]) -> str:
    rules = LEVEL_RULES.get(level, LEVEL_RULES["concept"])
    parts = [f"## {rules['name']}\n", f"> {result.summary or '请先确认自己已经理解题意和样例。'}", ""]
    if result.hints:
        parts.append("### 提示")
        parts.extend(f"{index + 1}. {item}" for index, item in enumerate(result.hints))
        parts.append("")
    if result.check_questions:
        parts.append("### 先自检")
        parts.extend(f"- {item}" for item in result.check_questions)
        parts.append("")
    if sources:
        parts.append("### 参考来源")
        for item in sources[:5]:
            title = item.get("title", "题解")
            author = item.get("author") or "未知作者"
            votes = item.get("votes", 0)
            parts.append(f"- {title}｜{author}｜{votes} 赞")
        parts.append("")
    parts.append("---")
    parts.append("*内容由模型根据公开题解整理，仅供参考；不要直接照搬代码。*")
    return "\n".join(parts)
