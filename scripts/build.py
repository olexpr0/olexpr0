#!/usr/bin/env python3
"""Builds the animated SVGs for the profile README.

Standard library only. Run by .github/workflows/update.yml every 6 hours.
The pipeline and ledger SVGs are fed with real public commit data, so the
README keeps itself current: the profile is a small agent.
"""
import datetime as dt
import hashlib
import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "olexpr0")
OUT = Path(__file__).resolve().parent.parent / "assets"
DIFFICULTY = 3  # leading zero hex digits required in every block hash

BG, PANEL, LINE = "#07080c", "#0c0e14", "#1c2030"
TEXT, DIM = "#e8ecf4", "#7a8399"
LIME, ORANGE, ICE = "#d4ff3a", "#ff5a1f", "#7df9ff"
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# Used when the API is unreachable, so a build never fails.
FALLBACK = [
    {"repo": "olexpr0/snake-game", "sha": "8f3c1d2", "msg": "feat: simple snake game", "date": "2026-09-04T20:35:13+02:00"},
    {"repo": "olexpr0/snake-game", "sha": "b19a77e", "msg": "feat: with autoplayer and green color", "date": "2026-09-04T21:09:38+02:00"},
    {"repo": "react-sweat/star-wars-tug-wars-backend", "sha": "44d0e19", "msg": "Initial commit", "date": "2026-02-12T14:07:04+01:00"},
    {"repo": "react-sweat/memory-leak-game", "sha": "c7a2f50", "msg": "Initial commit", "date": "2026-02-13T10:51:24+01:00"},
    {"repo": "react-sweat/memory-leak-game-for-deploy", "sha": "09be3d4", "msg": "Initial commit", "date": "2026-02-13T10:51:24+01:00"},
]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def clip(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------- data

def fetch_commits():
    url = f"https://api.github.com/search/commits?q=author:{USER}&sort=author-date&order=desc&per_page=30"
    headers = {"User-Agent": "profile-agent", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            data = json.load(r)
        items = [
            {
                "repo": i["repository"]["full_name"],
                "sha": i["sha"][:7],
                "msg": i["commit"]["message"].splitlines()[0],
                "date": i["commit"]["author"]["date"],
            }
            for i in data.get("items", [])
        ]
        if items:
            return items, int(data.get("total_count", len(items))), True
    except Exception as exc:  # network, rate limit, parse
        print("api failed, using fallback:", exc)
    return list(FALLBACK), len(FALLBACK), False


def mine(prev, payload):
    nonce = 0
    while True:
        h = hashlib.sha256(f"{prev}|{payload}|{nonce}".encode()).hexdigest()
        if h.startswith("0" * DIFFICULTY):
            return h, nonce
        nonce += 1


def build_chain(commits, total):
    newest = commits[:5]
    oldest_first = list(reversed(newest))
    first_no = max(total - len(newest) + 1, 1)
    blocks, prev = [], "0" * 64
    for i, c in enumerate(oldest_first):
        payload = f"{c['repo']}|{c['sha']}|{c['msg']}|{c['date']}"
        h, nonce = mine(prev, payload)
        blocks.append({**c, "no": first_no + i, "hash": h, "prev": prev, "nonce": nonce})
        prev = h
    return blocks


def short(h):
    return f"0x{h[:6]}…{h[-4:]}"


# --------------------------------------------------------------- helpers

def keyed(points):
    """points: [(t, value)] -> (keyTimes, values) with t in 0..1, strictly increasing."""
    pts = sorted(points)
    if pts[0][0] > 0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < 1:
        pts.append((1.0, pts[-1][1]))
    out, last = [], -1
    for t, v in pts:
        t = round(min(max(t, 0), 1), 4)
        if t <= last:
            t = round(last + 0.0001, 4)
        out.append((t, v))
        last = t
    out[-1] = (1.0, out[-1][1])
    return ";".join(str(t) for t, _ in out), ";".join(str(v) for _, v in out)


def animate(attr, points, dur, extra=""):
    kt, vs = keyed(points)
    return f'<animate attributeName="{attr}" values="{vs}" keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite" {extra}/>'


def head(w, h, title, desc):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT}" role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title>'
        f'<desc id="d">{esc(desc)}</desc>'
    )


