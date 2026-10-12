"""Builds README.md from the practice notebooks. Run by GitHub Actions."""
import json, re, glob, subprocess, datetime
from urllib.parse import quote

USER = "Phantom2101"
REPO = "Python-Daily-Practicee"
NAME = "Phantom"            # EDIT: name shown in the title
NB_DIR = "notebooks"

def has_nested_loop(code):
    stack = []
    for line in code.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        while stack and stack[-1] >= indent:
            stack.pop()
        if re.match(r"\s*(for|while)\b", line):
            if stack:
                return True
            stack.append(indent)
    return False

def has_recursion(code):
    lines = code.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"(\s*)def\s+(\w+)", line)
        if not m:
            continue
        ind, name = len(m.group(1)), m.group(2)
        for l in lines[i + 1:]:
            if l.strip() and len(l) - len(l.lstrip()) <= ind:
                break
            if re.search(rf"\b{name}\s*\(", l):
                return True
    return False

# (topic, level 1-3, regex or function). Order = learning roadmap order.
TOPICS = [
    ("Variables & Data Types", 1, r"\btype\(|\bint\(|\bfloat\(|\bbool\("),
    ("User Input", 1, r"\binput\("),
    ("Operators & Math", 1, r"\*\*|//|%|\bmath\.|\bdivmod\(|\bround\("),
    ("Conditionals", 1, r"^\s*(if|elif)\b"),
    ("Strings", 1, r"\.(upper|lower|split|join|replace|strip|find|title|startswith|endswith|format)\(|\bf[\"']"),
    ("Loops", 1, r"^\s*(for|while)\b"),
    ("Lists", 2, r"\.(append|extend|insert|remove|pop|sort|reverse)\(|\blist\(|\bsorted\("),
    ("Tuples", 2, r"\btuple\(|^\s*\w+\s*=\s*\([^)]*,[^)]*\)"),
    ("Sets", 2, r"\bset\(|\.(add|union|intersection|difference|discard)\("),
    ("Dictionaries", 2, r"\.(items|keys|values|get|update|setdefault)\(|\bdict\(|^\s*\w+\s*=\s*\{.*:"),
    ("Nested Loops", 2, has_nested_loop),
    ("Comprehensions", 2, r"\[[^\]\n]+\bfor\b[^\]\n]+\bin\b|\{[^}\n]+\bfor\b[^}\n]+\bin\b"),
    ("Functions", 2, r"^\s*def\s+\w+"),
    ("Lambda, Map & Filter", 2, r"\blambda\b|\bmap\(|\bfilter\(|\breduce\("),
    ("Error Handling", 2, r"^\s*(try|except|raise|finally)\b"),
    ("File Handling", 2, r"\bopen\("),
    ("Recursion", 3, has_recursion),
    ("OOP (Classes)", 3, r"^\s*class\s+\w+|__init__"),
    ("Decorators & Generators", 3, r"^\s*@\w+|\byield\b"),
    ("NumPy", 3, r"\bnumpy\b|\bnp\."),
    ("Pandas", 3, r"\bpandas\b|\bpd\.|DataFrame"),
    ("Visualization", 3, r"\bmatplotlib\b|\bplt\.|\bseaborn\b|\bsns\."),
]
LEVELS = {1: ("Beginner", "brightgreen", "🟢"),
          2: ("Intermediate", "yellow", "🟡"),
          3: ("Advanced", "red", "🔴")}

def matches(check, code):
    return check(code) if callable(check) else re.search(check, code, re.M) is not None

def clean(code):
    return "\n".join(l for l in code.splitlines()
                     if l.strip() and not l.strip().startswith(("#", "%", "!")))

def git_time(path):
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)

def practice_days():
    r = subprocess.run(["git", "log", "--format=%ad", "--date=short", "--", NB_DIR],
                       capture_output=True, text=True)
    return sorted(set(r.stdout.split()))

def streak(days):
    ds = {datetime.date.fromisoformat(d) for d in days}
    d = datetime.date.today()
    if d not in ds:
        d -= datetime.timedelta(days=1)
    n = 0
    while d in ds:
        n += 1
        d -= datetime.timedelta(days=1)
    return n

def badge(label, msg, color, logo=None):
    esc = lambda s: quote(str(s).replace("-", "--").replace("_", "__"), safe="")
    url = f"https://img.shields.io/badge/{esc(label)}-{esc(msg)}-{color}?style=for-the-badge"
    if logo:
        url += f"&logo={logo}&logoColor=white"
    return f'<img src="{url}" alt="{label}"/>'

