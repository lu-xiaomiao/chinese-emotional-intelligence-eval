"""批量实测脚本：读 questions/ 里的题，逐轮调用各家 API，回答存档到 runs/data/。
用法：
  python run_eval.py              # 跑所有题 x 所有已配置的厂商（跳过已跑的）
  python run_eval.py RP-001       # 只跑指定题
  python run_eval.py --force      # 已跑的也重跑
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent

PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "key_env": "ZHIPU_API_KEY",
        "model": "glm-4-flash",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1/chat/completions",
        "key_env": "MOONSHOT_API_KEY",
        "model": "kimi-k2.6",
    },
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "key_env": "ARK_API_KEY",
        "model": None,  # 用接入点 ID，运行时从 ARK_ENDPOINT_ID 读
    },
}


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def build_system_prompt(question):
    persona = question.get("persona")
    if not persona:
        return None
    return (
        "接下来请你扮演一个角色，全程保持人设，不要跳出角色，不要提及你是 AI。\n\n"
        + persona
        + "\n\n我是你的对话对象。准备好了吗？"
    )


def chat(base_url, api_key, model, messages):
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    # 豆包（火山方舟）长回复经常超过 120s，超时放宽到 300s
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def run_one(question, provider_name, provider, env, today):
    qid = question["id"]
    data_dir = ROOT / "runs" / "data" / qid
    data_dir.mkdir(parents=True, exist_ok=True)
    out_json = data_dir / f"{qid}_{provider_name}_{today}.json"
    if out_json.exists():
        print(f"  跳过 {provider_name}（已有结果，--force 可重跑）")
        return

    model = provider["model"] or env.get("ARK_ENDPOINT_ID", "")
    messages = []
    system = build_system_prompt(question)
    if system:
        messages.append({"role": "system", "content": system})

    transcript = []
    for turn in question["turns"]:
        messages.append({"role": "user", "content": turn["user"]})
        reply = chat(provider["base_url"], env[provider["key_env"]], model, messages)
        messages.append({"role": "assistant", "content": reply})
        transcript.append({"turn": turn["turn"], "user": turn["user"], "assistant": reply})
        time.sleep(1)  # 避免触发限流

    record = {
        "question_id": qid,
        "provider": provider_name,
        "model": model,
        "entrance": "api",
        "date": today,
        "system_prompt": system,  # 快照：当时实际喂给模型的提示词，改题后旧记录仍可复现
        "transcript": transcript,
    }
    out_json.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# {qid} × {provider_name}", f"- 入口：API", f"- 模型：{model}", f"- 日期：{today}", ""]
    for t in transcript:
        md += [f"## 第 {t['turn']} 轮", f"用户：{t['user']}", "", "模型：", t["assistant"], ""]
    out_json.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    print(f"  完成 {provider_name}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    if force:
        for f in (ROOT / "runs" / "data").rglob("*.json"):
            if not args or any(a in f.name for a in args):
                f.unlink()
                f.with_suffix(".md").unlink(missing_ok=True)

    env = load_env()
    questions = sorted((ROOT / "questions").glob("*.json"))
    if args:
        questions = [q for q in questions if q.stem in args]
    today = date.today().strftime("%Y%m%d")

    for qfile in questions:
        question = json.loads(qfile.read_text(encoding="utf-8"))
        print(f"题目 {question['id']}：")
        for name, provider in PROVIDERS.items():
            if not env.get(provider["key_env"]):
                print(f"  跳过 {name}（未配置 Key）")
                continue
            try:
                run_one(question, name, provider, env, today)
            except urllib.error.HTTPError as e:
                print(f"  失败 {name}：HTTP {e.code} {e.read().decode('utf-8')[:200]}")
            except Exception as e:
                print(f"  失败 {name}：{e}")


if __name__ == "__main__":
    main()