COMMON_DEFS = f"""
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="14"/></filter>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#12151f" stroke-width="1"/></pattern>
<radialGradient id="aura"><stop offset="0" stop-color="{LIME}" stop-opacity=".30"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>
"""


def frame(w, h):
    return (
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="20" fill="{BG}" stroke="{LINE}"/>'
        f'<g clip-path="url(#frame)"><rect width="{w}" height="{h}" fill="url(#grid)"/>'
    )


def clipdef(w, h):
    return f'<clipPath id="frame"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="20"/></clipPath>'


# --------------------------------------------------------------- banner

def banner():
    W, H = 1200, 340
    lines = ["full-stack developer", "builds agents that do the boring part", "writing a blockchain in Rust"]
    cw = 15.6  # char width at font-size 26
    DUR = 15
    typed, clips = [], []
    for i, line in enumerate(lines):
        full = (len(line) + 2) * cw
        t0 = i / 3
        pts = [(0, 0), (t0, 0), (t0 + 0.07, full), (t0 + 0.29, full), (t0 + 0.31, 0)]
        if i == 0:
            pts = [(0, 0), (0.07, full), (0.29, full), (0.31, 0)]
        clips.append(
            f'<clipPath id="ty{i}"><rect x="48" y="196" height="40" width="0">{animate("width", pts, DUR)}</rect></clipPath>'
        )
        caret_pts = [(t, 48 + w) for t, w in pts]
        typed.append(
            f'<text x="48" y="224" font-size="26" fill="{LIME}" textLength="{full:.1f}" lengthAdjust="spacing" clip-path="url(#ty{i})" filter="url(#glow)">&gt; {esc(line)}</text>'
            f'<rect x="48" y="203" width="12" height="26" fill="{LIME}" opacity=".9">{animate("x", caret_pts, DUR)}'
            f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>'
        )

    gl = lambda color, dx: (  # noqa: E731
        f'<text x="48" y="156" font-size="88" font-weight="800" letter-spacing="4" fill="{color}" opacity="0">ALEX BLITZ'
        f'{animate("opacity", [(0, 0), (0.9, 0), (0.905, .75), (0.915, 0), (0.93, .75), (0.94, 0), (1, 0)], 5)}'
        f'{animate("x", [(0, 48), (0.9, 48), (0.905, 48 + dx), (0.915, 48 - dx), (0.93, 48 + dx * 1.6), (0.94, 48), (1, 48)], 5)}</text>'
    )

    rings = (
        f'<g transform="translate(985 170)">'
        f'<circle r="128" fill="none" stroke="{LINE}" stroke-width="1"/>'
        f'<g><circle r="118" fill="none" stroke="{LIME}" stroke-width="1.5" stroke-dasharray="3 14" opacity=".8"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="40s" repeatCount="indefinite"/></g>'
        f'<g><circle r="86" fill="none" stroke="{ICE}" stroke-width="1" stroke-dasharray="40 10 4 10" opacity=".7"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="26s" repeatCount="indefinite"/></g>'
        f'<g><polygon points="0,-58 50,-29 50,29 0,58 -50,29 -50,-29" fill="none" stroke="{LIME}" stroke-width="2" filter="url(#glow)"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="18s" repeatCount="indefinite"/></g>'
        f'<g><polygon points="0,-34 29,-17 29,17 0,34 -29,17 -29,-17" fill="{LIME}" fill-opacity=".08" stroke="{ORANGE}" stroke-width="1.5"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="9s" repeatCount="indefinite"/></g>'
        f'<circle r="9" fill="{LIME}" filter="url(#glow)"><animate attributeName="r" values="7;11;7" dur="2.4s" repeatCount="indefinite"/></circle>'
        f'<g><circle cx="118" r="5" fill="{LIME}" filter="url(#glow)"/><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="7s" repeatCount="indefinite"/></g>'
        f'<g><circle cx="86" r="4" fill="{ICE}" filter="url(#glow)"/><animateTransform attributeName="transform" type="rotate" from="140" to="500" dur="11s" repeatCount="indefinite"/></g>'
        f'<g><circle cx="128" r="3" fill="{ORANGE}" filter="url(#glow)"/><animateTransform attributeName="transform" type="rotate" from="250" to="-110" dur="15s" repeatCount="indefinite"/></g>'
        f'</g>'
    )

    return (
        head(W, H, "Alex Blitz", "Animated banner: Alex Blitz, full-stack developer building agents and automation.")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}{''.join(clips)}</defs>"
        + frame(W, H)
        + f'<circle cx="985" cy="170" r="260" fill="url(#aura)">{animate("opacity", [(0, .55), (.5, 1), (1, .55)], 6)}</circle>'
        + f'<rect width="{W}" height="2" fill="{LIME}" opacity=".16">{animate("y", [(0, -4), (1, H)], 7)}</rect>'
        # status row
        + f'<circle cx="52" cy="54" r="4.5" fill="{LIME}" filter="url(#glow)"><animate attributeName="opacity" values="1;.25;1" dur="1.6s" repeatCount="indefinite"/></circle>'
        + f'<text x="66" y="58" font-size="13" fill="{DIM}" letter-spacing="2">ONLINE · POLAND · STUDENT · SHIPPING DAILY</text>'
        + gl(ORANGE, 5) + gl(ICE, -5)
        + f'<text x="48" y="156" font-size="88" font-weight="800" letter-spacing="4" fill="{TEXT}">ALEX BLITZ</text>'
        + "".join(typed)
        + f'<text x="48" y="294" font-size="13" fill="{DIM}" letter-spacing="1">github.com/{USER}  ·  alexblitz.vercel.app</text>'
        + f'<text x="48" y="314" font-size="13" fill="{DIM}">react · typescript · node · python · go · linux</text>'
        + rings
        + "</g></svg>"
    )


