"""Second batch of profile SVGs: contribution skyline, devnet, orbit, now card,
section headers, call-to-action and footer. Imported by build.py.

The skyline is a port of the Contribution Skyline on alexblitz.vercel.app: the
same grid, levels, bar heights, camera angles and oldest-to-newest wave, drawn
as SMIL instead of canvas.
"""
import datetime as dt
import json
import math
import re
import urllib.request
from pathlib import Path

from build import (BG, COMMON_DEFS, DIM, FONT, ICE, LIME, LINE, ORANGE, PANEL, TEXT, USER,
                   animate, clip, clipdef, esc, frame, head, keyed)

DATA = Path(__file__).resolve().parent.parent / "data"

# ------------------------------------------------------------ contribution data


def fetch_days():
    url = f"https://github.com/users/{USER}/contributions"
    cache = DATA / "contributions.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        ids = dict((i, d) for d, i in re.findall(r'data-date="([\d-]+)"[^>]*?id="(contribution-day-component-[\d-]+)"', html))
        days = {d: 0 for d in ids.values()}
        for for_id, text in re.findall(r'<tool-tip[^>]*?\sfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
            m = re.match(r"\s*(\d+) contribution", text)
            if m and for_id in ids:
                days[ids[for_id]] = int(m.group(1))
        out = [{"date": d, "count": c} for d, c in sorted(days.items())]
        if len(out) > 300:
            DATA.mkdir(exist_ok=True)
            cache.write_text(json.dumps(out), encoding="utf-8")
            return out, True
    except Exception as exc:
        print("contributions fetch failed:", exc)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")), False
    return [], False


def build_grid(days):
    if not days:
        return [], 0, 0
    counts = {d["date"]: d["count"] for d in days}
    end = dt.date.fromisoformat(max(counts))
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    cells, i, cur = [], 0, start
    while cur <= end:
        cells.append({"date": cur.isoformat(), "count": counts.get(cur.isoformat(), 0), "week": i // 7, "day": i % 7})
        cur += dt.timedelta(days=1)
        i += 1
    nz = sorted(c["count"] for c in cells if c["count"] > 0)
    busy = nz[int(0.95 * (len(nz) - 1))] if nz else 0
    for c in cells:
        n = c["count"]
        c["level"] = 0 if n <= 0 else (4 if busy <= 0 else 1 + min(3, int(n / busy * 4)))
    return cells, cells[-1]["week"] + 1, (nz[-1] if nz else 0)


def stats(cells):
    total = sum(c["count"] for c in cells)
    best = max(cells, key=lambda c: c["count"]) if cells else None
    run, longest, lstart, lbest = 0, 0, None, (None, None)
    for c in cells:
        if c["count"] > 0:
            if run == 0:
                lstart = c["date"]
            run += 1
            if run > longest:
                longest, lbest = run, (lstart, c["date"])
        else:
            run = 0
    j = len(cells) - 1
    if j >= 0 and cells[j]["count"] == 0:
        j -= 1
    end_at = j
    while j >= 0 and cells[j]["count"] > 0:
        j -= 1
    cur = end_at - j
    return {
        "total": total, "first": cells[0]["date"], "last": cells[-1]["date"],
        "best": best["count"], "best_date": best["date"],
        "longest": longest, "longest_range": lbest,
        "current": cur, "current_range": (cells[j + 1]["date"], cells[end_at]["date"]) if cur else (None, None),
    }


def md(d):
    x = dt.date.fromisoformat(d)
    return f"{x.strftime('%b')} {x.day}"


def mdy(d):
    x = dt.date.fromisoformat(d)
    return f"{x.strftime('%b')} {x.day}, {x.year}"


# ------------------------------------------------------------ skyline

LEVELS = ["#151926", "#33430a", "#5f8200", "#a6d400", LIME]


def shade(hexcol, f):
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (round(r * f), round(g * f), round(b * f))


def bar_h(count, mx):
    return 0.4 + (count / mx) ** 0.85 * 7.2 if count > 0 and mx > 0 else 0.2


def cam(yaw, elev):
    return math.cos(yaw), math.sin(yaw), math.sin(elev), math.cos(elev)


C2 = cam(0, math.pi / 2)
C3 = cam(math.pi / 4, 34 * math.pi / 180)


def proj(c, x, y, z):
    cs, sn, se, ce = c
    return x * cs - y * sn, (x * sn + y * cs) * se - z * ce


def fit(c, pts, box):
    xs = [proj(c, *p)[0] for p in pts]
    ys = [proj(c, *p)[1] for p in pts]
    bx0, by0, bx1, by1 = box
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    s = min((bx1 - bx0) / bw, (by1 - by0) / bh)
    ox = bx0 + ((bx1 - bx0) - bw * s) / 2 - min(xs) * s
    oy = by0 + ((by1 - by0) - bh * s) / 2 - min(ys) * s
    return s, ox, oy


def skyline(days, live):
    cells, weeks, mx = build_grid(days)
    if not cells:
        return None
    st = stats(cells)
    W, H = 1200, 620
    DUR = 22.0
    w2, w3 = 0.78, 0.9
    for c in cells:
        c["h"] = bar_h(c["count"], mx)

    def corners(c, w, z):
        off = (1 - w) / 2
        x0, y0 = c["week"] + off, c["day"] + off
        return x0, y0, x0 + w, y0 + w, z

    pts3 = []
    for c in cells:
        x0, y0, x1, y1, z = corners(c, w3, c["h"])
        pts3 += [(x0, y0, z), (x1, y0, z), (x0, y1, z), (x1, y1, 0), (x0, y1, 0), (x1, y0, 0)]
    pts3 += [(0, 7.6, 0), (weeks, 7.6, 0), (0, -0.4, 0), (weeks, 7.4, 0)]
    pts2 = [(0, 0, 0), (weeks, 7, 0)]
    s3, ox3, oy3 = fit(C3, pts3, (130, 100, 1070, 540))
    s2, ox2, oy2 = fit(C2, pts2, (100, 240, 1120, 420))

    def P(state, x, y, z):
        c, s, ox, oy = (C3, s3, ox3, oy3) if state else (C2, s2, ox2, oy2)
        px, py = proj(c, x, y, z)
        return ox + px * s, oy + py * s

    def poly(state, pts):
        return " ".join("%.1f,%.1f" % P(state, *p) for p in pts)

    def top(c, state):
        w = w3 if state else w2
        z = c["h"] if state else 0
        x0, y0, x1, y1, _ = corners(c, w, z)
        return poly(state, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)])

    def left(c, state):  # +y face
        w = w3 if state else w2
        z = c["h"] if state else 0
        x0, y0, x1, y1, _ = corners(c, w, z)
        return poly(state, [(x0, y1, 0), (x1, y1, 0), (x1, y1, z), (x0, y1, z)])

    def right(c, state):  # +x face
        w = w3 if state else w2
        z = c["h"] if state else 0
        x0, y0, x1, y1, _ = corners(c, w, z)
        return poly(state, [(x1, y0, 0), (x1, y1, 0), (x1, y1, z), (x1, y0, z)])

    # timeline (seconds): flat hold, rise wave, 3D hold, fall wave, flat hold
    T_UP, T_HOLD_END, T_DOWN, SPREAD, MT = 1.6, 14.2, 14.2, 1.7, 1.4
    EASE, LIN = "0.65 0 0.35 1", "0 0 1 1"

    def morph(fn_a, fn_b, c, delay_up, delay_down):
        a = (T_UP + delay_up * SPREAD) / DUR
        b = (T_UP + delay_up * SPREAD + MT) / DUR
        d = (T_DOWN + delay_down * SPREAD) / DUR
        e = (T_DOWN + delay_down * SPREAD + MT) / DUR
        kt = [0, a, b, d, e, 1]
        va, vb = fn_a(c, 0), fn_b(c, 1)
        vals = [va, va, vb, vb, va, va]
        splines = [LIN, EASE, LIN, EASE, LIN]
        return (f'<animate attributeName="points" values="{";".join(vals)}" keyTimes="{";".join("%.4f" % t for t in kt)}" '
                f'calcMode="spline" keySplines="{";".join(s.replace(" ", " ") for s in splines)}" dur="{DUR}s" repeatCount="indefinite"/>')

    order = sorted(cells, key=lambda c: (c["week"] + 0.5) * math.sin(math.pi / 4) + (c["day"] + 0.5) * math.cos(math.pi / 4))
    body = []
    for c in order:
        d = (c["week"] / max(weeks - 1, 1)) * 0.75 + (c["day"] / 6) * 0.25
        col = LEVELS[c["level"]]
        # fall wave runs newest to oldest
        mt = lambda fa, fb: morph(fa, fb, c, d, 1 - d)  # noqa: E731
        if c["count"] > 0:
            body.append(f'<polygon points="{left(c, 0)}" fill="{shade(col, .84)}">{mt(left, left)}</polygon>')
            body.append(f'<polygon points="{right(c, 0)}" fill="{shade(col, .68)}">{mt(right, right)}</polygon>')
        body.append(f'<polygon points="{top(c, 0)}" fill="{col}" stroke="{col}" stroke-width="{1.4 if c["level"] == 0 else 1}" stroke-linejoin="round">{mt(top, top)}</polygon>')

    # floor: a plate that turns from the flat grid backdrop into the iso diamond
    def floor(c, state):
        return poly(state, [(-0.5, -0.5, 0), (weeks + 0.5, -0.5, 0), (weeks + 0.5, 7.5, 0), (-0.5, 7.5, 0)])

    floor_el = (f'<polygon points="{floor(None, 0)}" fill="#0a0d14" stroke="{LINE}" stroke-width="1">'
                f'{morph(floor, floor, None, 0, 0)}</polygon>')

    def fade(points, extra=""):
        return f'opacity="0">{animate("opacity", points, DUR)}'

    u0, u1 = (T_UP + 0.5) / DUR, (T_UP + SPREAD + MT) / DUR
    d0, d1 = T_DOWN / DUR, (T_DOWN + 0.6) / DUR
    in3d = [(0, 0), (u0, 0), (u1, 1), (d0, 1), (d1, 0), (1, 0)]
    in2d = [(0, 1), (u0 - 0.01, 1), (u0 + 0.03, 0), (d0 + 0.02, 0), (d1 + 0.04, 1), (1, 1)]

    months = []
    prev = None
    last_x = -1e9
    for w in range(weeks):
        c = cells[w * 7]
        m = c["date"][5:7]
        if m != prev:
            months.append((w, dt.date.fromisoformat(c["date"]).strftime("%b")))
        prev = m
    if len(months) > 1 and months[1][0] - months[0][0] < 3:
        months.pop(0)
    lab2, lab3 = [], []
    for w, name in months:
        x, y = P(0, w + 0.11, -0.3, 0)
        lab2.append(f'<text x="{x:.1f}" y="{y - 6:.1f}" font-size="12" fill="{DIM}">{name}</text>')
        x, y = P(1, w + 0.5, 7.4, 0)
        lab3.append(f'<text x="{x:.1f}" y="{y + 14:.1f}" font-size="12" fill="{DIM}" transform="rotate(0)">{name}</text>')
    rows = []
    for d, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        x, y = P(0, 0, d + 0.5, 0)
        rows.append(f'<text x="{x - 10:.1f}" y="{y + 4:.1f}" font-size="12" fill="{DIM}" text-anchor="end">{name}</text>')

    def stat(x, y, label, value, unit, sub, anchor="start", size=52):
        return (f'<g text-anchor="{anchor}"><text x="{x}" y="{y}" font-size="13" fill="{DIM}">{label}</text>'
                f'<text x="{x}" y="{y + size * .95:.0f}" font-size="{size}" font-weight="700" fill="{LIME}" filter="url(#glow)">{value}</text>'
                f'<text x="{x}" y="{y + size * .95 + 22:.0f}" font-size="15" fill="{TEXT}">{unit}</text>'
                f'<text x="{x}" y="{y + size * .95 + 40:.0f}" font-size="12" fill="{DIM}">{sub}</text></g>')

    rng = lambda a, b: f"{md(a)} — {md(b)}"  # noqa: E731
    lr, cr = st["longest_range"], st["current_range"]
    corners_3d = (
        stat(W - 56, 104, "1 year total", st["total"], "contributions", f"{mdy(st['first'])} — {mdy(st['last'])}", "end")
        + stat(W - 56, 250, "Busiest day", st["best"], "contributions", md(st["best_date"]), "end")
        + stat(56, 380, "Longest streak", st["longest"], "days", rng(*lr) if lr[0] else "-")
        + stat(56, 500, "Current streak", st["current"], "days" if st["current"] != 1 else "day", rng(*cr) if cr[0] else "-")
    )

    def row(x, label, value, unit, sub):
        return (f'<text x="{x}" y="470" font-size="12" fill="{DIM}">{label}</text>'
                f'<text x="{x}" y="506" font-size="30" font-weight="700" fill="{LIME}">{value}</text>'
                f'<text x="{x + 12 + len(str(value)) * 18}" y="506" font-size="14" fill="{TEXT}">{unit}</text>'
                f'<text x="{x}" y="528" font-size="12" fill="{DIM}">{sub}</text>')

    row_2d = (row(70, "1 year total", st["total"], "contributions", f"{md(st['first'])} — {md(st['last'])}")
              + row(360, "Busiest day", st["best"], "contributions", md(st["best_date"]))
              + row(650, "Longest streak", st["longest"], "days", rng(*lr) if lr[0] else "-")
              + row(930, "Current streak", st["current"], "days" if st["current"] != 1 else "day", rng(*cr) if cr[0] else "-"))

    legend = "".join(f'<rect x="{W - 205 + i * 17}" y="{H - 44}" width="12" height="12" rx="2" fill="{c}"/>' for i, c in enumerate(LEVELS))
    legend += f'<text x="{W - 214}" y="{H - 34}" font-size="12" fill="{DIM}" text-anchor="end">Less</text><text x="{W - 112}" y="{H - 34}" font-size="12" fill="{DIM}">More</text>'

    # 2D / 3D toggle that follows the animation
    sw = [(0, 0), (u0 - 0.01, 0), (u0 + 0.02, 40), (d0 + 0.01, 40), (d0 + 0.04, 0), (1, 0)]
    kt, vs = keyed(sw)
    toggle = (f'<g transform="translate({W - 140} 34)"><rect width="84" height="32" rx="8" fill="none" stroke="{LINE}"/>'
              f'<rect x="3" y="3" width="38" height="26" rx="6" fill="{LIME}"><animate attributeName="x" values="{";".join(str(3 + float(v)) for v in vs.split(";"))}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/></rect>'
              f'<text x="22" y="21" font-size="13" font-weight="700" text-anchor="middle" fill="{BG}">2D</text>'
              f'<text x="63" y="21" font-size="13" font-weight="700" text-anchor="middle" fill="{TEXT}">3D</text></g>')

    return (
        head(W, H, "Contribution skyline", f"{st['total']} contributions in the last year, drawn as a heat map that rises into a 3D skyline.")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}</defs>"
        + frame(W, H)
        + f'<text x="44" y="56" font-size="20" fill="{TEXT}"><tspan font-weight="700" fill="{LIME}">{st["total"]}</tspan> contributions in the last year</text>'
        + f'<text x="44" y="78" font-size="12" fill="{DIM}">same skyline as the one on my portfolio · {"live from github" if live else "cached"}</text>'
        + toggle
        + floor_el
        + f'<g {fade(in2d)}{"".join(lab2)}{"".join(rows)}</g>'
        + f'<g {fade(in3d)}{"".join(lab3)}</g>'
        + "".join(body)
        + f'<g {fade(in3d)}{corners_3d}</g>'
        + f'<g {fade(in2d)}{row_2d}</g>'
        + legend
        + "</g></svg>"
    )


