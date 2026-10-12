"""Animated visuals for the README."""
import json, os, subprocess
from urllib.parse import quote_plus

CSS = """
.line{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.5s ease-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.area{opacity:0;animation:fade 1.5s 1.5s forwards}
@keyframes fade{to{opacity:1}}
.pulse{animation:pulse 1.6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes pulse{50%{transform:scale(1.9);opacity:.35}}
text{font-family:monospace;fill:#8b9bb4;font-size:12px}
.title{fill:#e6f1ff;font-size:15px;font-weight:bold}
"""

def header(name, topic, level, streak):
    lines = [f"Currently learning: {topic}", f"Level: {level}",
             f"Streak: {streak} days", "Showing up every day"]
    typing = ";".join(quote_plus(l) for l in lines)
    title = quote_plus("Python Practice Journey")
    desc = quote_plus(f"{name}'s learning log")
    return f"""<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=200&color=0:00f7ff,100:7b2ff7&text={title}&fontColor=ffffff&fontSize=44&animation=fadeIn&fontAlignY=38&desc={desc}&descAlignY=58&descSize=18" width="100%" alt="header"/>
</p>
<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=1000&color=00F7FF&center=true&vCenter=true&width=600&lines={typing}" alt="typing"/>
</p>"""

def _count_cells(raw):
    try:
        nb = json.loads(raw)
    except Exception:
        return 0
    n = 0
    for c in nb.get("cells", []):
        if c.get("cell_type") != "code":
            continue
        src = c.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        if "userdata.get" in src:
            continue
        if any(l.strip() and not l.strip().startswith(("#", "%", "!"))
               for l in src.splitlines()):
            n += 1
    return n

def history(nb_dir):
    """Total code cells at the end of each practice day, from git history."""
    def run(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True).stdout
    last = {}
    for line in run("log", "--reverse", "--format=%H %ad", "--date=short", "--", nb_dir).splitlines():
        h, d = line.split()
        last[d] = h
    series = []
    for d, h in sorted(last.items()):
        total = 0
        for p in run("ls-tree", "--name-only", h, f"{nb_dir}/").splitlines():
            if p.endswith(".ipynb"):
                total += _count_cells(run("show", f"{h}:{p}"))
        series.append((d, total))
    return series

def write_growth(series, path="assets/growth.svg"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H, P = 820, 300, 55
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%">'
            '<defs>'
            '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#141b2d"/></linearGradient>'
            '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00f7ff" stop-opacity="0.35"/><stop offset="1" stop-color="#00f7ff" stop-opacity="0"/></linearGradient>'
            '<filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            f'</defs><style>{CSS}</style>'
            f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>'
            f'<text class="title" x="{P}" y="32">Learning growth: total code cells over time</text>')
    n = len(series)
    if n < 2:
        svg = head + (f'<text class="pulse" x="{W/2}" y="{H/2}" text-anchor="middle" '
                      'style="fill:#00f7ff;font-size:16px">Growth chart unlocks after your 2nd practice day</text></svg>')
        open(path, "w", encoding="utf-8").write(svg)
        return "_The growth graph fills in as you practice on more days._"

    vals = [v for _, v in series]
    top = max(max(vals), 1)
    xs = [P + i * (W - 2 * P) / (n - 1) for i in range(n)]
    ys = [H - P - v / top * (H - 2 * P) for v in vals]
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = line + f" L{xs[-1]:.1f},{H-P} L{xs[0]:.1f},{H-P} Z"
    grid = ""
    for k in range(5):
        y = P + k * (H - 2 * P) / 4
        grid += (f'<line x1="{P}" y1="{y:.1f}" x2="{W-P}" y2="{y:.1f}" stroke="#1f2a44" stroke-dasharray="4 4"/>'
                 f'<text x="{P-10}" y="{y+4:.1f}" text-anchor="end">{round(top*(1-k/4))}</text>')
    step = max(1, n // 6)
    labels = "".join(f'<text x="{xs[i]:.1f}" y="{H-P+22}" text-anchor="middle">{series[i][0][5:]}</text>'
                     for i in range(0, n, step))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#00f7ff"><title>{d}: {v} cells</title></circle>'
                   for (d, v), x, y in zip(series, xs, ys))
    body = (grid + labels +
            f'<path class="area" d="{area}" fill="url(#area)"/>'
            f'<path class="line" pathLength="1" d="{line}" fill="none" stroke="#00f7ff" stroke-width="3" filter="url(#glow)"/>'
            + dots +
            f'<circle class="pulse" cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="6" fill="#ff4ecd"/></svg>')
    open(path, "w", encoding="utf-8").write(head + body)

    gained = vals[-1] - vals[0]
    avg = gained / (n - 1)
    return (f"**{vals[-1]}** code cells so far across **{n}** practice days, "
            f"averaging **{avg:+.1f} cells per day** since the first push.")
