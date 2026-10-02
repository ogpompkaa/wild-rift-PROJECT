#!/usr/bin/env python3
"""Generuje odznaki tierów (img/tiers/*.svg): heksagonalny kamień w złotej oprawie hextech.
Litery są zamienione na krzywe z fontu Cinzel ExtraBold, więc odznaka wygląda tak samo wszędzie
(na stronie, na stronach bohaterów i w obrazie tier listy rysowanym na canvasie).

Użycie: python3 make_badges.py   (wymaga fontTools; font pobiera z Google Fonts)
"""
import math
import os
import urllib.request

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "img", "tiers")
FONT_URL = "https://fonts.gstatic.com/s/cinzel/v26/8vIU7ww63mVu7gtR-kwKxNvkNOjw-lbgTYo.ttf"  # Cinzel 800

# tier: (plik, jasny, środek, ciemny, poświata)
TIERS = {
    "S+": ("splus", "#fff3c4", "#ffc53d", "#b8650a", "#ffd76a"),
    "S": ("s", "#ffd9b8", "#ff8a3d", "#a8360c", "#ff9a52"),
    "A": ("a", "#d4ffe9", "#3fd893", "#0b7a4d", "#5fe3a1"),
    "B": ("b", "#dcebff", "#5a9cff", "#1c3f9e", "#7ab8ff"),
    "C": ("c", "#eef2f7", "#9fadc2", "#3e4a5e", "#b6c2d4"),
}


def hexpts(cx, cy, r, flat=False):
    pts = []
    for i in range(6):
        a = math.radians(60 * i - (0 if flat else 90))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a) * 1.0))
    return pts


def poly(pts):
    return "M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + "Z"


def glyph_path(font, text, height, cx, baseline, gap=0.0):
    """Ścieżka SVG tekstu wyśrodkowana w poziomie; wysokość wersalików = height."""
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    cap = font["OS/2"].sCapHeight or 700
    scale = height / cap
    names = [cmap[ord(ch)] for ch in text]
    widths = [gs[n].width * scale for n in names]
    total = sum(widths) + gap * (len(names) - 1)
    x = cx - total / 2
    out = []
    for n, w in zip(names, widths):
        pen = SVGPathPen(gs)
        gs[n].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        out.append(pen.getCommands())
        x += w + gap
    return " ".join(out)


def badge(font, tier):
    name, light, mid, dark, glow = TIERS[tier]
    cx, cy = 60, 60
    outer, ring, inner = 54, 47.5, 43
    o, r_, i = hexpts(cx, cy, outer), hexpts(cx, cy, ring), hexpts(cx, cy, inner)
    facets = "".join(f'<path d="M{cx},{cy}L{x:.2f},{y:.2f}"/>' for x, y in i)
    top = poly([(cx, cy), i[5], i[0], i[1]])
    bottom = poly([(cx, cy), i[2], i[3], i[4]])
    if tier == "S+":
        letters = (f'<path d="{glyph_path(font, "S", 40, cx - 6, cy + 20)}"/>'
                   f'<path d="{glyph_path(font, "+", 22, cx + 19, cy + 3)}"/>')
    else:
        letters = f'<path d="{glyph_path(font, tier, 40, cx, cy + 20)}"/>'
    wings = ""
    if tier == "S+":  # złote skrzydła i korona dla najwyższego tieru
        wing = ("M14,36 C4,30 -2,22 -5,12 C0,30 4,38 9,44 C1,44 -4,41 -8,37 C-3,50 3,56 10,58 "
                "C3,61 -1,62 -5,61 C1,70 8,74 14,74 Z")
        inner = "M13,42 C6,38 2,32 0,26 C4,38 8,44 12,48 Z"
        mirror = lambda d: d  # odbicie robi transform
        wings = (f'<g stroke="#4a3812" stroke-width=".9" stroke-linejoin="round">'
                 f'<path d="{wing}" fill="url(#g)"/><path d="{inner}" fill="#fff3c4" opacity=".55" stroke="none"/>'
                 f'<g transform="translate(120,0) scale(-1,1)"><path d="{wing}" fill="url(#g)"/><path d="{inner}" fill="#fff3c4" opacity=".55" stroke="none"/></g>'
                 '<path d="M42,10 L46,-1 L52,6 L60,-8 L68,6 L74,-1 L78,10 Z" fill="url(#g)"/>'
                 '</g><path d="M60,-3 L63,2 L60,7 L57,2 Z" fill="#7ff3ff" stroke="#e8fbff" stroke-width=".6"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -8 132 136" width="132" height="136">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff6dc"/><stop offset=".28" stop-color="#e2c27e"/><stop offset=".55" stop-color="#9c7533"/><stop offset=".8" stop-color="#d9b56a"/><stop offset="1" stop-color="#6e5020"/></linearGradient>
<linearGradient id="gi" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a4316"/><stop offset="1" stop-color="#f3dfa8"/></linearGradient>
<linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{light}"/><stop offset=".45" stop-color="{mid}"/><stop offset="1" stop-color="{dark}"/></linearGradient>
<radialGradient id="h" cx=".5" cy=".38" r=".62"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset=".5" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<linearGradient id="gl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>
<linearGradient id="t" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#fff8ea"/><stop offset="1" stop-color="#f1dcb0"/></linearGradient>
<filter id="s" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="1.6" stdDeviation="1.4" flood-color="#000" flood-opacity=".55"/></filter>
<filter id="o" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4"/></filter>
</defs>
<path d="{poly(hexpts(cx, cy, outer + 2))}" fill="{glow}" opacity=".35" filter="url(#o)"/>
{wings}
<path d="{poly(o)}" fill="url(#g)" stroke="#4a3812" stroke-width="1.2" stroke-linejoin="round"/>
<path d="{poly(r_)}" fill="url(#gi)"/>
<path d="{poly(hexpts(cx, cy, ring - 1.6))}" fill="#0a1426"/>
<path d="{poly(i)}" fill="url(#f)"/>
<path d="{top}" fill="#ffffff" opacity=".14"/>
<path d="{bottom}" fill="#000000" opacity=".16"/>
<g stroke="#ffffff" stroke-opacity=".16" stroke-width=".8">{facets}</g>
<path d="{poly(i)}" fill="url(#h)"/>
<path d="M{i[5][0]:.2f},{i[5][1]:.2f}L{i[0][0]:.2f},{i[0][1]:.2f}L{i[1][0]:.2f},{i[1][1]:.2f}L{i[1][0]:.2f},{cy - 4:.2f}Q{cx},{cy + 6:.2f} {i[5][0]:.2f},{cy - 4:.2f}Z" fill="url(#gl)" opacity=".7"/>
<path d="{poly(i)}" fill="none" stroke="{light}" stroke-opacity=".75" stroke-width="1.4" stroke-linejoin="round"/>
<g fill="url(#t)" stroke="{dark}" stroke-width="2.2" stroke-linejoin="round" paint-order="stroke" filter="url(#s)">{letters}</g>
</svg>'''


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), ".cinzel800.ttf")
    if not os.path.exists(path):
        urllib.request.urlretrieve(FONT_URL, path)
    font = TTFont(path)
    for tier, spec in TIERS.items():
        with open(os.path.join(OUT, spec[0] + ".svg"), "w", encoding="utf-8") as f:
            f.write(badge(font, tier))
    print("Zapisano odznaki:", ", ".join(s[0] for s in TIERS.values()))


if __name__ == "__main__":
    main()