# ------------------------------------------------------------ devnet


def devnet():
    W, H = 1200, 470
    DUR = 12.0
    nodes = [(170, 190), (420, 130), (560, 262), (300, 322)]
    names = ["node-1", "node-2", "node-3", "node-4"]
    edges = []
    for i in range(4):
        for j in range(i + 1, 4):
            edges.append((i, j))
    g = []
    for i, j in edges:
        (x1, y1), (x2, y2) = nodes[i], nodes[j]
        g.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="1.5"/>')
        g.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LIME}" stroke-width="1" stroke-dasharray="3 9" opacity=".35">'
                 f'<animate attributeName="stroke-dashoffset" from="24" to="0" dur="2s" repeatCount="indefinite"/></line>')
    # one proposer per phase broadcasts a block to the other three
    for k, (kx, ky) in enumerate(nodes):
        a, b = k / 4, k / 4 + 0.2
        for j, (jx, jy) in enumerate(nodes):
            if j == k:
                continue
            kp = "0;0;1;1"
            kt = f"0;{a:.3f};{b:.3f};1"
            g.append(
                f'<g filter="url(#glow)"><rect x="-6" y="-6" width="12" height="12" rx="2" fill="{LIME}" opacity="0">'
                f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{a:.3f};{a + .01:.3f};{b - .01:.3f};{b:.3f};1" dur="{DUR}s" repeatCount="indefinite"/></rect>'
                f'<animateMotion path="M{kx} {ky} L{jx} {jy}" dur="{DUR}s" repeatCount="indefinite" keyPoints="{kp}" keyTimes="{kt}" calcMode="linear"/></g>'
            )
    for k, ((x, y), name) in enumerate(zip(nodes, names)):
        a, b = k / 4, (k + 1) / 4
        g.append(
            f'<g><circle cx="{x}" cy="{y}" r="30" fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>'
            f'<circle cx="{x}" cy="{y}" r="30" fill="{LIME}" fill-opacity=".1" stroke="{LIME}" stroke-width="2" opacity="0" filter="url(#glow)">'
            f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{max(a - .001, 0):.3f};{a + .01:.3f};{b - .02:.3f};{b:.3f};1" dur="{DUR}s" repeatCount="indefinite"/></circle>'
            f'<text x="{x}" y="{y + 4}" font-size="12" text-anchor="middle" fill="{TEXT}">{name}</text></g>'
        )

    # height ticker driven by phase
    tick = []
    for k in range(4):
        a, b = k / 4, (k + 1) / 4
        kt = f"0;{max(a - .001, 0):.3f};{a + .001:.3f};{b - .001:.3f};{b:.3f};1"
        tick.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'
            f'<text x="700" y="150" font-size="44" font-weight="700" fill="{LIME}" filter="url(#glow)">#000155</text>'
            f'<text x="700" y="178" font-size="13" fill="{DIM}">next block, proposed by {names[k]} · 1 tx · sha256</text></g>'
        )

    blocks = []
    for i in range(5):
        x = 700 + i * 90
        n = 150 + i
        newest = i == 4
        blocks.append(
            f'<rect x="{x}" y="212" width="70" height="56" rx="8" fill="{PANEL}" stroke="{LIME if newest else LINE}" stroke-width="{1.6 if newest else 1}"/>'
            f'<text x="{x + 35}" y="236" font-size="11" text-anchor="middle" fill="{DIM}">#{n:06d}</text>'
            f'<text x="{x + 35}" y="254" font-size="10" text-anchor="middle" fill="{TEXT}">0x{(n * 2654435761) % 0xffffff:06x}</text>'
        )
        if i:
            blocks.append(f'<line x1="{x - 20}" y1="240" x2="{x}" y2="240" stroke="{LIME}" stroke-width="1.5" stroke-dasharray="3 3"/>')

    stats = "".join(
        f'<text x="{700 + i * 120}" y="304" font-size="11" fill="{DIM}">{k}</text><text x="{700 + i * 120}" y="324" font-size="18" fill="{TEXT}">{v}</text>'
        for i, (k, v) in enumerate([("peers", "4"), ("pending", "4"), ("consensus", "undecided"), ("network", "local devnet")])
    )

    steps = [("Blocks and hashing", 1), ("Transactions", 1), ("Local devnet", 1), ("Consensus", 2), ("The coin", 0), ("Public testnet", 0)]
    sx0, sx1, sy = 120, 1080, 400
    gap = (sx1 - sx0) / (len(steps) - 1)
    road = f'<line x1="{sx0}" y1="{sy}" x2="{sx1}" y2="{sy}" stroke="{LINE}" stroke-width="2"/>'
    road += f'<line x1="{sx0}" y1="{sy}" x2="{sx0 + gap * 3}" y2="{sy}" stroke="{LIME}" stroke-width="2"/>'
    for i, (label, st) in enumerate(steps):
        x = sx0 + gap * i
        if st == 1:
            road += f'<circle cx="{x}" cy="{sy}" r="8" fill="{LIME}"/><path d="M{x - 3.5} {sy} l2.5 3 l5 -6" stroke="{BG}" stroke-width="2" fill="none"/>'
            tag = "done"
        elif st == 2:
            road += (f'<circle cx="{x}" cy="{sy}" r="9" fill="{BG}" stroke="{ORANGE}" stroke-width="2.5" filter="url(#glow)"/>'
                     f'<circle cx="{x}" cy="{sy}" r="9" fill="none" stroke="{ORANGE}"><animate attributeName="r" values="9;22;9" dur="2s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values=".8;0;.8" dur="2s" repeatCount="indefinite"/></circle>')
            tag = "now"
        else:
            road += f'<circle cx="{x}" cy="{sy}" r="7" fill="{BG}" stroke="{DIM}" stroke-width="1.5"/>'
            tag = "next"
        col = ORANGE if st == 2 else (LIME if st == 1 else DIM)
        road += (f'<text x="{x}" y="{sy + 30}" font-size="13" text-anchor="middle" fill="{TEXT if st else DIM}">{label}</text>'
                 f'<text x="{x}" y="{sy + 48}" font-size="11" text-anchor="middle" fill="{col}" letter-spacing="2">{tag.upper()}</text>')

    return (
        head(W, H, "Layer one devnet", "Animated simulation of my from-scratch Rust blockchain devnet: four nodes sealing blocks in turn, plus the roadmap.")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}</defs>"
        + frame(W, H)
        + f'<text x="44" y="46" font-size="13" fill="{DIM}" letter-spacing="2">LAYER ONE · LOCAL DEVNET</text>'
        + f'<text x="44" y="68" font-size="12" fill="{DIM}">written in Rust from the first line · an engineering project, nothing to buy, nothing for sale</text>'
        + f'<text x="{W - 44}" y="46" text-anchor="end" font-size="13" fill="{ORANGE}">● consensus: in progress</text>'
        + "".join(g) + "".join(tick) + "".join(blocks) + stats + road
        + "</g></svg>"
    )