def bar(n, goal=8, width=10):
    filled = round(min(n / goal, 1) * width)
    return "█" * filled + "░" * (width - filled)

def status(n):
    return ("⬜ Not started" if n == 0 else "🟡 Started" if n < 3
            else "🟠 Practicing" if n < 8 else "🟢 Strong")

# ---------- analyse notebooks ----------
counts = {t[0]: 0 for t in TOPICS}
nb_info = []            # (file name, code cells, last topic index, last heading)
for path in sorted(glob.glob(f"{NB_DIR}/*.ipynb"), key=git_time):
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    code_cells, last_hit, last_title = 0, None, None
    for c in nb.get("cells", []):
        src = c.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        if c.get("cell_type") == "markdown":
            m = re.search(r"^#+\s*(.+)$", src, re.M)
            if m:
                last_title = m.group(1).strip()
            continue
        if c.get("cell_type") != "code" or "userdata.get" in src:
            continue
        code = clean(src)
        if not code:
            continue
        code_cells += 1
        hit = [i for i, t in enumerate(TOPICS) if matches(t[2], code)]
        for i in hit:
            counts[TOPICS[i][0]] += 1
        if hit:
            last_hit = max(hit)
    nb_info.append((path.split("/")[-1], code_cells, last_hit, last_title))

latest = next(((i, t) for _, _, i, t in reversed(nb_info) if i is not None), None)
if latest:
    idx, latest_title = latest
    latest_name, lvl = TOPICS[idx][0], TOPICS[idx][1]
else:
    latest_name, lvl, latest_title = "Getting started", 1, None
latest_title = latest_title or latest_name
lvl_name, lvl_color, lvl_emoji = LEVELS[lvl]

days = practice_days()
cur_streak = streak(days)
covered = sum(1 for v in counts.values() if v)
total_cells = sum(n[1] for n in nb_info)

# ---------- build README ----------
rows = []
for name, level, _ in TOPICS:
    n = counts[name]
    rows.append(f"| {LEVELS[level][2]} {LEVELS[level][0]} | {name} | `{bar(n)}` | {n} | {status(n)} |")

pie = "\n".join(f'    "{n}" : {c}' for n, c in counts.items() if c) or '    "No data yet" : 1'

nb_rows = []
for fname, cells, _, _ in nb_info:
    q = quote(fname)
    colab = f"https://colab.research.google.com/github/{USER}/{REPO}/blob/main/{NB_DIR}/{q}"
    nb_rows.append(f"| [{fname}]({NB_DIR}/{q}) | {cells} | "
                   f"[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({colab}) |")

now = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC")

readme = f"""<h1 align="center">🐍 {NAME}'s Python Practice Journey</h1>
<p align="center"><i>Learning in public: daily Colab practice, tracked automatically.</i></p>

<p align="center">
{badge("Level", lvl_name, lvl_color, "python")}
{badge("Topics", f"{covered} of {len(TOPICS)}", "blue")}
{badge("Streak", f"{cur_streak} days", "orange")}
{badge("Days practiced", len(days), "success")}
</p>

## 📊 Live Dashboard

| 🎯 Current topic | 📈 Level | 📝 Latest section | 🔥 Streak | 🗓️ Days practiced | 🧮 Code cells |
|---|---|---|---|---|---|
| **{latest_name}** | {lvl_emoji} {lvl_name} | {latest_title} | {cur_streak} days | {len(days)} | {total_cells} |

## 🗺️ Topic Roadmap

| Level | Topic | Practice depth | Cells | Status |
|---|---|---|---|---|
{chr(10).join(rows)}

## 🥧 Practice Distribution

```mermaid
pie showData title Practice cells per topic
{pie}
```

## 📓 Notebooks

| Notebook | Code cells | Run it |
|---|---|---|
{chr(10).join(nb_rows)}

## 🔥 Activity

<p align="center">
  <img src="https://streak-stats.demolab.com/?user={USER}&theme=tokyonight&hide_border=true" alt="Streak"/>
</p>
<p align="center">
  <img src="https://github-readme-activity-graph.vercel.app/graph?username={USER}&theme=tokyo-night&hide_border=true" alt="Activity graph"/>
</p>

---
<sub>Auto-generated on {now} by GitHub Actions from the notebooks in this repo.</sub>
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)
print("README.md updated")
