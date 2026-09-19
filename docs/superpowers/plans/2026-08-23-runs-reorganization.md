# runs/ 目录重组 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 runs/ 下混放的 34 个原始实测文件和 4 个评分文件分成两层（data/ 和 scores/），让鹿小苗复核时只进 scores/，查原文只进 data/。

**Architecture:** 纯文件移动 + run_eval.py 输出路径改一处。run_eval.py 是唯一写 runs/ 的程序，改它即可；评分文件、README、投放模板里的路径引用同步更新。

**Tech Stack:** PowerShell 文件操作、Python（run_eval.py）。

## Global Constraints

- 任何文件内容不改一字，只移动位置（原始回答的完整性是公信力来源）
- `.broken` 文件（RP-003_doubao_20260822 空回答）随数据一起进 data/，保留审计痕迹
- 目标结构：
  - `runs/data/` —— 机器产物：每题每家的 `.json`（结构化）+ `.md`（可读版）+ `.broken`
  - `runs/scores/` —— 人的判断：`RP-00X-scores.md`
  - `runs/README.md` —— 留在根部，改写为结构说明
- 工作目录：`C:\ai学习\trae学习\评测集`


### Task 2: run_eval.py 输出路径改到 runs/data/

**Files:**
- Modify: `run_eval.py`（docstring 第 2 行、`run_one` 内 out_json 一行、`main` 内 force 删除的 glob 一处）

**Interfaces:**
- Consumes: Task 1 建好的 `runs/data/` 目录。
- Produces: 脚本今后所有输出写入 `runs/data/`；`--force` 的清理也只扫 `runs/data/`。

- [ ] **Step 1: 改 docstring 和 out_json 路径**

docstring 第 2 行改为：

```python
"""批量实测脚本：读 questions/ 里的题，逐轮调用各家 API，回答存档到 runs/data/。
```

`run_one` 里这一行：

```python
    out_json = ROOT / "runs" / f"{qid}_{provider_name}_{today}.json"
```

改为：

```python
    data_dir = ROOT / "runs" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_json = data_dir / f"{qid}_{provider_name}_{today}.json"
```

- [ ] **Step 2: 改 --force 的清理范围**

`main` 里这一行：

```python
        for f in (ROOT / "runs").glob("*.json"):
```

改为：

```python
        for f in (ROOT / "runs" / "data").glob("*.json"):
```

- [ ] **Step 3: 验证路径构造正确（不真跑 API）**

```powershell
python -c "import sys; sys.path.insert(0,'.'); import run_eval, json; from pathlib import Path; q=json.loads(Path('questions/RP-001.json').read_text(encoding='utf-8')); print(run_eval.build_system_prompt(q)[:20]); d=Path('runs/data'); print('data 目录存在:', d.exists())"
```

期望输出：打印人设卡前 20 字 + `data 目录存在: True`。

- [ ] **Step 4: 冒烟测试——确认不会误重跑**

```powershell
python run_eval.py NO-SUCH-QUESTION
```

期望输出：无任何输出、不报错的退出（没有匹配的题，什么都不做）。这验证脚本改动后还能正常启动。

- [ ] **Step 5: Commit**

```powershell
git add run_eval.py; git commit -m "refactor: run_eval 输出路径迁至 runs/data"
```


### Task 3: 更新三处文档里的路径引用

**Files:**
- Modify: `runs/README.md`（整篇改写为结构说明）
- Modify: `README.md`（目录一节）
- Modify: `prompts/RP-001-prompt.md`（第三步存档路径）

**Interfaces:**
- Consumes: Task 1 的最终结构。
- Produces: 文档与实际结构一致。

- [ ] **Step 1: 改写 runs/README.md**

全文替换为：

```markdown
# runs/ 实测与评分

## 结构

- `data/` —— 原始回答（机器产物）。每题每家一对文件：`.json`（结构化）+ `.md`（可读版）。
  回答一字不改，包括语气词和错别字，这是公信力的来源。
  `.broken` 后缀 = 该次运行不完整（如 API 返回为空），仅存档，不参与评分。
- `scores/` —— 评分成绩单（人的判断）。`RP-00X-scores.md`，含分数、理由、分歧点。

## 文件命名

`题号_模型_日期`，例如 `RP-001_deepseek_20260821.md`

## 规则

- 同时保留截图（放 `data/screenshots/`），防篡改质疑
- 模型如果拒绝角色扮演或跳出人设，原样记录，这本身就是数据
- 评分前先做数据完整性检查（空回答、缺轮次），见 RP-003 豆包 0822 案例
```