# ------------------------------------------------------------ orbit


def orbit():
    W, H = 1200, 600
    cx, cy = 600, 300
    tiers = [
        (118, 70, False, ["React", "TypeScript", "Next.js", "Node.js", "Python", "Go"]),
        (192, -110, False, ["PostgreSQL", "MySQL", "FastAPI", "Django", "NestJS", "Express", "Linux", "PHP"]),
        (262, 150, True, ["Rust", "C++", "Kotlin", "React Native", "MongoDB", "Redis"]),
    ]
    out = []
    for r, dur, learning, items in tiers:
        col = ORANGE if learning else LIME
        dash = ' stroke-dasharray="5 7"' if learning else ""
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r * 1.9:.0f}" ry="{r}" fill="none" stroke="{col}" stroke-opacity=".28"{dash}/>')
    for r, dur, learning, items in tiers:
        col = ORANGE if learning else LIME
        n = len(items)
        sign = 1 if dur > 0 else -1
        ad = abs(dur)
        # rotate the whole ring: points move along the ellipse by rotating angle, so use two nested
        # transforms: rotate in unit-circle space, then scale x to get the ellipse
        ring = []
        for i, name in enumerate(items):
            a0 = 360 / n * i
            w = len(name) * 8.4 + 30
            chip = (f'<rect x="{-w / 2:.1f}" y="-16" width="{w:.1f}" height="32" rx="16" fill="{PANEL}" stroke="{col}" stroke-opacity=".75"/>'
                    f'<circle cx="{-w / 2 + 14:.1f}" cy="0" r="3.5" fill="{col}"/>'
                    f'<text x="{-w / 2 + 25:.1f}" y="4.5" font-size="13" fill="{TEXT}">{esc(name)}</text>')
            # position on the ellipse by animating a rotation of a point at (r,0): x stretched by 1.9
            # SMIL cannot stretch a rotation, so approximate the ellipse path with animateMotion
            path = ellipse_path(cx, cy, r * 1.9, r, a0)
            rev = 'keyPoints="1;0" keyTimes="0;1" calcMode="linear"' if sign < 0 else ''
            ring.append(f'<g>{chip}<animateMotion path="{path}" dur="{ad}s" repeatCount="indefinite" {rev}/></g>')
        out.append("".join(ring))

    core = (
        f'<circle cx="{cx}" cy="{cy}" r="120" fill="url(#aura)"><animate attributeName="r" values="100;130;100" dur="5s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{cx}" cy="{cy}" r="52" fill="{BG}" stroke="{LIME}" stroke-width="2" filter="url(#glow)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="52" fill="none" stroke="{LIME}" opacity=".6"><animate attributeName="r" values="52;86;52" dur="3s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".6;0;.6" dur="3s" repeatCount="indefinite"/></circle>'
        f'<text x="{cx}" y="{cy - 2}" font-size="20" font-weight="800" text-anchor="middle" fill="{TEXT}" letter-spacing="2">ALEX</text>'
        f'<text x="{cx}" y="{cy + 20}" font-size="20" font-weight="800" text-anchor="middle" fill="{LIME}" letter-spacing="2">BLITZ</text>'
    )
    legend = (
        f'<circle cx="60" cy="{H - 52}" r="4" fill="{LIME}"/><text x="74" y="{H - 48}" font-size="13" fill="{TEXT}">shipping: orbits close to the core</text>'
        f'<circle cx="60" cy="{H - 28}" r="4" fill="{ORANGE}"/><text x="74" y="{H - 24}" font-size="13" fill="{TEXT}">learning now: the outer, dashed ring</text>'
    )
    return (
        head(W, H, "Stack orbit", "Animated orbit map of the technologies I ship with and the ones I am learning.")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}</defs>"
        + frame(W, H)
        + "".join(out) + core + legend
        + "</g></svg>"
    )


