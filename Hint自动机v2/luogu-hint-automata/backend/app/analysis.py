import re
from collections import Counter

from app.models import ProblemContent, SolutionSummary

STOPWORDS = {
    "的", "了", "是", "在", "和", "也", "就", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "有", "一", "一个", "一种", "可以", "这个", "那个", "但", "但是", "因为", "所以", "如果", "那么",
    "把", "被", "让", "从", "到", "对", "与", "及", "或", "等", "并", "且", "则", "即", "为", "这",
    "the", "a", "an", "is", "are", "of", "and", "to", "in", "on", "for", "we", "you", "it", "that",
    "this", "with", "as", "be", "by", "or", "if", "can", "will", "do", "does", "not", "no",
}

TECH_TERMS = {
    "前缀和", "差分", "二分", "倍增", "并查集", "线段树", "树状数组", "单调栈", "单调队列",
    "贪心", "动态规划", "dp", "状压", "数位dp", "区间dp", "树形dp", "概率期望", "网络流",
    "最短路", "最小生成树", "拓扑排序", "强连通分量", "双连通分量", "割点", "桥",
    "深度优先搜索", "广度优先搜索", "dfs", "bfs", "回溯", "分治", "cdq分治", "整体二分",
    "哈希", "字符串", "kmp", "manacher", "trie", "ac自动机", "后缀数组", "后缀自动机",
    "莫队", "分块", "树链剖分", "lca", "最近公共祖先", "欧拉回路", "哈密顿", "博弈",
    "矩阵", "高斯消元", "线性基", "多项式", "fft", "生成函数", "容斥", "卡特兰",
    "贪心", "模拟", "枚举", "构造", "交互", "离线", "在线",
}


def score_solution(summary: SolutionSummary, index: int) -> float:
    """按来源质量评分：互动数据 > 内容完整性 > 排序位置。"""
    score = 0.0
    score += min(summary.votes, 500) * 0.5
    if summary.author:
        score += 5.0
    if len(summary.excerpt) >= 80:
        score += 10.0
    if re.search(r"思路|算法|分析|做法|复杂度", summary.excerpt):
        score += 6.0
    score -= index * 1.2
    return score


def select_solutions(content: ProblemContent, limit: int) -> list[SolutionSummary]:
    candidates = [item for item in content.solution_summaries if item.excerpt or item.title]
    scored = sorted(
        ((score_solution(item, index), item) for index, item in enumerate(candidates)),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [item for _, item in scored[:limit]]


def keyword_score(text: str) -> dict[str, float]:
    """统计可能的知识点词频，用于选择材料和生成提示。"""
    if not text:
        return {}
    lowered = text.lower()
    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{2,}", lowered)
    frequencies = Counter(tokens)
    scores: dict[str, float] = {}
    for term in TECH_TERMS:
        key = term.lower()
        count = 0
        for token, number in frequencies.items():
            if key == token or key in token:
                count += number
        if count:
            scores[term] = scores.get(term, 0.0) + count * 2.0
    for token, number in frequencies.items():
        if token in STOPWORDS:
            continue
        if len(token) >= 2 and token not in scores:
            scores[token] = scores.get(token, 0.0) + number * 0.25
    return scores


def best_keywords(content: ProblemContent, limit: int = 12) -> list[tuple[str, float]]:
    corpus = " ".join([content.statement, *content.solution_texts])
    if not corpus.strip():
        return []
    scores = keyword_score(corpus)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)[:limit]


def build_corpus(content: ProblemContent, limit: int) -> str:
    """组装供模型使用的上下文，控制长度并标注来源。"""
    parts: list[str] = [f"# {content.title}\n\n## 题面\n\n{content.statement[:12000]}"]
    solutions = select_solutions(content, limit)
    for index, solution in enumerate(solutions, 1):
        parts.append(
            f"## 参考题解 {index}\n标题：{solution.title}\n作者：{solution.author or '未知'}"
            f"\n点赞：{solution.votes}\n\n{solution.excerpt[:3000]}"
        )
    text = "\n\n".join(parts)
    return text[:28000]
