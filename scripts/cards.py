#!/usr/bin/env python3
"""Generate the animated SVG cards used in the profile README.

  python scripts/cards.py impact --out assets      # static proof-point tiles (committed)
  python scripts/cards.py pulse  --out dist        # live contribution card (built by CI)

Standard library only. `pulse` reads GITHUB_TOKEN and GH_USER from the environment.
Every card is written twice: <name>-light.svg and <name>-dark.svg.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import urllib.request
from html import escape

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "dark": dict(bg="#0d1117", card="#161b22", border="#30363d", text="#e6edf3",
                 muted="#8b949e", a1="#a78bfa", a2="#22d3ee", a3="#34d399", track="#21262d"),
    "light": dict(bg="#ffffff", card="#f6f8fa", border="#d0d7de", text="#1f2328",
                  muted="#59636e", a1="#6d28d9", a2="#0e7490", a3="#047857", track="#eaeef2"),
}

# Only verified proof points. Edit here, then re-run `impact`.
IMPACT = [
    ("$7,000", "SuperHack 2025 runner-up", "out of 10,000+ teams worldwide"),
    ("6×", "Hackathon wins", "$10,000+ in cumulative prizes"),
    ("60%", "LLM cost cut", "token optimisation, live platform"),
    ("100+", "Users scaled", "agentic chatbot, built from scratch"),
    ("89%", "Failure-forecast precision", "IoT faults predicted 4+ hours ahead"),
    ("+20%", "Edge inference speed", "ship-hull detection on 50K+ images"),
]


def _defs(t: dict) -> str:
    return f"""<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t['a1']}"/><stop offset="1" stop-color="{t['a2']}"/>
  </linearGradient>
</defs>"""


def impact_svg(t: dict) -> str:
    cols, w, tile_w, tile_h, gap, pad = 3, 840, 264, 150, 12, 12
    rows = (len(IMPACT) + cols - 1) // cols
    h = pad * 2 + rows * tile_h + (rows - 1) * gap
    tiles = []
    for i, (big, label, sub) in enumerate(IMPACT):
        x = pad + (i % cols) * (tile_w + gap)
        y = pad + (i // cols) * (tile_h + gap)
        d = 0.12 * i
        tiles.append(f"""
<g class="tile" style="animation-delay:{d:.2f}s">
  <rect x="{x}" y="{y}" width="{tile_w}" height="{tile_h}" rx="14" fill="{t['card']}" stroke="{t['border']}"/>
  <rect class="bar" x="{x + 20}" y="{y + 20}" width="44" height="4" rx="2" fill="url(#g)" style="animation-delay:{d + .25:.2f}s"/>
  <text x="{x + 20}" y="{y + 72}" font-size="40" font-weight="800" fill="url(#g)">{escape(big)}</text>
  <text x="{x + 20}" y="{y + 102}" font-size="17" font-weight="700" fill="{t['text']}">{escape(label)}</text>
  <text x="{x + 20}" y="{y + 126}" font-size="13" fill="{t['muted']}">{escape(sub)}</text>
</g>""")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img" aria-label="Selected impact">
<title>Selected impact</title>
{_defs(t)}
<style>
  .tile {{ opacity:0; animation: rise .6s ease-out forwards; }}
  .bar  {{ transform-box: fill-box; transform-origin: left; transform: scaleX(0); animation: grow .7s ease-out forwards; }}
  @keyframes rise {{ from {{ opacity:0; transform: translateY(8px); }} to {{ opacity:1; transform:none; }} }}
  @keyframes grow {{ to {{ transform: scaleX(1); }} }}
  @media (prefers-reduced-motion: reduce) {{ .tile,.bar {{ animation:none; opacity:1; transform:none; }} }}
</style>
{''.join(tiles)}
</svg>"""


# ---------------------------------------------------------------- pulse

QUERY = """query($login:String!){ user(login:$login){ contributionsCollection {
  restrictedContributionsCount
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
}}}"""


def fetch_calendar(user: str, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]