# --------------------------------------------------------------- stack marquee

def stack():
    W, H = 1200, 168
    row1 = ["React", "TypeScript", "Next.js", "Node.js", "Express", "NestJS", "FastAPI", "Django", "Go", "PHP",
            "PostgreSQL", "MySQL", "SQL Server", "Python", "Linux", "Bash"]
    row2 = [("AI agents", 0), ("Hermes Agent", 0), ("OpenClaw", 0), ("workflow bots", 0), ("trading bots", 0),
            ("Flipper Zero", 0), ("firmware", 0), ("AI video pipeline", 0),
            ("Rust", 1), ("C++", 1), ("Kotlin", 1), ("React Native", 1), ("MongoDB", 1), ("Redis", 1)]

    def chips(items, y):
        x, out = 0, []
        for it in items:
            name, learning = (it, 0) if isinstance(it, str) else it
            w = len(name) * 8.6 + 34
            stroke, dash, col = (ORANGE, ' stroke-dasharray="4 4"', ORANGE) if learning else (LINE, "", TEXT)
            out.append(
                f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="38" rx="19" fill="{PANEL}" stroke="{stroke}"{dash}/>'
                f'<circle cx="{x+17:.1f}" cy="{y+19}" r="3.5" fill="{col if learning else LIME}"/>'
                f'<text x="{x+30:.1f}" y="{y+24}" font-size="14" fill="{col}">{esc(name)}</text>'
            )
            x += w + 14
        return "".join(out), x

    c1, w1 = chips(row1, 0)
    c2, w2 = chips(row2, 0)
    mq = lambda body, w, y, rev: (  # noqa: E731
        f'<g transform="translate(0 {y})"><g>{body}<g transform="translate({w:.1f} 0)">{body}</g>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="{-w if rev else 0:.1f} 0" to="{0 if rev else -w:.1f} 0" dur="{w/55:.0f}s" repeatCount="indefinite"/></g></g>'
    )
    return (
        head(W, H, "Stack", "Scrolling stack: shipped technologies and things currently being learned.")
        + f'<defs><linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".08" stop-color="#fff"/>'
        f'<stop offset=".92" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask></defs>'
        + f'<g mask="url(#m)">{mq(c1, w1, 24, False)}{mq(c2, w2, 90, True)}</g>'
        + f'<text x="8" y="12" font-size="11" fill="{DIM}" letter-spacing="2" opacity=".0">stack</text>'
        + f'<text x="{W/2}" y="{H-6}" text-anchor="middle" font-size="11" fill="{DIM}">'
        f'<tspan fill="{LIME}">●</tspan> shipping   <tspan fill="{ORANGE}">◌</tspan> learning now</text>'
        + "</svg>"
    )


