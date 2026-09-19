"""把 questions/*.json 渲染成人可读版本：
- questions/README.md：全部题目的总览（一页翻完）
- prompts/{题号}-prompt.md：每题一张卡片，含投放说明
改完题后运行一次：python export_questions.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent


def render(q):
    lines = [f"## {q['id']} {q['title']}", ""]
    lines.append(f"- 类别：{q['category']}")
    if q.get("persona"):
        lines.append(f"- 人设卡：{q['persona']}")
    else:
        lines.append("- 人设卡：无（测裸模型默认行为）")
    lines.append(f"- 考维度：{' / '.join(q['dimensions'])}")
    lines.append("")
    lines.append("### 用户脚本")
    for t in q["turns"]:
        lines.append(f"{t['turn']}. {t['user']}")
    lines.append("")
    lines.append("### 题眼与踩雷点")
    for p in q["pitfalls"]:
        lines.append(f"- {p}")
    lines.append("")
    lines.append(f"### 理想回答方向\n\n{q['ideal_direction']}")
    lines.append("")
    lines.append(f"> 评分细则（rubric）见原文件 questions/{q['id']}.json")
    lines.append("")
    return "\n".join(lines)


def main():
    questions = sorted((ROOT / "questions").glob("*.json"))
    prompts_dir = ROOT / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    parts = [
        "# 题库总览（人类可读版）",
        "",
        "本文件由 `python export_questions.py` 自动生成，改题后请重新生成。",
        "评分细则的完整 rubric 以各题 JSON 为准。",
        "单题卡片见 prompts/ 目录。",
        "",
        f"当前共 {len(questions)} 题。",
        "",
        "---",
        "",
    ]
    for f in questions:
        q = json.loads(f.read_text(encoding="utf-8"))
        parts.append(render(q))
        parts.append("---")
        parts.append("")
        card = [
            f"# {q['id']} {q['title']}（投放卡片）",
            "",
            render(q),
            "",
            "## 投放方式",
            "",
            "- API 批量跑：`python run_eval.py " + q["id"] + "`",
            "- 手动网页测：有人设卡则先发人设、等回应后逐轮发用户消息；无人设卡直接逐轮发",
            "- 回答一字不改存档到 runs/data/<题号>/，命名 `题号_模型_日期.md`",
        ]
        (prompts_dir / f"{q['id']}-prompt.md").write_text("\n".join(card), encoding="utf-8")
    (ROOT / "questions" / "README.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"已生成 questions/README.md + prompts/ 单题卡片（{len(questions)} 题）")


if __name__ == "__main__":
    main()