def summarise(cc: dict) -> dict:
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today may not have activity yet
        i -= 1
    while i >= 0 and counts[i]:
        current, i = current + 1, i - 1
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cc["contributionCalendar"]["weeks"]]
    total = cc["contributionCalendar"]["totalContributions"]
    private = cc.get("restrictedContributionsCount", 0)
    recent = sum(counts[-90:])
    return dict(total=total, private=private, current=current, longest=longest, recent=recent,
                active=sum(1 for c in counts if c), best=max(counts or [0]), weeks=weeks[-52:])


def pulse_svg(t: dict, s: dict, updated: str) -> str:
    w, h = 840, 260
    chart_x, chart_y, chart_w, chart_h = 300, 70, 516, 130
    n = len(s["weeks"]) or 1
    peak = max(s["weeks"] or [1]) or 1
    slot = chart_w / n
    bw = max(slot - 3, 2)
    bars = []
    for i, v in enumerate(s["weeks"]):
        bh = max(chart_h * v / peak, 2)
        x = chart_x + i * slot
        bars.append(
            f'<rect class="b" x="{x:.1f}" y="{chart_y + chart_h - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" '
            f'fill="{"url(#g)" if v else t["track"]}" style="animation-delay:{i * 0.018:.3f}s"/>'
        )
    share = f"{round(100 * s['private'] / s['total'])}% in private repos" if s["total"] and s["private"] else "public + private work"
    stats = [("Last 90 days", f"{s['recent']:,}"), ("Longest streak", f"{s['longest']} days"), ("Active days", f"{s['active']} / 365")]
    stat_svg = "".join(
        f'<text x="24" y="{150 + i * 32}" font-size="13" fill="{t["muted"]}">{a}</text>'
        f'<text x="270" y="{150 + i * 32}" font-size="15" font-weight="700" text-anchor="end" fill="{t["text"]}">{b}</text>'
        for i, (a, b) in enumerate(stats)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img" aria-label="Build pulse: {s['total']} contributions in the last year">
<title>Build pulse: {s['total']} contributions in the last year</title>
{_defs(t)}
<style>
  .b {{ transform-box: fill-box; transform-origin: bottom; transform: scaleY(0); animation: up .5s cubic-bezier(.2,.8,.2,1) forwards; }}
  .dot {{ animation: pulse 1.8s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }}
  @keyframes up {{ to {{ transform: scaleY(1); }} }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; transform: scale(1); }} 50% {{ opacity:.35; transform: scale(.7); }} }}
  @media (prefers-reduced-motion: reduce) {{ .b,.dot {{ animation:none; transform:none; }} }}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="{t['card']}" stroke="{t['border']}"/>
<circle class="dot" cx="30" cy="34" r="5" fill="{t['a3']}"/>
<text x="44" y="39" font-size="14" font-weight="700" fill="{t['text']}">BUILD PULSE</text>
<text x="146" y="39" font-size="13" fill="{t['muted']}">· last 12 months · updated {updated}</text>
<text x="24" y="98" font-size="44" font-weight="800" fill="url(#g)">{s['total']:,}</text>
<text x="24" y="122" font-size="13" fill="{t['muted']}">contributions · {share}</text>
{stat_svg}
<line x1="{chart_x}" y1="{chart_y + chart_h + .5}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h + .5}" stroke="{t['border']}"/>
{''.join(bars)}
<text x="{chart_x}" y="{chart_y + chart_h + 24}" font-size="12" fill="{t['muted']}">12 months ago</text>
<text x="{chart_x + chart_w}" y="{chart_y + chart_h + 24}" font-size="12" text-anchor="end" fill="{t['muted']}">this week · peak day {s['best']}</text>
</svg>"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("card", choices=["impact", "pulse"])
    p.add_argument("--out", default="assets")
    a = p.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.card == "impact":
        for name, t in THEMES.items():
            (out / f"impact-{name}.svg").write_text(impact_svg(t))
    else:
        s = summarise(fetch_calendar(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"]))
        updated = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")
        for name, t in THEMES.items():
            (out / f"pulse-{name}.svg").write_text(pulse_svg(t, s, updated))
    print(f"wrote {a.card} cards to {out}/")


if __name__ == "__main__":
    main()