# --------------------------------------------------------------- pipeline (signature #1)

def pipeline(commits, total, live, blocks):
    W, H = 1200, 470
    now = dt.datetime.now(dt.timezone.utc)
    ts = now.strftime("%Y-%m-%d %H:%M UTC")
    last = commits[0]
    cls = last["msg"].split(":")[0].lower() if ":" in last["msg"] else "misc"
    cls = cls if cls in {"feat", "fix", "chore", "docs", "refactor", "test"} else "misc"
    repos = len({c["repo"] for c in commits})
    head_hash = blocks[-1]["hash"]
    src = "live" if live else "cached"
    stages = [
        ("TRIGGER", "cron 0 */6 * * *", f"fired {ts}"),
        ("READ", "GitHub search API", f"{total} public commits across {repos} repos ({src})"),
        ("DECIDE", "classify newest push", f'{last["repo"]}  "{clip(last["msg"], 38)}"  ->  {cls}'),
        ("ACT", f"sha256 · diff {DIFFICULTY}", f"chain re-mined, head {short(head_hash)}"),
        ("REPORT", "commit 4 svgs", "profile redrawn, next run in 6h"),
    ]
    cxs = [130, 365, 600, 835, 1070]
    DUR = 12
    arrive = [0.0, 0.2, 0.4, 0.6, 0.8]
    nodes, lit = [], []
    for i, ((name, sub, _), cx) in enumerate(zip(stages, cxs)):
        a = arrive[i]
        pts = [(0, 0), (a, 0), (a + 0.015, 1), (min(a + 0.19, 0.99), .7 if i < 4 else 1), (min(a + 0.2, 0.995), 0 if i < 4 else 1)]
        if i == 4:
            pts = [(0, 0), (a, 0), (a + 0.015, 1), (0.96, 1), (0.985, 0)]
        nodes.append(
            f'<g><rect x="{cx-78}" y="104" width="156" height="104" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
            f'<text x="{cx-62}" y="130" font-size="12" fill="{DIM}">0{i+1}</text>'
            f'<text x="{cx-62}" y="160" font-size="20" font-weight="700" fill="{TEXT}" letter-spacing="1">{name}</text>'
            f'<text x="{cx-62}" y="184" font-size="12" fill="{DIM}">{esc(sub)}</text>'
            f'<rect x="{cx-78}" y="104" width="156" height="104" rx="14" fill="{LIME}" fill-opacity=".07" stroke="{LIME}" stroke-width="1.6" opacity="0" filter="url(#glow)">'
            f'{animate("opacity", pts, DUR)}</rect></g>'
        )
        lit.append(pts)

    links = "".join(
        f'<line x1="{cxs[i]+78}" y1="156" x2="{cxs[i+1]-78}" y2="156" stroke="{LIME}" stroke-width="2" stroke-dasharray="6 8" opacity=".55">'
        f'<animate attributeName="stroke-dashoffset" from="28" to="0" dur="1.2s" repeatCount="indefinite"/></line>'
        for i in range(4)
    )
    kp = ";".join(str(x) for x in [0, 0, .25, .25, .5, .5, .75, .75, 1, 1])
    kt = ";".join(str(x) for x in [0, .03, .2, .23, .4, .43, .6, .63, .8, 1])
    packet = (
        f'<g filter="url(#glow)"><circle r="7" fill="{LIME}"/><circle r="14" fill="none" stroke="{LIME}" opacity=".5">'
        f'<animate attributeName="r" values="8;18;8" dur="1.2s" repeatCount="indefinite"/></circle>'
        f'<animateMotion dur="{DUR}s" repeatCount="indefinite" path="M130 156 L1070 156" keyPoints="{kp}" keyTimes="{kt}" calcMode="linear"/></g>'
    )

    log = []
    tags = ["trigger", "read", "decide", "act", "report"]
    for i, (_, _, line) in enumerate(stages):
        y = 292 + i * 30
        a = arrive[i] + 0.02
        pts = [(0, 0), (a, 0), (a + 0.02, 1), (0.96, 1), (0.985, 0)]
        log.append(
            f'<g opacity="0">{animate("opacity", pts, DUR)}'
            f'<text x="44" y="{y}" font-size="14" fill="{LIME}">[{tags[i]}]</text>'
            f'<text x="148" y="{y}" font-size="14" fill="{TEXT}">{esc(clip(line, 104))}</text></g>'
        )
    bar = (
        f'<rect x="44" y="444" width="1112" height="3" rx="1.5" fill="{LINE}"/>'
        f'<rect x="44" y="444" width="0" height="3" rx="1.5" fill="{LIME}" filter="url(#glow)">{animate("width", [(0, 0), (1, 1112)], DUR)}</rect>'
    )
    return (
        head(W, H, "Profile agent", "Animated pipeline: trigger, read, decide, act, report. Fed by real public commit data.")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}</defs>"
        + frame(W, H)
        + f'<circle cx="44" cy="40" r="5" fill="#ff5f56"/><circle cx="64" cy="40" r="5" fill="#ffbd2e"/><circle cx="84" cy="40" r="5" fill="#27c93f"/>'
        + f'<text x="110" y="45" font-size="13" fill="{DIM}">profile.agent  ·  last run {ts}</text>'
        + f'<text x="{W-44}" y="45" text-anchor="end" font-size="13" fill="{LIME}">● this README is an agent</text>'
        + f'<line x1="0" y1="66" x2="{W}" y2="66" stroke="{LINE}"/>'
        + f'<text x="44" y="96" font-size="12" fill="{DIM}" letter-spacing="2">PIPELINE</text>'
        + links + "".join(nodes) + packet
        + f'<rect x="28" y="236" width="{W-56}" height="192" rx="12" fill="#090b11" stroke="{LINE}"/>'
        + f'<text x="44" y="262" font-size="12" fill="{DIM}" letter-spacing="2">OUTPUT</text>'
        + "".join(log) + bar
        + "</g></svg>"
    )


