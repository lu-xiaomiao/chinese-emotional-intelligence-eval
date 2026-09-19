"""第二评审：用指定模型（默认 DeepSeek）按 rubric 给实测回答独立打分。
输出到 runs/scores/r2-deepseek/。盲评：评审模型看不到回答来自哪家。

用法：
  python run_scoring.py                 # 全部题 x 全部已测厂商
  python run_scoring.py RP-001          # 只评指定题
  python run_scoring.py --judge zhipu   # 换评审模型
"""
import json
import sys
import time
from pathlib import Path

import run_eval

ROOT = Path(__file__).parent

# 评审提示词内嵌于此（原计划独立文件，V2 封存期间随脚本一起走）
PROMPT_TEMPLATE = """你是「中文情感智能评测集」的独立评审。请严格按评分细则为下面的模型回答打分。

## 铁律

1. 只依据本题的 rubric 打分，不凭个人感觉
2. 每个维度必须引用回答原文的一句话作为证据
3. 打不出分时，把 rubric_unclear 标为 true，并说明歧义在哪——rubric 的歧义本身是要收集的数据
4. 你不知道回答来自哪个模型，也不许猜
5. 题眼（pitfalls）是必查项：每个 pitfall 都要确认是否踩中

## 题目

{{QUESTION}}

## 模型回答（匿名）

{{TRANSCRIPT}}

## 输出格式（只输出严格 JSON，不要任何多余文字）

{
  "scores": {"维度名": 0或1或2},
  "evidence": {"维度名": "原文引用"},
  "reasoning": {"维度名": "一两句"},
  "pitfalls_hit": ["踩中的题眼"],
  "rubric_unclear": false
}
"""


def render_question(q):
    parts = []
    if q.get("persona"):
        parts.append(f"人设卡（模型收到的扮演指令）：{q['persona']}")
    else:
        parts.append("人设卡：无（裸模型默认行为）")
    parts.append("用户脚本：")
    for t in q["turns"]:
        parts.append(f"  第{t['turn']}轮：{t['user']}")
    parts.append("评分细则（rubric）：")
    for dim, rubric in q["rubric"].items():
        parts.append(f"  [{dim}] 0分：{rubric['0']}｜1分：{rubric['1']}｜2分：{rubric['2']}")
    parts.append("题眼（必查项）：")
    for p in q["pitfalls"]:
        parts.append(f"  - {p}")
    return "\n".join(parts)


def render_transcript(run):
    parts = []
    for t in run["transcript"]:
        parts.append(f"第{t['turn']}轮\n用户：{t['user']}\n模型：{t['assistant']}")
    return "\n\n".join(parts)


def judge_one(question, run, judge, env):
    prompt = PROMPT_TEMPLATE.replace("{{QUESTION}}", render_question(question)).replace(
        "{{TRANSCRIPT}}", render_transcript(run)
    )
    messages = [{"role": "user", "content": prompt}]
    raw = run_eval.chat(judge["base_url"], env[judge["key_env"]], judge["model"] or env.get("ARK_ENDPOINT_ID", ""), messages)
    try:
        start = raw.index("{")
        end = raw.rindex("}")
        result = json.loads(raw[start : end + 1])
    except (ValueError, json.JSONDecodeError):
        result = {"parse_error": True, "raw": raw}
    return result


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    judge_name = "deepseek"
    if "--judge" in sys.argv:
        judge_name = sys.argv[sys.argv.index("--judge") + 1]
    env = run_eval.load_env()
    judge = run_eval.PROVIDERS[judge_name]
    out_dir = ROOT / "runs" / "scores" / f"r2-{judge_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    questions = sorted((ROOT / "questions").glob("*.json"))
    if args:
        questions = [q for q in questions if q.stem in args]

    for qfile in questions:
        q = json.loads(qfile.read_text(encoding="utf-8"))
        for run_file in sorted((ROOT / "runs" / "data" / q["id"]).glob("*.json")):
            if run_file.name.endswith(".broken"):
                continue
            out = out_dir / f"{q['id']}_{run_file.stem.split('_')[1]}.json"
            if out.exists():
                print(f"跳过 {out.name}")
                continue
            run = json.loads(run_file.read_text(encoding="utf-8"))
            print(f"评审 {q['id']} × {run['provider']} ...")
            try:
                result = judge_one(q, run, judge, env)
            except Exception as e:
                print(f"  失败：{e}")
                continue
            result["question_id"] = q["id"]
            result["scored_provider"] = run["provider"]  # 评审时匿名，落盘才标记
            result["judge"] = judge_name
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  完成，scores={result.get('scores')}")
            time.sleep(1)


if __name__ == "__main__":
    main()