def ellipse_path(cx, cy, rx, ry, start_deg):
    """Closed ellipse starting at start_deg, drawn with four cubic segments so animateMotion loops cleanly."""
    k = 0.5522847498
    a = math.radians(start_deg)
    pts = []
    # build points for 0, 90, 180, 270 relative to the start using the parametric ellipse
    def pt(t):
        return cx + rx * math.cos(t), cy + ry * math.sin(t)

    def tan(t):
        return -rx * math.sin(t), ry * math.cos(t)

    segs = []
    p0 = pt(a)
    d = f"M{p0[0]:.1f} {p0[1]:.1f}"
    for q in range(4):
        t0, t1 = a + q * math.pi / 2, a + (q + 1) * math.pi / 2
        s, e = pt(t0), pt(t1)
        ts, te = tan(t0), tan(t1)
        c1 = (s[0] + ts[0] * k * 1.0, s[1] + ts[1] * k * 1.0)
        c2 = (e[0] - te[0] * k * 1.0, e[1] - te[1] * k * 1.0)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {e[0]:.1f} {e[1]:.1f}"
    return d + " Z"


# ------------------------------------------------------------ now card


def now_card():
    W, H = 1200, 250
    try:
        from zoneinfo import ZoneInfo
        local = dt.datetime.now(ZoneInfo("Europe/Warsaw"))
    except Exception:
        local = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)
    hh = local.hour + local.minute / 60
    part = ("Night" if hh < 5 or hh >= 23 else "Morning" if hh < 12 else "Afternoon" if hh < 18 else "Evening")
    # sun arc: sunrise 6, sunset 20 (rough, the point is the picture)
    ax, ay, ar = 190, 168, 100
    f = min(max((hh - 6) / 14, 0), 1)
    daytime = 6 <= hh <= 20
    ang = math.pi * (1 - f)
    sx, sy = ax + ar * math.cos(ang), ay - ar * math.sin(ang)
    body = (f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="11" fill="{LIME}" filter="url(#glow)"><animate attributeName="r" values="10;14;10" dur="3s" repeatCount="indefinite"/></circle>'
            if daytime else
            f'<circle cx="{ax}" cy="{ay - 70}" r="12" fill="{TEXT}"/><circle cx="{ax + 6}" cy="{ay - 74}" r="11" fill="{BG}"/>')
    card1 = (
        f'<text x="44" y="46" font-size="12" fill="{DIM}" letter-spacing="2">RIGHT NOW · POLAND TIME</text>'
        f'<path d="M{ax - ar} {ay} A{ar} {ar} 0 0 1 {ax + ar} {ay}" fill="none" stroke="{LINE}" stroke-width="2" stroke-dasharray="3 6"/>'
        f'<line x1="{ax - ar - 14}" y1="{ay}" x2="{ax + ar + 14}" y2="{ay}" stroke="{LINE}"/>{body}'
        f'<text x="{ax}" y="{ay + 40}" font-size="44" font-weight="700" text-anchor="middle" fill="{TEXT}">{local.strftime("%H:%M")}</text>'
        f'<text x="{ax}" y="{ay + 62}" font-size="12" text-anchor="middle" fill="{DIM}">{part} in Poland · as of the last run</text>'
    )
    card2 = (
        f'<text x="440" y="46" font-size="12" fill="{DIM}" letter-spacing="2">BUILDING</text>'
        f'<text x="440" y="96" font-size="26" font-weight="700" fill="{TEXT}">A blockchain from</text>'
        f'<text x="440" y="130" font-size="26" font-weight="700" fill="{LIME}" filter="url(#glow)">scratch, in Rust.</text>'
        f'<text x="440" y="162" font-size="13" fill="{DIM}">and a coin to live on it. Consensus is next.</text>'
        f'<rect x="440" y="186" width="300" height="4" rx="2" fill="{LINE}"/>'
        f'<rect x="440" y="186" width="0" height="4" rx="2" fill="{LIME}" filter="url(#glow)">{animate("width", [(0, 0), (.8, 180), (1, 180)], 6)}</rect>'
        f'<text x="440" y="214" font-size="12" fill="{DIM}">3 of 7 milestones done</text>'
    )
    learning = ["Rust", "C++", "Kotlin", "React Native", "MongoDB", "Redis"]
    chips, y = [], 82
    for i, n in enumerate(learning):
        x = 800 + (i % 2) * 175
        yy = 78 + (i // 2) * 44
        chips.append(f'<rect x="{x}" y="{yy}" width="160" height="34" rx="17" fill="{PANEL}" stroke="{ORANGE}" stroke-dasharray="4 4" stroke-opacity=".8"/>'
                     f'<circle cx="{x + 18}" cy="{yy + 17}" r="3.5" fill="{ORANGE}"><animate attributeName="opacity" values="1;.2;1" dur="{2 + i * .3:.1f}s" repeatCount="indefinite"/></circle>'
                     f'<text x="{x + 32}" y="{yy + 22}" font-size="14" fill="{TEXT}">{esc(n)}</text>')
    card3 = f'<text x="800" y="46" font-size="12" fill="{DIM}" letter-spacing="2">LEARNING THIS MONTH</text>' + "".join(chips)
    return (
        head(W, H, "Now", "What I am doing right now: local time in Poland, what I am building and what I am learning.")
        + f"<defs>{COMMON_DEFS}{clipdef(W, H)}</defs>"
        + frame(W, H)
        + card1
        + f'<line x1="400" y1="30" x2="400" y2="{H - 30}" stroke="{LINE}"/><line x1="770" y1="30" x2="770" y2="{H - 30}" stroke="{LINE}"/>'
        + card2 + card3
        + "</g></svg>"
    )


# ------------------------------------------------------------ headers, cta, footer


def section(idx, title, sub):
    W, H = 1200, 84
    tw = len(title) * 17 + 70
    return (
        head(W, H, title, sub)
        + f'<defs><linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="{LIME}" stop-opacity="0"/><stop offset=".5" stop-color="{LIME}"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></linearGradient>'
        f'<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        + f'<text x="12" y="52" font-size="14" fill="{LIME}" letter-spacing="2">{idx:02d} /</text>'
        + f'<text x="64" y="54" font-size="30" font-weight="800" fill="{TEXT}" letter-spacing="4">{esc(title.upper())}'
        + animate("opacity", [(0, 1), (.9, 1), (.92, .4), (.94, 1), (.96, .5), (1, 1)], 6) + "</text>"
        + f'<text x="{tw + 40}" y="52" font-size="13" fill="{DIM}">{esc(sub)}</text>'
        + f'<line x1="12" y1="74" x2="{W - 12}" y2="74" stroke="{LINE}"/>'
        + f'<rect x="12" y="72" width="160" height="3" fill="url(#sh)" filter="url(#glow)">{animate("x", [(0, 12), (1, W - 172)], 5)}</rect>'
        + "</svg>"
    )


def cta():
    W, H = 420, 76
    return (
        head(W, H, "Open portfolio", "Button linking to the portfolio.")
        + f'<defs>{COMMON_DEFS}<linearGradient id="bd" x1="0" x2="1"><stop offset="0" stop-color="{LIME}"/><stop offset=".5" stop-color="{ICE}"/><stop offset="1" stop-color="{ORANGE}"/>'
        f'<animateTransform attributeName="gradientTransform" type="rotate" from="0 .5 .5" to="360 .5 .5" dur="6s" repeatCount="indefinite"/></linearGradient></defs>'
        + f'<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="{(H - 8) / 2}" fill="{BG}" stroke="url(#bd)" stroke-width="2.5"/>'
        + f'<text x="{W / 2 - 14}" y="{H / 2 + 6}" font-size="18" font-weight="700" text-anchor="middle" fill="{TEXT}" letter-spacing="2">OPEN THE PORTFOLIO</text>'
        + f'<text x="{W - 52}" y="{H / 2 + 7}" font-size="22" font-weight="700" fill="{LIME}">→<animate attributeName="x" values="{W - 56};{W - 46};{W - 56}" dur="1.4s" repeatCount="indefinite"/></text>'
        + "</svg>"
    )


def footer():
    W, H = 1200, 200

    def wave(y, amp, per, col, op, dur, rev=False):
        # path wider than the viewport, shifted by one period for a seamless loop
        pts = [f"M{-per} {y}"]
        x = -per
        while x < W + per:
            pts.append(f"q{per / 4} {-amp} {per / 2} 0 t{per / 2} 0")
            x += per
        frm, to = (0, per) if not rev else (per, 0)
        return (f'<path d="{" ".join(pts)}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="2" filter="url(#glow)"><animateTransform attributeName="transform" type="translate" '
                f'from="{frm} 0" to="{to} 0" dur="{dur}s" repeatCount="indefinite"/></path>')

    return (
        head(W, H, "Footer", "Animated footer waves with a closing line.")
        + f'<defs><linearGradient id="fw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{LIME}" stop-opacity=".35"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></linearGradient>'
        f'<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        + wave(140, 24, 420, LIME, .9, 14)
        + wave(150, 18, 300, ICE, .45, 9, True)
        + wave(158, 14, 520, ORANGE, .5, 20)
        + wave(166, 10, 260, LIME, .25, 7, True)
        + f'<text x="{W / 2}" y="74" font-size="20" text-anchor="middle" fill="{TEXT}" letter-spacing="1">I build the front end, the back end, and the agents that run the rest.</text>'
        + f'<text x="{W / 2}" y="100" font-size="13" text-anchor="middle" fill="{LIME}" letter-spacing="3" filter="url(#glow)">ALEX BLITZ · POLAND</text>'
        + "</svg>"
    )


def build_all(out):
    days, live = fetch_days()
    files = {
        "devnet.svg": devnet(),
        "orbit.svg": orbit(),
        "now.svg": now_card(),
        "cta.svg": cta(),
        "footer.svg": footer(),
        "h-activity.svg": section(1, "Activity", "a year of commits, folded into a skyline"),
        "h-agent.svg": section(2, "The agent", "this README redraws itself every six hours"),
        "h-orbit.svg": section(3, "Stack", "what I ship with, and what I am learning"),
        "h-now.svg": section(4, "Now", "time, focus, study list"),
        "h-chain.svg": section(5, "Layer one", "my blockchain, from the first line of Rust"),
    }
    sky = skyline(days, live)
    if sky:
        files["skyline.svg"] = sky
    for name, svg in files.items():
        (out / name).write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg) / 1024:.1f} KB")
