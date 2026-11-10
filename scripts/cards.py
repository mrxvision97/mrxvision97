#!/usr/bin/env python3
"""Animated, Magic-UI-style SVG cards for the profile README.

  python scripts/cards.py static --out assets   # hero, building, impact, recognition, stack, soon
  python scripts/cards.py live   --out dist     # pulse + open-source repo cards (run by CI daily)

Standard library only. `live` reads GITHUB_TOKEN and GH_USER from the environment
and the featured repo list from featured.json. Each card is written as
<name>-light.svg and <name>-dark.svg; the README picks one with <picture>.

Visual language: border beam, flowing gradient text, aurora glow, dot grid,
staggered reveal. All motion is CSS/SMIL (works inside <img>) and respects
prefers-reduced-motion.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import textwrap
import urllib.request
from html import escape as esc

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Inter','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"
W = 880  # full-width card
HALF = 434  # half-width card (two per row)

THEMES = {
    "dark": dict(card="#0a0a0c", tile="#111115", border="#27272a", text="#fafafa", muted="#a1a1aa",
                 dim="#71717a", dot="#3f3f46", g1="#c084fc", g2="#22d3ee", b1="#ffaa40", b2="#9c40ff",
                 green="#34d399", amber="#fbbf24", cyan="#22d3ee", violet="#a78bfa", track="#1c1c21",
                 glow=".32", sweep="#ffffff", sweep_op=".06", aurora=".40"),
    "light": dict(card="#ffffff", tile="#fafafa", border="#e4e4e7", text="#09090b", muted="#52525b",
                  dim="#a1a1aa", dot="#d4d4d8", g1="#7c3aed", g2="#0891b2", b1="#f59e0b", b2="#9333ea",
                  green="#059669", amber="#d97706", cyan="#0891b2", violet="#7c3aed", track="#f4f4f5",
                  glow=".16", sweep="#7c3aed", sweep_op=".05", aurora=".22"),
}

CSS = """
.beam{animation:beam var(--d,7s) linear infinite}
@keyframes beam{from{stroke-dashoffset:0}to{stroke-dashoffset:-100}}
.rise{animation:rise .8s cubic-bezier(.2,.8,.2,1) backwards}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.6)}}
.ring{transform-box:fill-box;transform-origin:center;animation:ring 2s ease-out infinite}
@keyframes ring{from{opacity:.6;transform:scale(1)}to{opacity:0;transform:scale(2.6)}}
.a1{animation:a1 16s ease-in-out infinite alternate}.a2{animation:a2 19s ease-in-out infinite alternate}.a3{animation:a3 23s ease-in-out infinite alternate}
@keyframes a1{to{transform:translate(120px,40px)}}@keyframes a2{to{transform:translate(-140px,-30px)}}@keyframes a3{to{transform:translate(60px,-50px)}}
.sweep{animation:sweep 6s ease-in-out infinite}
@keyframes sweep{0%{transform:translateX(0)}60%,100%{transform:translateX(1400px)}}
.bar{transform-box:fill-box;transform-origin:bottom;animation:up .6s cubic-bezier(.2,.8,.2,1) backwards}
@keyframes up{from{transform:scaleY(0)}}
.mq{animation:mq var(--d,30s) linear infinite}
@keyframes mq{to{transform:translateX(var(--l))}}
.rot{opacity:0;animation:rot 12s infinite}
@keyframes rot{0%{opacity:0;transform:translateY(10px)}4%,22%{opacity:1;transform:none}26%,100%{opacity:0;transform:translateY(-10px)}}
.bob{animation:bob 3.2s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
.shadow{transform-box:fill-box;transform-origin:center;animation:shadow 3.2s ease-in-out infinite}
@keyframes shadow{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(.8);opacity:.6}}
.blink{transform-box:fill-box;transform-origin:center;animation:blink 4.6s infinite}
@keyframes blink{0%,91%,100%{transform:scaleY(1)}94%{transform:scaleY(.1)}}
.look{animation:look 7s ease-in-out infinite}
@keyframes look{0%,35%,100%{transform:translateX(0)}45%,60%{transform:translateX(5px)}70%,85%{transform:translateX(-4px)}}
.wave{transform-box:fill-box;transform-origin:50% 92%;animation:wave 1.4s ease-in-out infinite}
@keyframes wave{0%,100%{transform:rotate(18deg)}50%{transform:rotate(42deg)}}
.glow{transform-box:fill-box;transform-origin:center;animation:glowb 1.8s ease-in-out infinite}
@keyframes glowb{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(1.35)}}
.ph1{opacity:0;animation:ph1 6s infinite}.ph2{animation:ph2 6s infinite}
@keyframes ph1{0%,36%{opacity:1}42%,94%{opacity:0}100%{opacity:1}}
@keyframes ph2{0%,40%{opacity:0}47%,90%{opacity:1}96%,100%{opacity:0}}
.dt{animation:dt 1s ease-in-out infinite}
@keyframes dt{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-4px)}}
.tw{transform-box:fill-box;transform-origin:center;animation:tw 2.8s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.25;transform:scale(.55) rotate(0)}50%{opacity:1;transform:scale(1) rotate(45deg)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.rise,.bar{opacity:1;transform:none}.rot{opacity:0}.rot0{opacity:1}.ph1{opacity:0}.ph2{opacity:1}}
"""


# ------------------------------------------------------------------ primitives

def doc(w: int, h: int, t: dict, body: str, title: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<defs>
  <linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['g1']}"/><stop offset="1" stop-color="{t['g2']}"/></linearGradient>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w // 2}" y2="0" spreadMethod="repeat">
    <stop offset="0" stop-color="{t['g1']}"/><stop offset=".5" stop-color="{t['g2']}"/><stop offset="1" stop-color="{t['g1']}"/>
    <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{w // 2} 0" dur="6s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t['b1']}"/><stop offset="1" stop-color="{t['b2']}"/></linearGradient>
  <linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['sweep']}" stop-opacity="0"/><stop offset=".5" stop-color="{t['sweep']}" stop-opacity="{t['sweep_op']}"/><stop offset="1" stop-color="{t['sweep']}" stop-opacity="0"/></linearGradient>
  <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.1" fill="{t['dot']}"/></pattern>
  <radialGradient id="fg" cx=".5" cy=".25" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <mask id="fade"><rect width="{w}" height="{h}" fill="url(#fg)"/></mask>
  <clipPath id="clip"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="17"/></clipPath>
  <filter id="blur" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="46"/></filter>
</defs>
<style>{CSS}</style>
{body}
</svg>"""


