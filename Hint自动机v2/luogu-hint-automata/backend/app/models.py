from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SolutionSummary(BaseModel):
    """题解摘要，用于筛选和展示来源。"""

    solution_id: str
    title: str
    author: str = ""
    votes: int = 0
    created_at: str | None = None
    excerpt: str = ""


class ProblemContent(BaseModel):
    """抓取到的题目与题解内容。"""

    problem_id: str
    title: str
    difficulty: str = ""
    tags: list[str] = Field(default_factory=list)
    statement: str = ""
    solution_summaries: list[SolutionSummary] = Field(default_factory=list)
    solution_texts: list[str] = Field(default_factory=list)
    source: str = "luogu"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    truncated: bool = False


class HintRequest(BaseModel):
    problem_id: str = Field(..., description="洛谷题目编号，例如 P1001")
    level: str = Field("concept", description="keyword/concept/approach/next_step")
    student_note: str = Field("", description="用户当前的卡点或思路")
    mode: str = Field("normal", description="normal/explore/stuck")


class SourceItem(BaseModel):
    title: str
    author: str = ""
    votes: int = 0
    excerpt: str = ""


class HintResponse(BaseModel):
    problem_id: str
    title: str
    level: str
    mode: str
    model: str
    answer: str
    suggested_next_level: str | None = None
    sources: list[SourceItem] = Field(default_factory=list)
    safety: dict[str, Any] = Field(default_factory=dict)
    demo: bool = False
    cached: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ProblemMeta(BaseModel):
    problem_id: str
    title: str
    difficulty: str = ""
    tags: list[str] = Field(default_factory=list)
    solution_count: int = 0
    has_full_text: bool = False
    demo: bool = False
