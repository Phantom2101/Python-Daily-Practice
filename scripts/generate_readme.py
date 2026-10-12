"""Builds README.md from the practice notebooks. Run by GitHub Actions."""
import json, re, glob, subprocess, datetime
from urllib.parse import quote
import visuals
import platforms

USER = "Phantom2101"
REPO = "Python-Daily-Practice"
NAME = "Affan"            # EDIT: name shown in the title
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
    ("Variables & Data Types", 1, r"\btype\(|\bint\(|\bfloat\(|\bbool\(|\bstr\("),
    ("User Input", 1, r"\binput\("),
    ("Operators & Math", 1, r"\*\*|//|%|\bmath\.|\bdivmod\(|\bround\(|\babs\("),
    ("Conditionals", 1, r"^\s*(if|elif)\b"),
    ("Strings", 1, r"\.(upper|lower|split|join|replace|strip|find|title|startswith|endswith|format)\(|\bf[\"']|\[::-1\]"),
    ("Loops", 1, r"^\s*(for|while)\b"),
    ("Number Logic", 2, r"%\s*10\b|//=?\s*10\b|(?i:factorial|prime|fibonacci|palindrome|armstrong|gcd|lcm|divisor|factor)"),
    ("Lists", 2, r"\.(append|extend|insert|remove|pop|sort|reverse)\(|\blist\(|\bsorted\(|range\(len\(|\w\[(?![\"'])[^\]]+\]"),
    ("Frequency & Counting", 2, r"(?i)\bfreq|\bcount\w*(\[[^\]]*\])?\s*\+=\s*1|\.count\("),
    ("Tuples", 2, r"\btuple\(|^\s*\w+\s*=\s*\([^)]*,[^)]*\)"),
    ("Sets", 2, r"\bset\(|\.(add|union|intersection|difference|discard)\("),
    ("Dictionaries", 2, r"\.(items|keys|values|get|update|setdefault)\(|\bdict\(|=\s*\{|\[\{|\w\[[\"'][^\"']+[\"']\]"),
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
DIFF = {"Easy": ("Easy", "brightgreen", "🟢"),
        "Medium": ("Medium", "yellow", "🟡"),
        "Hard": ("Hard", "red", "🔴")}
# basic topics that appear in almost every solution; used only when picking "current topic"
GENERIC = {"Variables & Data Types", "User Input", "Operators & Math",
           "Conditionals", "Loops", "Functions"}
# input-reading lines are ignored for topic detection (they show up in every cell)
BOILER = re.compile(r"input\(|\[\s*int\(\s*\w+\s*\)\s*for\s+\w+\s+in\s+\w+\s*\]")

def matches(check, code):
    return check(code) if callable(check) else re.search(check, code, re.M) is not None

def no_comments(code):
    return "\n".join(l for l in code.splitlines()
                     if l.strip() and not l.strip().startswith(("#", "%", "!")))

def clean(code):
    return "\n".join(l for l in no_comments(code).splitlines() if not BOILER.search(l))

def comment_meta(src):
    """Reads the title and difficulty (Easy/Medium/Hard) from a cell's comment lines."""
    title, diff = None, None
    for l in src.splitlines():
        s = l.strip()
        if not s.startswith("#"):
            continue
        text = s.lstrip("#").strip()
        if not text:
            continue
        if title is None:
            m = re.match(r"Q\s*\d+\s*[:.]\s*(?:\d+\.\s*)?(.+)", text)
            title = (m.group(1) if m else text)[:70].strip()
        found = re.findall(r"\b(Easy|Medium|Hard)\b", text, re.I)
        if found:
            diff = max((f.capitalize() for f in found), key=["Easy", "Medium", "Hard"].index)
    return title, diff

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

def pick_topic(hits):
    specific = [i for i in hits if TOPICS[i][0] not in GENERIC]
    return max(specific or hits)

# ---------- analyse notebooks ----------
counts = {t[0]: 0 for t in TOPICS}
diff_mix = {"Easy": 0, "Medium": 0, "Hard": 0}
nb_info = []   # (file name, code cells, last topic index, last title, last difficulty)
for path in sorted(glob.glob(f"{NB_DIR}/*.ipynb"), key=git_time):
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    code_cells, last_hit, last_title, last_diff = 0, None, None, None
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
        raw = no_comments(src)
        if not raw:
            continue
        code_cells += 1
        title, diff = comment_meta(src)
        if title:
            last_title = title
        if diff:
            last_diff = diff
            diff_mix[diff] += 1
        hit = [i for i, t in enumerate(TOPICS)
               if matches(t[2], raw if t[0] == "User Input" else code)]
        for i in hit:
            counts[TOPICS[i][0]] += 1
        real = [i for i in hit if TOPICS[i][0] != "User Input"]
        if real:
            last_hit = pick_topic(real)
    nb_info.append((path.split("/")[-1], code_cells, last_hit, last_title, last_diff))

latest = next((n for n in reversed(nb_info) if n[2] is not None), None)
if latest:
    idx, latest_title, latest_diff = latest[2], latest[3], latest[4]
    latest_name, lvl = TOPICS[idx][0], TOPICS[idx][1]
else:
    latest_name, lvl, latest_title, latest_diff = "Getting started", 1, None, None
newest = nb_info[-1] if nb_info else None
if newest and newest[3]:
    latest_title = newest[3]          # newest notebook's latest question, even if unsolved
if newest and newest[4]:
    latest_diff = newest[4]
latest_title = latest_title or latest_name
lvl_name, lvl_color, lvl_emoji = DIFF[latest_diff] if latest_diff else LEVELS[lvl]

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