def frame(w: int, h: int, t: dict, glows=(), dots: bool = True, sweep: bool = False) -> str:
    """Card background: surface, dot grid, aurora glows, optional sweep."""
    g = "".join(
        f'<circle class="{cls}" cx="{x}" cy="{y}" r="{r}" fill="{t[c]}" opacity="{t["glow"]}" filter="url(#blur)"/>'
        for (x, y, r, c, cls) in glows)
    d = f'<rect width="{w}" height="{h}" fill="url(#dots)" mask="url(#fade)"/>' if dots else ""
    s = f'<rect class="sweep" x="-260" y="0" width="260" height="{h}" fill="url(#sw)"/>' if sweep else ""
    return (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="{t["card"]}"/>'
            f'<g clip-path="url(#clip)">{d}{g}{s}</g>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{t["border"]}"/>')


def beam(w: int, h: int, delay: float = 0, dur: float = 7) -> str:
    return (f'<rect class="beam" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="17" fill="none" stroke="url(#beam)" '
            f'stroke-width="1.6" stroke-linecap="round" pathLength="100" stroke-dasharray="14 86" '
            f'style="--d:{dur}s;animation-delay:-{delay}s"/>')


def live_dot(x: float, y: float, color: str) -> str:
    return (f'<circle class="ring" cx="{x}" cy="{y}" r="4" fill="none" stroke="{color}" stroke-width="1.5"/>'
            f'<circle class="pulse" cx="{x}" cy="{y}" r="4" fill="{color}"/>')


def pill(x: float, y: float, label: str, color: str, t: dict, size: int = 11) -> tuple[str, float]:
    tw = len(label) * size * 0.68 + 30
    svg = (f'<rect x="{x}" y="{y}" width="{tw:.0f}" height="24" rx="12" fill="{color}" fill-opacity=".10" stroke="{color}" stroke-opacity=".35"/>'
           f'<circle class="pulse" cx="{x + 13}" cy="{y + 12}" r="3.5" fill="{color}"/>'
           f'<text x="{x + 23}" y="{y + 16}" font-family="{MONO}" font-size="{size}" font-weight="600" letter-spacing=".6" fill="{color}">{esc(label)}</text>')
    return svg, tw


def lines(x: float, y: float, rows: list[str], size: int, fill: str, lh: float = 1.5, cls: str = "", delay: float = 0) -> str:
    out = []
    for i, r in enumerate(rows):
        out.append(f'<text class="{cls}" x="{x}" y="{y + i * size * lh:.1f}" font-size="{size}" fill="{fill}" '
                   f'style="animation-delay:{delay + i * .06:.2f}s">{esc(r)}</text>')
    return "".join(out)


SPARK = "M0,-10 C1.6,-2.2 2.2,-1.6 10,0 C2.2,1.6 1.6,2.2 0,10 C-1.6,2.2 -2.2,1.6 -10,0 C-2.2,-1.6 -1.6,-2.2 0,-10Z"


