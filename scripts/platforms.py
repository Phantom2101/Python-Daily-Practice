"""LeetCode + HackerRank section for the README."""
import json, os, time, datetime, urllib.request

LC_USER = "affankotwal"
HR_USER = "affankotwal"
CACHE = "data/platforms.json"
MANUAL_HR = "data/hackerrank.json"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
EMOJI = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴", "?": "⚪"}
COLORS = {"Easy": "#00b8a3", "Medium": "#ffc01e", "Hard": "#ef4743"}

def _http(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def _lc(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    out = _http("https://leetcode.com/graphql", body,
                {"Content-Type": "application/json", "Referer": "https://leetcode.com/"})
    return out["data"]

Q_PROFILE = """query p($u:String!){
  matchedUser(username:$u){ profile{ranking} submitStatsGlobal{acSubmissionNum{difficulty count}} }
  recentAcSubmissionList(username:$u, limit:20){ title titleSlug timestamp }
  allQuestionsCount{ difficulty count }
}"""
Q_DIFF = "query q($s:String!){ question(titleSlug:$s){ difficulty } }"

def fetch_leetcode():
    d = _lc(Q_PROFILE, {"u": LC_USER})
    user = d.get("matchedUser")
    if not user:
        raise ValueError("LeetCode user not found, or profile is private")
    solved = {x["difficulty"]: x["count"] for x in user["submitStatsGlobal"]["acSubmissionNum"]}
    total = {x["difficulty"]: x["count"] for x in (d.get("allQuestionsCount") or [])}
    seen, recent = set(), []
    for s in d.get("recentAcSubmissionList") or []:
        if s["titleSlug"] in seen:
            continue
        seen.add(s["titleSlug"])
        try:
            diff = _lc(Q_DIFF, {"s": s["titleSlug"]})["question"]["difficulty"]
        except Exception:
            diff = "?"
        time.sleep(0.3)
        recent.append({"title": s["title"], "slug": s["titleSlug"],
                       "difficulty": diff, "ts": int(s["timestamp"])})
        if len(recent) == 10:
            break
    counts = {}
    for r in recent:
        counts[r["difficulty"]] = counts.get(r["difficulty"], 0) + 1
    rank = {"Easy": 1, "Medium": 2, "Hard": 3}
    current = max((k for k in counts if k in rank),
                  key=lambda k: (counts[k], rank[k]), default="-")
    return {"solved": solved, "total": total, "recent": recent, "current": current,
            "ranking": (user.get("profile") or {}).get("ranking")}

def fetch_hackerrank():
    d = _http(f"https://www.hackerrank.com/rest/hackers/{HR_USER}/badges")
    badges = [{"name": m.get("badge_name"), "stars": int(m.get("stars") or 0),
               "solved": m.get("solved")} for m in d.get("models", [])]
    if not badges:
        raise ValueError("no badges returned")
    return {"badges": badges, "source": "auto"}

def manual_hackerrank():
    if not os.path.exists(MANUAL_HR):
        return None
    with open(MANUAL_HR, encoding="utf-8") as f:
        d = json.load(f)
    d["source"] = "manual"
    return d

def _milestone(n):
    for m in (10, 25, 50, 100, 150, 200, 300, 500, 1000):
        if n < m:
            return m
    return n + 100

CSS = """
text{font-family:monospace;fill:#8b9bb4;font-size:13px}
.big{fill:#00f7ff;font-size:44px;font-weight:bold}
.tag{fill:#e6f1ff;font-size:14px}
.bar{transform-box:fill-box;transform-origin:left;animation:grow 1.4s ease-out both}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.glow{animation:glow 2.4s ease-in-out infinite}
@keyframes glow{50%{opacity:.55}}
"""

def write_lc_svg(lc, path="assets/leetcode.svg"):
    os.makedirs("assets", exist_ok=True)
    W, H = 820, 250
    rows = ""
    for i, k in enumerate(("Easy", "Medium", "Hard")):
        n = lc["solved"].get(k, 0)
        m = _milestone(n)
        y = 105 + i * 42
        w = 430 * n / m
        rows += (f'<text x="40" y="{y+14}">{k}</text>'
                 f'<rect x="130" y="{y}" width="430" height="18" rx="9" fill="#1f2a44"/>'
                 f'<rect class="bar" style="animation-delay:{0.3*i}s" x="130" y="{y}" '
                 f'width="{w:.1f}" height="18" rx="9" fill="{COLORS[k]}"/>'
                 f'<text x="575" y="{y+14}">{n} solved, next milestone {m}</text>')
    rank = f"Global rank {lc['ranking']:,}" if lc.get("ranking") else ""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%">'
           '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#141b2d"/>'
           f'</linearGradient></defs><style>{CSS}</style>'
           f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>'
           f'<text class="big glow" x="40" y="70">{lc["solved"].get("All", 0)}</text>'
           '<text class="tag" x="130" y="48">problems solved on LeetCode</text>'
           f'<text class="tag" x="130" y="68">Current difficulty: {lc["current"]}</text>'
           f'<text x="130" y="86">{rank}</text>'
           + rows + '</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)

def _lc_md(lc, note):
    write_lc_svg(lc)
    out = [f"### 🟠 LeetCode: [@{LC_USER}](https://leetcode.com/u/{LC_USER})", "",
           '<img src="assets/leetcode.svg" alt="LeetCode stats" width="100%"/>', ""]
    if note:
        out += [note, ""]
    if lc["recent"]:
        out += ["| Recently solved | Difficulty | Date |", "|---|---|---|"]
        for r in lc["recent"]:
            date = datetime.datetime.fromtimestamp(r["ts"], datetime.timezone.utc).strftime("%d %b %Y")
            out.append(f"| [{r['title']}](https://leetcode.com/problems/{r['slug']}/) | "
                       f"{EMOJI.get(r['difficulty'], '⚪')} {r['difficulty']} | {date} |")
    else:
        out.append("_No solved problems yet. Your first one will appear here automatically._")
    return "\n".join(out)

def _hr_md(hr, note):
    out = [f"### 🟢 HackerRank: [@{HR_USER}](https://www.hackerrank.com/profile/{HR_USER})", ""]
    if not hr:
        out.append("_Profile linked. Badges will appear here once data is available._")
        return "\n".join(out)
    if hr.get("current_level"):
        out += [f"**Current level:** {hr['current_level']}", ""]
    if hr.get("solved"):
        out += [f"**Challenges solved:** {hr['solved']}", ""]
    if hr.get("badges"):
        out += ["| Badge | Stars | Solved |", "|---|---|---|"]
        for b in hr["badges"]:
            out.append(f"| {b.get('name')} | {'⭐' * int(b.get('stars') or 0) or '-'} | {b.get('solved', '-')} |")
        out.append("")
    if hr.get("recent"):
        out += ["**Recent challenges:**"] + [f"- {x}" for x in hr["recent"]] + [""]
    if note:
        out.append(note)
    return "\n".join(out)

def build():
    os.makedirs("data", exist_ok=True)
    cache = {}
    if os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y")
    lc_note = hr_note = ""

    try:
        lc = fetch_leetcode()
        cache["leetcode"], cache["leetcode_synced"] = lc, now
    except Exception as e:
        print("LeetCode fetch failed:", repr(e))
        lc = cache.get("leetcode")
        lc_note = f"_Showing last synced data ({cache.get('leetcode_synced', 'earlier')})._"

    try:
        hr = fetch_hackerrank()
        cache["hackerrank"], cache["hackerrank_synced"] = hr, now
    except Exception as e:
        print("HackerRank fetch failed:", repr(e))
        hr = manual_hackerrank() or cache.get("hackerrank")
        if hr and hr.get("source") != "manual":
            hr_note = f"_Showing last synced data ({cache.get('hackerrank_synced', 'earlier')})._"

    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    lc_badge = (f'<a href="https://leetcode.com/u/{LC_USER}"><img src="https://img.shields.io/badge/'
                f'LeetCode-{LC_USER}-FFA116?style=for-the-badge&logo=leetcode&logoColor=black"/></a>')
    hr_badge = (f'<a href="https://www.hackerrank.com/profile/{HR_USER}"><img src="https://img.shields.io/badge/'
                f'HackerRank-{HR_USER}-00EA64?style=for-the-badge&logo=hackerrank&logoColor=black"/></a>')
    parts = ["## 🧩 Coding Platforms", "", f'<p align="center">{lc_badge} {hr_badge}</p>', ""]
    parts.append(_lc_md(lc, lc_note) if lc else
                 f"### 🟠 LeetCode: [@{LC_USER}](https://leetcode.com/u/{LC_USER})\n\n_Stats will appear after the first successful sync._")
    parts += ["", _hr_md(hr, hr_note), ""]
    return "\n".join(parts)