# --------------------------------------------------------------- ledger (signature #2)

def ledger(blocks, total, live):
    W, H = 1200, 360
    bw, gap, x0, y0, bh = 196, 36, 38, 96, 200
    chain_ok = all(
        blocks[i]["prev"] == blocks[i - 1]["hash"] and blocks[i]["hash"].startswith("0" * DIFFICULTY)
        for i in range(1, len(blocks))
    )
    out = []
    for i, b in enumerate(blocks):
        x = x0 + i * (bw + gap)
        newest = i == len(blocks) - 1
        delay = i * 0.35
        stroke = LIME if newest else LINE
        h = b["hash"]
        hashtxt = (
            f'<tspan fill="{LIME}">{h[:DIFFICULTY]}</tspan><tspan fill="{TEXT}">{h[DIFFICULTY:DIFFICULTY+5]}</tspan>'
        )
        date = b["date"][:10]
        nonce_flicker = ""
        if newest:
            vals = [f"{(b['nonce'] + k * 37) % 9999:04d}" for k in range(1, 8)] + [f"{b['nonce']:04d}"]
            for k, v in enumerate(vals):
                pts = [(0, 0), (k / 8, 0), (k / 8 + .001, 1), ((k + 1) / 8, 1), ((k + 1) / 8 + .001, 0)]
                nonce_flicker += f'<text x="{x+16}" y="{y0+bh-18}" font-size="12" fill="{ORANGE}" opacity="0">nonce {v}{animate("opacity", pts, 2.4)}</text>'
        else:
            nonce_flicker = f'<text x="{x+16}" y="{y0+bh-18}" font-size="12" fill="{DIM}">nonce {b["nonce"]:04d}</text>'
        out.append(
            f'<g opacity="0" transform="translate(0 14)"><animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur=".6s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 14" to="0 0" begin="{delay}s" dur=".6s" fill="freeze"/>'
            f'<rect x="{x}" y="{y0}" width="{bw}" height="{bh}" rx="14" fill="{PANEL}" stroke="{stroke}" stroke-width="{1.6 if newest else 1}">'
            + (f'<animate attributeName="stroke-opacity" values="1;.35;1" dur="2.4s" repeatCount="indefinite"/>' if newest else "")
            + f'</rect>'
            f'<text x="{x+16}" y="{y0+28}" font-size="12" fill="{DIM}" letter-spacing="2">BLOCK #{b["no"]:03d}</text>'
            f'<text x="{x+16}" y="{y0+56}" font-size="15" font-weight="700" fill="{TEXT}">0x{hashtxt}<tspan fill="{DIM}">…{h[-4:]}</tspan></text>'
            f'<text x="{x+16}" y="{y0+80}" font-size="11" fill="{DIM}">prev {short(b["prev"]) if i else "0x000000…0000"}</text>'
            f'<line x1="{x+16}" x2="{x+bw-16}" y1="{y0+96}" y2="{y0+96}" stroke="{LINE}"/>'
            f'<text x="{x+16}" y="{y0+120}" font-size="12" fill="{TEXT}">{esc(clip(b["repo"].split("/")[-1], 22))}</text>'
            f'<text x="{x+16}" y="{y0+142}" font-size="12" fill="{DIM}">{esc(clip(b["msg"], 24))}</text>'
            f'<text x="{x+16}" y="{y0+164}" font-size="11" fill="{DIM}">{date}  ·  {b["sha"]}</text>'
            f'{nonce_flicker}</g>'
        )
        if i:
            lx = x - gap
            out.append(
                f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur=".4s" fill="freeze"/>'
                f'<line x1="{lx+4}" y1="{y0+bh/2}" x2="{x-4}" y2="{y0+bh/2}" stroke="{LIME}" stroke-width="2" stroke-dasharray="4 5">'
                f'<animate attributeName="stroke-dashoffset" from="18" to="0" dur=".9s" repeatCount="indefinite"/></line>'
                f'<path d="M{x-10} {y0+bh/2-5} L{x-3} {y0+bh/2} L{x-10} {y0+bh/2+5}" fill="none" stroke="{LIME}" stroke-width="2"/></g>'
            )
    # mining bar under newest block
    nx = x0 + (len(blocks) - 1) * (bw + gap)
    status = "chain valid" if chain_ok else "chain broken"
    return (
        head(W, H, "Commit ledger", f"My latest public commits as a proof-of-work hash chain (sha256, difficulty {DIFFICULTY}).")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}</defs>"
        + frame(W, H)
        + f'<text x="44" y="46" font-size="13" fill="{DIM}" letter-spacing="2">COMMIT LEDGER</text>'
        + f'<text x="44" y="68" font-size="12" fill="{DIM}">every block is a real public commit, hashed with sha256 and mined to {DIFFICULTY} leading zeros</text>'
        + f'<text x="{W-44}" y="46" text-anchor="end" font-size="13" fill="{LIME}">● {status}</text>'
        + f'<text x="{W-44}" y="68" text-anchor="end" font-size="12" fill="{DIM}">{total} commits indexed · {"live" if live else "cached"}</text>'
        + "".join(out)
        + f'<rect x="{nx}" y="{y0+bh+22}" width="{bw}" height="3" rx="1.5" fill="{LINE}"/>'
        + f'<rect x="{nx}" y="{y0+bh+22}" width="0" height="3" rx="1.5" fill="{LIME}" filter="url(#glow)">{animate("width", [(0, 0), (.85, bw), (1, bw)], 2.4)}</rect>'
        + f'<text x="{nx+bw}" y="{y0+bh+46}" text-anchor="end" font-size="11" fill="{DIM}">mining next block…</text>'
        + "</g></svg>"
    )


def main():
    OUT.mkdir(exist_ok=True)
    commits, total, live = fetch_commits()
    blocks = build_chain(commits, total)
    files = {
        "banner.svg": banner(),
        "stack.svg": stack(),
        "pipeline.svg": pipeline(commits, total, live, blocks),
        "ledger.svg": ledger(blocks, total, live),
    }
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg)/1024:.1f} KB")
    print("head", blocks[-1]["hash"], "live" if live else "fallback")


if __name__ == "__main__":
    main()