def sparkle(x: float, y: float, s: float, color: str, delay: float) -> str:
    return (f'<g transform="translate({x},{y}) scale({s})"><path class="tw" d="{SPARK}" fill="{color}" '
            f'style="animation-delay:-{delay}s"/></g>')


def bot(uid: str, c1: str, c2: str, t: dict, delay: float = 0, wave: bool = False) -> str:
    """An original plush-style helper bot, drawn around (0,0). Blinks, glances, bobs."""
    eye, d = "#a5f3fc", f"animation-delay:-{delay}s"
    arm_r = (f'<g class="wave" style="{d}"><rect x="30" y="6" width="13" height="36" rx="6.5" fill="{c2}"/><circle cx="36.5" cy="6" r="8" fill="{c1}"/></g>' if wave
             else f'<rect x="27" y="38" width="13" height="24" rx="6.5" fill="{c2}"/>')
    return f"""<defs><linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<ellipse class="shadow" cx="0" cy="84" rx="34" ry="6" fill="{t['text']}" fill-opacity=".14" style="{d}"/>
<g class="bob" style="{d}">
  <line x1="0" y1="-46" x2="0" y2="-62" stroke="{c2}" stroke-width="3.5" stroke-linecap="round"/>
  <circle class="glow" cx="0" cy="-66" r="6" fill="{c1}" style="{d}"/>
  <rect x="-53" y="-14" width="11" height="26" rx="5.5" fill="{c2}"/><rect x="42" y="-14" width="11" height="26" rx="5.5" fill="{c2}"/>
  <rect x="-40" y="38" width="13" height="24" rx="6.5" fill="{c2}"/>{arm_r}
  <rect x="-27" y="30" width="54" height="40" rx="16" fill="url(#bg{uid})"/>
  <circle class="glow" cx="0" cy="50" r="5" fill="{eye}" style="animation-delay:-{delay + .6}s"/>
  <rect x="-45" y="-46" width="90" height="78" rx="30" fill="url(#bg{uid})"/>
  <ellipse cx="-20" cy="-34" rx="16" ry="7" fill="#fff" fill-opacity=".35" transform="rotate(-18 -20 -34)"/>
  <rect x="-33" y="-30" width="66" height="44" rx="17" fill="#0b0b14"/>
  <g class="look" style="{d}">
    <rect class="blink" x="-19" y="-21" width="10" height="17" rx="5" fill="{eye}" style="{d}"/>
    <rect class="blink" x="9" y="-21" width="10" height="17" rx="5" fill="{eye}" style="{d}"/>
    <path d="M-8 3 Q0 9 8 3" fill="none" stroke="{eye}" stroke-width="2.6" stroke-linecap="round"/>
  </g>
  <circle cx="-25" cy="2" r="3.5" fill="#f472b6" fill-opacity=".7"/><circle cx="25" cy="2" r="3.5" fill="#f472b6" fill-opacity=".7"/>
</g>"""


def bubble(x: float, y: float, text: str, t: dict, delay: float = 0, thinking: bool = False) -> str:
    """Speech bubble centred on x: typing dots (or a 'Thinking' shimmer), then a status line."""
    w = max(len(text) * 7.6 + 30, 96)
    d = f"animation-delay:-{delay}s"
    first = (f'<text x="{x}" y="{y + 20}" text-anchor="middle" font-size="13" font-weight="600" fill="url(#think)">Thinking…</text>' if thinking else
             "".join(f'<circle class="dt" cx="{x - 12 + k * 12}" cy="{y + 15}" r="3.2" fill="{t["muted"]}" style="animation-delay:{k * .15:.2f}s"/>' for k in range(3)))
    return (f'<g><rect x="{x - w / 2:.0f}" y="{y}" width="{w:.0f}" height="30" rx="15" fill="{t["tile"]}" stroke="{t["border"]}"/>'
            f'<path d="M{x - 6} {y + 29.5} L{x} {y + 37} L{x + 6} {y + 29.5}" fill="{t["tile"]}" stroke="{t["border"]}"/>'
            f'<rect x="{x - 7}" y="{y + 27}" width="14" height="3" fill="{t["tile"]}"/>'
            f'<g class="ph1" style="{d}">{first}</g>'
            f'<text class="ph2" x="{x}" y="{y + 20}" text-anchor="middle" font-family="{MONO}" font-size="12.5" font-weight="600" fill="{t["text"]}" style="{d}">{esc(text)}</text></g>')


def think_defs(t: dict) -> str:
    return (f'<defs><linearGradient id="think" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="140" y2="0" spreadMethod="repeat">'
            f'<stop offset="0" stop-color="{t["dim"]}"/><stop offset=".5" stop-color="{t["text"]}"/><stop offset="1" stop-color="{t["dim"]}"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="140 0" dur="1.6s" repeatCount="indefinite"/>'
            f'</linearGradient></defs>')