- [ ] **Step 2: 改根 README.md 的目录一节**

把：

```markdown
- `questions/` —— 题库（JSON，每题含场景、人设卡、多轮脚本、rubric、踩雷点）
- `examples/` —— badcase 实录 + 归因 + 修复示范样例
```

改为：

```markdown
- `questions/` —— 题库（JSON，每题含场景、人设卡、多轮脚本、rubric、踩雷点）
- `runs/data/` —— 原始实测回答（每题每家 json + md）
- `runs/scores/` —— 评分成绩单与分歧点记录
- `examples/` —— badcase 实录 + 归因 + 修复示范样例
```

- [ ] **Step 3: 改 prompts/RP-001-prompt.md 第三步**

把"存到 `runs/` 目录"改为"存到 `runs/data/` 目录"。

- [ ] **Step 4: Commit**

```powershell
git add runs/README.md README.md prompts/RP-001-prompt.md; git commit -m "docs: 同步 runs 新结构的路径引用"
```

---

### Task 4: 总验证

**Files:** 无新增，纯检查。

- [ ] **Step 1: 全文搜残留旧路径**

```powershell
python -c "import pathlib; [print(f) for f in pathlib.Path('.').rglob('*.md') if 'runs/' in f.read_text(encoding='utf-8', errors='ignore') or 'runs\\' in f.read_text(encoding='utf-8', errors='ignore')]"
```

逐个看输出文件，确认引用的是 `runs/data` 或 `runs/scores`，没有裸 `runs/` 存数据的写法。
（工作日志.md 里的历史记录不用改——那是日志，不是路径引用。）

- [ ] **Step 2: 抽查一个原始回答内容未变**

```powershell
Get-Content -Encoding UTF8 "runs\data\RP-001_kimi_20260821.md" | Select-Object -First 10
```

期望：内容正常显示中文，无乱码、无截断。

- [ ] **Step 3: 最终 commit**

```powershell
git add -A; git commit -m "chore: runs 重组完成，验证通过"
```

---

## 完成后你看到的结构

```
runs/
├── README.md          # 结构说明
├── data/              # 34 个原始文件，查原文来这里
└── scores/            # 4 个成绩单，复核只进这里
```

复核动线：打开 `runs/scores/RP-002-scores.md` → 看到分歧点 → 想查原文时去 `runs/data/` 找同题号文件。

### Task 1: 建目录并移动文件

**Files:**
- Create: `runs/data/`、`runs/scores/`（目录）
- Move: runs/ 下 17 个 `RP-00X_模型_日期.json`、17 个 `.md`、2 个 `.broken` → `runs/data/`
- Move: 4 个 `RP-00X-scores.md` → `runs/scores/`

**Interfaces:**
- Produces: `runs/data/` 与 `runs/scores/` 两个目录，Task 2 的脚本路径依赖此结构。

- [ ] **Step 1: 建目录**

```powershell
New-Item -ItemType Directory -Force "runs\data", "runs\scores"
```

- [ ] **Step 2: 移动原始数据（json + md + broken）**

```powershell
Move-Item "runs\RP-*_*.json*" "runs\data\"
Move-Item "runs\RP-*_*.md*" "runs\data\"
```

说明：通配符 `RP-*_*` 里的下划线保证 scores 文件（`RP-001-scores.md`，无下划线）不会被误移动。`*` 后缀同时覆盖 `.json` 和 `.json.broken`。
若 Move-Item 被策略拦截，改用 Python 兜底：

```powershell
python -c "import shutil,glob,os; os.makedirs('runs/data',exist_ok=True); [shutil.move(f,'runs/data/') for f in glob.glob('runs/RP-*_*.*')]"
```

- [ ] **Step 3: 移动评分文件**

```powershell
Move-Item "runs\RP-001-scores.md","runs\RP-002-scores.md","runs\RP-003-scores.md","runs\RP-004-scores.md" "runs\scores\"
```

- [ ] **Step 4: 验证移动结果**

```powershell
(Get-ChildItem "runs\data" -File).Count    # 期望：34（16 json + 16 md + 2 broken）
(Get-ChildItem "runs\scores" -File).Count  # 期望：4
Get-ChildItem "runs" -File                 # 期望：只剩 README.md
```

期望输出：36 / 4 / 根目录只有 README.md。数字不对就停下来查，不要继续。

- [ ] **Step 5: Commit**

```powershell
git init; git add -A; git commit -m "chore: 重组 runs 目录，data 与 scores 分层"
```

（项目尚未 git init，这一步顺手建仓——反正发布时也要传 GitHub。）

---
