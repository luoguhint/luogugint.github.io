from app.models import ProblemContent, SolutionSummary


def demo_problem(problem_id: str) -> ProblemContent:
    return ProblemContent(
        problem_id=problem_id.upper(),
        title=f"演示题目 {problem_id.upper()}",
        difficulty="普及-",
        tags=["模拟", "演示模式"],
        statement=(
            "这是演示模式的占位题面。配置真实模型与洛谷抓取后，将显示对应题目的实际内容。"
            "请阅读真实题面中的输入格式、输出格式、数据范围、样例及说明，并先尝试自己建模。"
        ),
        solution_summaries=[
            SolutionSummary(
                solution_id="demo-1",
                title="演示题解：先审题，再建模",
                author="Hint Automata",
                votes=0,
                excerpt="演示材料仅用于验证页面流程，不能替代真实题解。",
            )
        ],
        solution_texts=[],
        source="demo",
        truncated=False,
    )