# ------------------------------------------------------------------ static cards

HERO_ROTATE = [
    "I ship complete applications, from 0 → 1.",
    "Building Unbordr: visa readiness for India.",
    "AI automations for lead gen, marketing & eng.",
    "SuperHack 2025 runner-up · 6× hackathon winner.",
]


def hero(t: dict) -> str:
    w, h = W, 320
    body = [frame(w, h, t, glows=[(140, 40, 150, "b2", "a1"), (760, 300, 170, "g2", "a2"), (520, -30, 120, "b1", "a3")])]
    p, _ = pill(48, 44, "CURRENTLY BUILDING · UNBORDR", t["green"], t)
    body.append(f'<g class="rise">{p}</g>')
    body.append(f'<text class="rise" x="46" y="150" font-size="76" font-weight="800" letter-spacing="-2.5" fill="url(#shine)" style="animation-delay:.1s">Aman Kumar</text>')
    body.append(f'<text class="rise" x="50" y="190" font-size="21" font-weight="500" fill="{t["muted"]}" style="animation-delay:.2s">Product-minded engineer · Bangalore</text>')
    for i, line in enumerate(HERO_ROTATE):
        body.append(f'<text class="rot rot{i}" x="50" y="236" font-family="{MONO}" font-size="19" font-weight="600" fill="{t["text"]}" style="animation-delay:{i * 3}s">'
                    f'<tspan fill="{t["g1"]}">›</tspan> {esc(line)}</text>')
    chips = ["0 → 1 products", "AI-native builder", "6× hackathon winner", "$10K+ in prizes"]
    x = 50
    for i, c in enumerate(chips):
        cw = len(c) * 7.4 + 26
        body.append(f'<g class="rise" style="animation-delay:{.35 + i * .08:.2f}s"><rect x="{x}" y="262" width="{cw:.0f}" height="28" rx="8" fill="{t["tile"]}" stroke="{t["border"]}"/>'
                    f'<text x="{x + cw / 2:.0f}" y="281" text-anchor="middle" font-size="13" font-weight="600" fill="{t["muted"]}">{esc(c)}</text></g>')
        x += cw + 10
    body.append(think_defs(t))
    for (sx, sy, sc, col, dl) in [(650, 92, .9, "g1", 0), (842, 120, .7, "g2", 1.1), (668, 250, .6, "b1", 2), (835, 262, 1, "g1", .6), (612, 168, .5, "g2", 1.7)]:
        body.append(sparkle(sx, sy, sc, t[col], dl))
    body.append(bubble(748, 34, "shipping Unbordr", t, thinking=True))
    body.append(f'<g transform="translate(748,178) scale(1.18)">{bot("h", "#c084fc", "#22d3ee", t, wave=True)}</g>')
    body.append(beam(w, h, dur=8))
    return doc(w, h, t, "".join(body), "Aman Kumar, product-minded engineer in Bangalore. Currently building Unbordr.")


BUILDING = [
    dict(slug="unbordr", n="01", status="LIVE", c="green", title="Unbordr", foot="unbordr.in ↗",
         text="Schengen visa readiness for Indian applicants: readiness score, checklist, cover letter, pre-filled forms."),
    dict(slug="flywheel", n="02", status="INVITE-ONLY SOON", c="violet", title="Flywheel", foot="experienceflywheel.ai ↗",
         text="A creative platform for briefs, production, reviews, approvals and delivery. Built for internal teams first."),
    dict(slug="automations", n="03", status="ONGOING", c="cyan", title="AI automations", foot="lead gen · workflows · marketing · eng",
         text="Lead generation, workflow orchestration, marketing ops and engineering automations that take repetitive work off people."),
    dict(slug="fintech", n="04", status="CONTRACT", c="amber", title="Fintech workflows", foot="product · backend · automation",
         text="Collection-workflow automation and internal backend processes for a fintech team."),
]


def building(t: dict, b: dict, i: int) -> str:
    w, h = HALF, 250
    body = [frame(w, h, t, glows=[(w - 30, 10, 110, b["c"], "a1")])]
    body.append(f'<text x="28" y="44" font-family="{MONO}" font-size="12" font-weight="600" fill="{t["dim"]}">{b["n"]}</text>')
    p, pw = pill(0, 0, b["status"], t[b["c"]], t)
    body.append(f'<g transform="translate({w - 28 - pw:.0f},26)">{p}</g>')
    body.append(f'<text class="rise" x="26" y="100" font-size="32" font-weight="800" letter-spacing="-.8" fill="{t["text"]}">{esc(b["title"])}</text>')
    rows = textwrap.wrap(b["text"], 46, break_on_hyphens=False)
    assert len(rows) <= 3, f"{b['slug']} text too long for card"
    body.append(lines(28, 134, rows, 15.5, t["muted"], cls="rise", delay=.1))
    body.append(f'<line x1="28" y1="{h - 52}" x2="{w - 28}" y2="{h - 52}" stroke="{t["border"]}"/>')
    body.append(f'<text x="28" y="{h - 24}" font-family="{MONO}" font-size="13" font-weight="600" fill="url(#tg)">{esc(b["foot"])}</text>')
    return doc(w, h, t, "".join(body), f"{b['title']}: {b['text']}")


