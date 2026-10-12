"""LeetCode + HackerRank (Python track) section for the README."""
import json, os, time, datetime, urllib.request

LC_USER = "affankotwal"
HR_USER = "affankotwal"
HR_ONLY_PYTHON = True            # only list HackerRank problems from the Python track
CACHE = "data/platforms.json"
MANUAL_HR = "data/hackerrank.json"
SHOW = 15                        # rows shown in each "recently solved" table
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
EMOJI = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴", "?": "⚪"}
COLORS = {"Easy": "#00b8a3", "Medium": "#ffc01e", "Hard": "#ef4743"}
RANK = {"Easy": 1, "Medium": 2, "Hard": 3}

def _http(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def _ts(value):
    """Turns a timestamp (number or ISO text) into epoch seconds."""
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return int(time.time())

def _date(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%d %b %Y")

def _current_level(items):
    """Difficulty you solved most among your last 10 problems (ties go to the harder one)."""
    counts = {}
    for r in items[:10]:
        counts[r["difficulty"]] = counts.get(r["difficulty"], 0) + 1
    return max((k for k in counts if k in RANK),
               key=lambda k: (counts[k], RANK[k]), default="-")

def _milestone(n):
    for m in (10, 25, 50, 100, 150, 200, 300, 500, 1000):
        if n < m:
            return m
    return n + 100

# ---------------- LeetCode ----------------
def _lc(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    out = _http("https://leetcode.com/graphql", body,
                {"Content-Type": "application/json", "Referer": "https://leetcode.com/"})
    return out["data"]

Q_PROFILE = """query p($u:String!){
  matchedUser(username:$u){ profile{ranking} submitStatsGlobal{acSubmissionNum{difficulty count}} }
  recentAcSubmissionList(username:$u, limit:20){ title titleSlug timestamp }
}"""
Q_DIFF = "query q($s:String!){ question(titleSlug:$s){ difficulty } }"

def fetch_leetcode(history):
    d = _lc(Q_PROFILE, {"u": LC_USER})
    user = d.get("matchedUser")
    if not user:
        raise ValueError("LeetCode user not found, or profile is private")
    solved = {x["difficulty"]: x["count"] for x in user["submitStatsGlobal"]["acSubmissionNum"]}
    for s in d.get("recentAcSubmissionList") or []:
        slug, ts = s["titleSlug"], int(s["timestamp"])
        if slug in history:
            history[slug]["ts"] = max(history[slug]["ts"], ts)
            continue
        try:
            diff = _lc(Q_DIFF, {"s": slug})["question"]["difficulty"]
        except Exception:
            diff = "?"
        time.sleep(0.3)
        history[slug] = {"title": s["title"], "difficulty": diff, "ts": ts}
    return {"solved": solved, "ranking": (user.get("profile") or {}).get("ranking")}

# ---------------- HackerRank ----------------
def _hr(path):
    return _http(f"https://www.hackerrank.com/rest/{path}")

def fetch_hackerrank(history, info):
    d = _hr(f"hackers/{HR_USER}/badges")
    badges = [{"name": m.get("badge_name"), "stars": int(m.get("stars") or 0),
               "solved": m.get("solved")} for m in d.get("models", [])]
    print("HR badges:", [(b["name"], b["solved"]) for b in badges])
    cursor = ""
    for page in range(3):                           # up to 3 pages of recent challenges
        r = _hr(f"hackers/{HR_USER}/recent_challenges?limit=20&cursor={cursor}&response_type=recent")
        models = r.get("models", [])
        print(f"HR recent page {page}: {len(models)} challenges; keys:",
              list(models[0].keys())[:12] if models else "none")
        for m in models:
            slug = m.get("ch_slug") or m.get("slug")
            if not slug:
                print("HR skipped, no slug:", list(m.keys())[:12])
                continue
            ts = _ts(m.get("created_at"))
            if slug in history:
                history[slug]["ts"] = max(history[slug]["ts"], ts)
                continue
            if slug not in info or not info[slug].get("track"):    # retry failed lookups
                try:
                    model = _hr(f"contests/master/challenges/{slug}").get("model", {})
                    info[slug] = {"difficulty": (model.get("difficulty_name") or "?").capitalize(),
                                  "track": (model.get("track") or {}).get("name", ""),
                                  "title": model.get("name") or m.get("name") or slug}
                    print("HR detail:", slug, info[slug]["track"], info[slug]["difficulty"])
                except Exception as e:
                    print("HR detail failed:", slug, repr(e))
                    info[slug] = {"difficulty": "?", "track": "", "title": m.get("name") or slug}
                time.sleep(0.3)
            c = info[slug]
            if HR_ONLY_PYTHON and "python" not in (c["track"] or "").lower():
                print("HR skipped, track is not Python:", slug, repr(c["track"]))
                continue
            history[slug] = {"title": c["title"], "difficulty": c["difficulty"], "ts": ts}
        cursor = r.get("cursor") or ""
        if r.get("last_page", True) or not cursor:
            break
    if not badges and not history:
        raise ValueError("no data returned (HackerRank may be blocking automated requests)")
    return {"badges": badges}

def manual_hackerrank():
    if not os.path.exists(MANUAL_HR):
        return {}
    try:
        with open(MANUAL_HR, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Could not read", MANUAL_HR, repr(e))
        return {}

# ---------------- visuals ----------------
CSS = """
text{font-family:monospace;fill:#8b9bb4;font-size:13px}
.big{fill:#00f7ff;font-size:44px;font-weight:bold}
.tag{fill:#e6f1ff;font-size:14px}
.bar{transform-box:fill-box;transform-origin:left;animation:grow 1.4s ease-out both}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.glow{animation:glow 2.4s ease-in-out infinite}
@keyframes glow{50%{opacity:.55}}
"""

def write_card(path, headline, total, bars, current, subtitle):
    os.makedirs("assets", exist_ok=True)
    W, H = 820, 250
    rows = ""
    for i, k in enumerate(("Easy", "Medium", "Hard")):
        n = bars.get(k, 0)
        m = _milestone(n)
        y = 105 + i * 42
        rows += (f'<text x="40" y="{y+14}">{k}</text>'
                 f'<rect x="130" y="{y}" width="430" height="18" rx="9" fill="#1f2a44"/>'
                 f'<rect class="bar" style="animation-delay:{0.3*i}s" x="130" y="{y}" '
                 f'width="{430*n/m:.1f}" height="18" rx="9" fill="{COLORS[k]}"/>'
                 f'<text x="575" y="{y+14}">{n} solved, next milestone {m}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%">'
           '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#141b2d"/>'
           f'</linearGradient></defs><style>{CSS}</style>'
           f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>'
           f'<text class="big glow" x="40" y="70">{total}</text>'
           f'<text class="tag" x="130" y="48">{headline}</text>'
           f'<text class="tag" x="130" y="68">Current difficulty: {current}</text>'
           f'<text x="130" y="86">{subtitle}</text>'
           + rows + '</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)

def _table(items, url_fn):
    if not items:
        return "_No solved problems yet. Your first one will appear here automatically._"
    out = ["| Recently solved | Difficulty | Date |", "|---|---|---|"]
    for r in items[:SHOW]:
        out.append(f"| [{r['title']}]({url_fn(r)}) | "
                   f"{EMOJI.get(r['difficulty'], '⚪')} {r['difficulty']} | {_date(r['ts'])} |")
    return "\n".join(out)

def _items(history):
    out = [dict(v, slug=k) for k, v in history.items()]
    return sorted(out, key=lambda r: -r["ts"])

def _mix(items):
    mix = {"Easy": 0, "Medium": 0, "Hard": 0}
    for r in items:
        if r["difficulty"] in mix:
            mix[r["difficulty"]] += 1
    return mix

def lc_section(lc, history, note):
    items = _items(history)
    head = [f"### 🟠 LeetCode: [@{LC_USER}](https://leetcode.com/u/{LC_USER})", ""]
    if not lc:
        return "\n".join(head + ["_Stats will appear after the first successful sync._"])
    s = lc["solved"]
    rank = f"Global rank {lc['ranking']:,}" if lc.get("ranking") else ""
    write_card("assets/leetcode.svg", "problems solved on LeetCode", s.get("All", 0),
               {k: s.get(k, 0) for k in RANK}, _current_level(items), rank)
    out = head + ['<img src="assets/leetcode.svg" alt="LeetCode stats" width="100%"/>', ""]
    if note:
        out += [note, ""]
    out.append(_table(items, lambda r: f"https://leetcode.com/problems/{r['slug']}/"))
    return "\n".join(out)

def hr_section(hr, history, manual, note):
    hist = dict(history)
    for p in manual.get("problems", []):
        key = p.get("slug") or p.get("title")
        if key and key not in hist:
            hist[key] = {"title": p.get("title", key), "difficulty": p.get("difficulty", "?"),
                         "ts": _ts(p.get("date")), "nolink": not p.get("slug")}
    items = _items(hist)
    badges = (hr or {}).get("badges", []) or manual.get("badges", [])
    py = next((b for b in badges if (b.get("name") or "").lower() == "python"), {})
    total = max(len(items), int(py.get("solved") or 0), int(manual.get("python_solved") or 0))
    stars = int(py.get("stars") or manual.get("stars") or 0)
    head = [f"### 🟢 HackerRank (Python): [@{HR_USER}](https://www.hackerrank.com/profile/{HR_USER})", ""]
    if not items and not total:
        return "\n".join(head + ["_Profile linked. Python problems will appear here once data is available._"])
    write_card("assets/hackerrank.svg", "Python problems solved on HackerRank", total,
               _mix(items), _current_level(items), ("⭐" * stars) + (" Python badge" if stars else ""))
    out = head + ['<img src="assets/hackerrank.svg" alt="HackerRank Python stats" width="100%"/>', ""]
    out.append("_Difficulty bars count the problems listed below; the big number comes from your Python badge._")
    out.append("")
    if note:
        out += [note, ""]
    out.append(_table(items, lambda r: f"https://www.hackerrank.com/profile/{HR_USER}"
                      if r.get("nolink") else
                      f"https://www.hackerrank.com/challenges/{r['slug']}/problem"))
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
    lc_hist = cache.setdefault("lc_history", {})
    hr_hist = cache.setdefault("hr_history", {})
    hr_info = cache.setdefault("hr_challenge_info", {})
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y")
    lc_note = hr_note = ""

    try:
        lc = fetch_leetcode(lc_hist)
        cache["leetcode"], cache["leetcode_synced"] = lc, now
    except Exception as e:
        print("LeetCode fetch failed:", repr(e))
        lc = cache.get("leetcode")
        lc_note = f"_Showing last synced data ({cache.get('leetcode_synced', 'earlier')})._"

    try:
        hr = fetch_hackerrank(hr_hist, hr_info)
        cache["hackerrank"], cache["hackerrank_synced"] = hr, now
    except Exception as e:
        print("HackerRank fetch failed:", repr(e))
        hr = cache.get("hackerrank")
        if hr:
            hr_note = f"_Showing last synced data ({cache.get('hackerrank_synced', 'earlier')})._"

    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    lc_badge = (f'<a href="https://leetcode.com/u/{LC_USER}"><img src="https://img.shields.io/badge/'
                f'LeetCode-{LC_USER}-FFA116?style=for-the-badge&logo=leetcode&logoColor=black"/></a>')
    hr_badge = (f'<a href="https://www.hackerrank.com/profile/{HR_USER}"><img src="https://img.shields.io/badge/'
                f'HackerRank-{HR_USER}-00EA64?style=for-the-badge&logo=hackerrank&logoColor=black"/></a>')
    return "\n".join(["## 🧩 Coding Platforms", "", f'<p align="center">{lc_badge} {hr_badge}</p>', "",
                      lc_section(lc, lc_hist, lc_note), "",
                      hr_section(hr, hr_hist, manual_hackerrank(), hr_note), ""])