mix = ""
if sum(diff_mix.values()):
    mix = ("**Question difficulty mix:** "
           + " · ".join(f"{DIFF[k][2]} {k} {v}" for k, v in diff_mix.items()))

nb_rows = []
for fname, cells, _, _, _ in nb_info:
    q = quote(fname)
    colab = f"https://colab.research.google.com/github/{USER}/{REPO}/blob/main/{NB_DIR}/{q}"
    nb_rows.append(f"| [{fname}]({NB_DIR}/{q}) | {cells} | "
                   f"[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({colab}) |")

series = visuals.history(NB_DIR)
growth_note = visuals.write_growth(series)
platforms_md = platforms.build()
now = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC")

readme = f"""{visuals.header(NAME, latest_name, lvl_name, cur_streak)}

<p align="center">
{badge("Difficulty", lvl_name, lvl_color, "python")}
{badge("Topics", f"{covered} of {len(TOPICS)}", "blue")}
{badge("Streak", f"{cur_streak} days", "orange")}
{badge("Days practiced", len(days), "success")}
</p>

## 📑 Table of Contents

- [Project Highlights](#project-highlights)
- [How to Use This Repository](#how-to-use-this-repository)
- [Live Dashboard](#live-dashboard)
- [Learning Growth](#learning-growth)
- [Topic Roadmap](#topic-roadmap)
- [Practice Distribution](#practice-distribution)
- [Notebooks](#notebooks)
- [Coding Platforms](#coding-platforms)
  - [LeetCode](#leetcode)
  - [HackerRank](#hackerrank)
- [Activity](#activity)

---

<a id="project-highlights"></a>
## 💡 Project Highlights

- **Python problem solving:** Practice programming fundamentals and progressively explore more advanced concepts.
- **Jupyter notebooks:** Keep exercises, examples, experiments, and solutions in an interactive format.
- **Workflow automation:** Use GitHub Actions to regenerate repository documentation when relevant files change.
- **Automated dashboards:** Generate topic-progress summaries, practice charts, and SVG visuals using Python.
- **API integration and caching:** Collect coding-platform statistics and retain previously synced data when requests fail.
- **Learning in public:** Document my learning journey, including practice exercises and ongoing progress, rather than showing only selected polished examples.

<a id="how-to-use-this-repository"></a>
## 🚀 How to Use This Repository

- **Browse notebooks:** Open the notebooks to explore my exercises, examples, and experiments.
- **Run online:** Use the Google Colab links in the notebook table to open supported notebooks in your browser.
- **Run locally:** Install Python and Jupyter to execute notebook cells on your computer.
- **Track progress:** Explore the dashboard, roadmap, and charts to see the topics detected in my practice notebooks.
- **Explore coding profiles:** Visit the linked LeetCode and HackerRank sections to review the displayed platform statistics.

### Run Locally

Clone the repository:

```bash
 git clone https://github.com/Phantom2101/Python-Daily-Practice.git
 cd Python-Daily-Practice
```

Install Jupyter Notebook:

```bash
python -m pip install notebook
```

Start Jupyter Notebook:

```bash
jupyter notebook
```

Open a notebook and run its cells. Some notebooks may require additional Python libraries; install those dependencies if prompted. These instructions assume Python is already installed.

<a id="live-dashboard"></a>
## 📊 Live Dashboard

| 🎯 Current topic | 📈 Difficulty | 📝 Latest question | 🔥 Streak | 🗓️ Days practiced | 🧮 Code cells |
|---|---|---|---|---|---|
| **{latest_name}** | {lvl_emoji} {lvl_name} | {latest_title} | {cur_streak} days | {len(days)} | {total_cells} |

> **How to read these metrics:** The practice-day count is based on distinct Git commit dates for files under `notebooks/`. The streak is calculated from those dates and counts consecutive days ending today or yesterday. It is not the same as activity on LeetCode or HackerRank.

<a id="learning-growth"></a>
## 📈 Learning Growth

<img src="assets/growth.svg" alt="Learning growth over time" width="100%"/>

{growth_note}

<a id="topic-roadmap"></a>
## 🗺️ Topic Roadmap

The roadmap is generated by analysing code patterns in the practice notebooks. Cell counts show where patterns were detected; they do **not** measure mastery or guarantee that a topic has been fully learned. The practice-depth bar and status are simple activity indicators based on detected cell counts.

| Level | Topic | Practice depth | Cells | Status |
|---|---|---|---|---|
{chr(10).join(rows)}

{mix}

<a id="practice-distribution"></a>
## 🥧 Practice Distribution

```mermaid
pie showData title Practice cells per topic
{pie}
```

<a id="notebooks"></a>
## 📓 Notebooks

Browse the original practice notebooks on GitHub, or use the Colab badge to open a notebook online. The notebooks are kept as a record of my learning process, including exercises and experiments.

| Notebook | Code cells | Run it |
|---|---|---|
{chr(10).join(nb_rows)}

<a id="coding-platforms"></a>
{platforms_md}

<a id="activity"></a>
## 🔥 GitHub Activity

<p align="center">
  <img src="https://streak-stats.demolab.com/?user={USER}&theme=tokyonight&hide_border=true" alt="GitHub contribution streak"/>
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/{USER}/{REPO}/output/github-snake-dark.svg" alt="GitHub contribution snake animation" width="100%"/>
</p>

---

<sub>Auto-generated on {now} by GitHub Actions from the practice notebooks and coding-platform data.</sub>
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)
print("README.md updated")