IMPACT = [
    ("$7,000", "SuperHack 2025 runner-up", "out of 10,000+ teams worldwide"),
    ("6×", "Hackathon wins", "$10,000+ in cumulative prizes"),
    ("60%", "LLM cost cut", "token optimisation, live platform"),
    ("100+", "Users scaled", "agentic chatbot, built from scratch"),
    ("89%", "Forecast precision", "IoT failures, 4+ hours ahead"),
    ("+20%", "Edge inference speed", "ship-hull detection, 50K+ images"),
]


def impact(t: dict) -> str:
    cols, pad, gap, tw, th = 3, 18, 12, 270, 150
    w = pad * 2 + cols * tw + (cols - 1) * gap
    rows = (len(IMPACT) + cols - 1) // cols
    h = pad * 2 + rows * th + (rows - 1) * gap
    body = [frame(w, h, t, glows=[(w / 2, h + 40, 220, "b2", "a2")], sweep=True)]
    for i, (big, label, sub) in enumerate(IMPACT):
        x, y = pad + (i % cols) * (tw + gap), pad + (i // cols) * (th + gap)
        body.append(f'<g class="rise" style="animation-delay:{i * .1:.1f}s">'
                    f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="14" fill="{t["tile"]}" fill-opacity=".85" stroke="{t["border"]}"/>'
                    f'<text x="{x + 22}" y="{y + 66}" font-size="46" font-weight="800" letter-spacing="-1.5" fill="url(#shine)">{esc(big)}</text>'
                    f'<text x="{x + 22}" y="{y + 100}" font-size="17" font-weight="700" fill="{t["text"]}">{esc(label)}</text>'
                    f'<text x="{x + 22}" y="{y + 124}" font-size="13.5" fill="{t["muted"]}">{esc(sub)}</text></g>')
    return doc(w, h, t, "".join(body), "Selected impact: " + "; ".join(f"{a} {b}" for a, b, _ in IMPACT))


HACKS = [
    ("2nd", "#a1a1aa", "SuperHack 2025 · global", "Runner-up · $7,000 · 10,000+ teams"),
    ("1st", "#f59e0b", "IEEE Global Hack", "Winner"),
    ("1st", "#f59e0b", "IEEE Group Video Competition", "First place"),
    ("3rd", "#c2410c", "Bhashini Technathon", "Third place · special recognition"),
    ("T17", "#8b5cf6", "GST Analytics Hackathon 2024", "Top 17 of 900+ teams · ₹25,000"),
]
ACADEMIC = [
    ("B.Tech", "B.Tech Computer Science", "Vidyashilp University · 2022–2026"),
    ("Schol.", "Full scholarship", "Vidyashilp University & Vidyagyan School"),
    ("IEEE", "Vice Chair, IEEE Student Branch", "Vidyashilp University · 2023–2025"),
]


def recognition(t: dict) -> str:
    w, h = W, 400
    body = [frame(w, h, t, glows=[(80, 0, 140, "b1", "a1"), (820, 400, 150, "b2", "a2")])]

    def col(x: int, eyebrow: str, big: str, small: str, rows, badge_w: int) -> None:
        body.append(f'<text x="{x}" y="50" font-family="{MONO}" font-size="12" font-weight="600" letter-spacing="1.5" fill="{t["dim"]}">{esc(eyebrow)}</text>')
        body.append(f'<text class="rise" x="{x - 2}" y="98" font-size="38" font-weight="800" letter-spacing="-1" fill="url(#shine)">{esc(big)}</text>')
        body.append(f'<text class="rise" x="{x}" y="124" font-size="14" fill="{t["muted"]}" style="animation-delay:.1s">{esc(small)}</text>')
        for i, (tag, color, name, detail) in enumerate(rows):
            y = 162 + i * 46
            col_ = color if color.startswith("#") else t[color]
            body.append(f'<g class="rise" style="animation-delay:{.15 + i * .08:.2f}s">'
                        f'<rect x="{x}" y="{y}" width="{badge_w}" height="32" rx="9" fill="{col_}" fill-opacity=".12" stroke="{col_}" stroke-opacity=".5"/>'
                        f'<text x="{x + badge_w / 2}" y="{y + 21}" text-anchor="middle" font-family="{MONO}" font-size="11.5" font-weight="700" fill="{col_}">{esc(tag)}</text>'
                        f'<text x="{x + badge_w + 14}" y="{y + 13}" font-size="15" font-weight="700" fill="{t["text"]}">{esc(name)}</text>'
                        f'<text x="{x + badge_w + 14}" y="{y + 31}" font-size="13" fill="{t["muted"]}">{esc(detail)}</text></g>')

    col(36, "HACKATHONS", "6× winner", "$10,000+ in prizes across AI, ML and robotics", HACKS, 44)
    body.append(f'<line x1="452" y1="36" x2="452" y2="{h - 36}" stroke="{t["border"]}" stroke-dasharray="3 5"/>')
    col(484, "ACADEMICS & LEADERSHIP", "Valedictorian", "Class of 2026", [(a, "violet", b, c) for a, b, c in ACADEMIC], 58)
    alt = "Recognition: 6× hackathon winner, $10,000+ in prizes. " + "; ".join(f"{n}: {d}" for _, _, n, d in HACKS) + \
          ". Valedictorian, Class of 2026. " + "; ".join(f"{n}, {d}" for _, n, d in ACADEMIC)
    return doc(w, h, t, "".join(body), alt)


STACK = [
    [("Python", "#3776ab"), ("TypeScript", "#3178c6"), ("React", "#61dafb"), ("Django", "#44b78b"), ("FastAPI", "#009688"),
     ("SQL", "#5b8def"), ("AWS", "#ff9900"), ("Docker", "#2496ed"), ("Kubernetes", "#326ce5")],
    [("PyTorch", "#ee4c2c"), ("TensorFlow", "#ff6f00"), ("LangChain", "#22c55e"), ("Hugging Face", "#ffd21e"), ("MLflow", "#0194e2"),
     ("Multi-agent systems", "#c084fc"), ("LLM apps", "#22d3ee")],
]


def stack(t: dict) -> str:
    w, h = W, 150
    body = [frame(w, h, t, dots=True)]
    body.append(f'<defs><linearGradient id="edge" x1="0" x2="1"><stop offset="0" stop-color="#000"/><stop offset=".1" stop-color="#fff"/>'
                f'<stop offset=".9" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
                f'<mask id="edges"><rect width="{w}" height="{h}" fill="url(#edge)"/></mask></defs>')
    body.append('<g mask="url(#edges)" clip-path="url(#clip)">')
    for r, items in enumerate(STACK):
        y = 30 + r * 52
        seq, x = [], 0.0
        while x < w + 40:  # repeat until one sequence covers the card
            for name, color in items:
                pw = len(name) * 8.1 + 44
                seq.append((x, name, color, pw))
                x += pw + 12
        period = x
        g = []
        for k in (0, 1):
            for (px, name, color, pw) in seq:
                ox = px + k * period
                g.append(f'<rect x="{ox:.0f}" y="{y}" width="{pw:.0f}" height="38" rx="19" fill="{t["tile"]}" stroke="{t["border"]}"/>'
                         f'<circle cx="{ox + 20:.0f}" cy="{y + 19}" r="5" fill="{color}"/>'
                         f'<text x="{ox + 32:.0f}" y="{y + 24}" font-size="14.5" font-weight="600" fill="{t["text"]}">{esc(name)}</text>')
        direction = -period if r == 0 else period
        start = 0 if r == 0 else -period
        body.append(f'<g transform="translate({start:.0f},0)"><g class="mq" style="--l:{direction:.0f}px;--d:{period / 28:.0f}s">{"".join(g)}</g></g>')
    body.append('</g>')
    names = ", ".join(n for row in STACK for n, _ in row)
    return doc(w, h, t, "".join(body), f"Stack: {names}")


CREW = [
    ("Scout", "Lead gen", "scouting leads", "#c4b5fd", "#7c3aed"),
    ("Relay", "Workflows", "syncing tools", "#a5f3fc", "#0891b2"),
    ("Pixel", "Marketing", "drafting posts", "#fde68a", "#f59e0b"),
    ("Patch", "Engineering", "running QA", "#fbcfe8", "#db2777"),
]


def crew(t: dict) -> str:
    w, h = W, 330
    body = [frame(w, h, t, glows=[(220, 330, 160, "b2", "a1"), (660, 0, 150, "g2", "a2")])]
    body.append(think_defs(t))
    for i, (name, role, task, c1, c2) in enumerate(CREW):
        cx = 110 + i * 220
        body.append(bubble(cx, 30, task + "…", t, delay=i * 1.5))
        body.append(f'<g transform="translate({cx},166)">{bot(str(i), c1, c2, t, delay=i * .9, wave=(i == 0))}</g>')
        body.append(f'<text x="{cx}" y="286" text-anchor="middle" font-size="17" font-weight="800" fill="{t["text"]}">{name}</text>')
        body.append(f'<text x="{cx}" y="307" text-anchor="middle" font-family="{MONO}" font-size="12" font-weight="600" fill="url(#tg)">{role.upper()}</text>')
    for (sx, sy, sc, col, dl) in [(220, 120, .6, "g1", .4), (440, 210, .5, "g2", 1.3), (660, 110, .55, "b1", 2.1), (860, 200, .5, "g1", .9), (24, 210, .5, "g2", 1.8)]:
        body.append(sparkle(sx, sy, sc, t[col], dl))
    return doc(w, h, t, "".join(body), "The automation crew: agents for lead generation, workflows, marketing and engineering.")


def soon(t: dict) -> str:
    w, h = W, 96
    body = [frame(w, h, t, glows=[(w / 2, h + 30, 160, "b2", "a1")], sweep=True)]
    body.append(f'<rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="12" fill="none" stroke="{t["dim"]}" stroke-opacity=".6" stroke-dasharray="5 6"/>')
    body.append(live_dot(44, h / 2, t["amber"]))
    body.append(f'<text x="64" y="{h / 2 - 3}" font-size="17" font-weight="800" fill="url(#shine)">More open source on the way</text>')
    body.append(f'<text x="64" y="{h / 2 + 19}" font-size="13.5" fill="{t["muted"]}">Open-sourcing the tooling behind my products. Watch this space.</text>')
    body.append(f'<text x="{w - 40}" y="{h / 2 + 5}" text-anchor="end" font-family="{MONO}" font-size="12.5" font-weight="600" fill="{t["dim"]}">git push --soon</text>')
    return doc(w, h, t, "".join(body), "More open source on the way.")


# ------------------------------------------------------------------ live cards

QUERY = """query($login:String!){ user(login:$login){ contributionsCollection {
  restrictedContributionsCount
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
}}}"""


def gh(url: str, token: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                                 headers={"Authorization": f"bearer {token}", "User-Agent": "profile-cards",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def summarise(cc: dict) -> dict:
    weeks_raw = cc["contributionCalendar"]["weeks"]
    counts = [d["contributionCount"] for wk in weeks_raw for d in wk["contributionDays"]]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    weeks = [sum(d["contributionCount"] for d in wk["contributionDays"]) for wk in weeks_raw][-52:]
    return dict(total=cc["contributionCalendar"]["totalContributions"], private=cc.get("restrictedContributionsCount", 0),
                longest=longest, recent=sum(counts[-90:]), active=sum(1 for c in counts if c),
                best=max(counts or [0]), weeks=weeks)


def pulse(t: dict, s: dict, updated: str) -> str:
    w, h = W, 270
    cx, cy, cw, ch = 316, 78, 528, 132
    body = [frame(w, h, t, glows=[(cx + cw / 2, h + 50, 200, "b2", "a2"), (60, 20, 110, "g2", "a1")])]
    body.append(live_dot(38, 40, t["green"]))
    body.append(f'<text x="54" y="45" font-family="{MONO}" font-size="12.5" font-weight="700" letter-spacing="1.5" fill="{t["text"]}">BUILD PULSE</text>')
    body.append(f'<text x="160" y="45" font-size="13" fill="{t["dim"]}">last 12 months · auto-updated {updated}</text>')
    body.append(f'<text class="rise" x="34" y="112" font-size="52" font-weight="800" letter-spacing="-1.5" fill="url(#shine)">{s["total"]:,}</text>')
    share = f"contributions · {round(100 * s['private'] / s['total'])}% in private repos" if s["total"] and s["private"] else "contributions, public + private"
    body.append(f'<text x="36" y="138" font-size="13.5" fill="{t["muted"]}">{esc(share)}</text>')
    for i, (a, b) in enumerate([("Last 90 days", f"{s['recent']:,}"), ("Longest streak", f"{s['longest']} days"), ("Active days", f"{s['active']} / 365")]):
        y = 176 + i * 30
        body.append(f'<text x="36" y="{y}" font-size="13.5" fill="{t["muted"]}">{a}</text>'
                    f'<text x="282" y="{y}" text-anchor="end" font-size="15" font-weight="700" fill="{t["text"]}">{b}</text>')
    n, peak = len(s["weeks"]) or 1, max(s["weeks"] or [1]) or 1
    slot = cw / n
    for i, v in enumerate(s["weeks"]):
        bh = max(ch * v / peak, 3)
        body.append(f'<rect class="bar" x="{cx + i * slot:.1f}" y="{cy + ch - bh:.1f}" width="{max(slot - 3, 2):.1f}" height="{bh:.1f}" rx="2.5" '
                    f'fill="{"url(#tg)" if v else t["track"]}" style="animation-delay:{i * .02:.2f}s"/>')
    body.append(f'<line x1="{cx}" y1="{cy + ch + .5}" x2="{cx + cw}" y2="{cy + ch + .5}" stroke="{t["border"]}"/>')
    body.append(f'<text x="{cx}" y="{cy + ch + 26}" font-size="12" fill="{t["dim"]}">12 months ago</text>')
    body.append(f'<text x="{cx + cw}" y="{cy + ch + 26}" text-anchor="end" font-size="12" fill="{t["dim"]}">this week · peak day {s["best"]}</text>')
    body.append(beam(w, h, dur=9, delay=3))
    return doc(w, h, t, "".join(body), f"Build pulse: {s['total']} contributions in the last 12 months")


LANG = {"Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Go": "#00ADD8", "Rust": "#dea584"}


def ago(iso: str) -> str:
    d = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if d < 1:
        return "today"
    if d < 30:
        return f"{d}d ago"
    if d < 365:
        return f"{d // 30}mo ago"
    return f"{d // 365}y ago"


def repo_card(t: dict, r: dict, tagline: str | None, i: int) -> str:
    w, h = HALF, 230
    body = [frame(w, h, t, glows=[(w - 20, 0, 100, "b2" if i % 2 else "g2", "a1")])]
    p, pw = pill(0, 0, "OPEN SOURCE", t["green"], t)
    body.append(f'<g transform="translate({w - 28 - pw:.0f},26)">{p}</g>')
    body.append(f'<text x="28" y="44" font-family="{MONO}" font-size="12.5" font-weight="600" fill="{t["dim"]}">{esc(r["owner"]["login"])} /</text>')
    body.append(f'<text class="rise" x="26" y="88" font-size="30" font-weight="800" letter-spacing="-.8" fill="{t["text"]}">{esc(r["name"])}</text>')
    desc = textwrap.wrap(tagline or r.get("description") or "", 46, break_on_hyphens=False)
    if len(desc) > 3:
        desc = desc[:3]
        desc[-1] = desc[-1].rstrip(".,; ") + "…"
    body.append(lines(28, 120, desc, 15, t["muted"], cls="rise", delay=.1))
    body.append(f'<line x1="28" y1="{h - 50}" x2="{w - 28}" y2="{h - 50}" stroke="{t["border"]}"/>')
    lang = r.get("language") or "Code"
    meta = [f'<circle cx="34" cy="{h - 26}" r="5" fill="{LANG.get(lang, t["g1"])}"/>',
            f'<text x="46" y="{h - 21}" font-size="13" font-weight="600" fill="{t["muted"]}">{esc(lang)}</text>',
            f'<text x="{46 + len(lang) * 8 + 18}" y="{h - 21}" font-size="13" fill="{t["muted"]}">★ {r["stargazers_count"]}</text>',
            f'<text x="{w - 28}" y="{h - 21}" text-anchor="end" font-family="{MONO}" font-size="12.5" fill="url(#tg)">updated {ago(r["pushed_at"])}</text>']
    body.extend(meta)
    return doc(w, h, t, "".join(body), f"{r['name']}: {tagline or r.get('description') or ''}")


# ------------------------------------------------------------------ main

def write(out: pathlib.Path, name: str, fn) -> None:
    for theme, t in THEMES.items():
        (out / f"{name}-{theme}.svg").write_text(fn(t))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["static", "live"])
    ap.add_argument("--out", default="assets")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == "static":
        write(out, "hero", hero)
        for i, b in enumerate(BUILDING):
            write(out, f"build-{b['slug']}", lambda t, b=b, i=i: building(t, b, i))
        write(out, "impact", impact)
        write(out, "recognition", recognition)
        write(out, "stack", stack)
        write(out, "soon", soon)
        write(out, "crew", crew)
    else:
        user, token = os.environ["GH_USER"], os.environ["GITHUB_TOKEN"]
        data = gh("https://api.github.com/graphql", token, {"query": QUERY, "variables": {"login": user}})
        if "errors" in data:
            raise SystemExit(f"GraphQL error: {data['errors']}")
        s = summarise(data["data"]["user"]["contributionsCollection"])
        updated = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")
        write(out, "pulse", lambda t: pulse(t, s, updated))
        for i, f in enumerate(json.loads((ROOT / "featured.json").read_text())):
            r = gh(f"https://api.github.com/repos/{user}/{f['repo']}", token)
            write(out, f"repo-{f['repo']}", lambda t, r=r, f=f, i=i: repo_card(t, r, f.get("tagline"), i))
    print(f"wrote {a.mode} cards to {out}/")


if __name__ == "__main__":
    main()
