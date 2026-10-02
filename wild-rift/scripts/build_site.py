#!/usr/bin/env python3
"""Składa wersję strony na GitHub Pages: kopiuje aplikację i generuje osobną, statyczną stronę dla każdego bohatera
(c/<id>/index.html) z tytułem, opisem i podglądem linku, plus sitemap.xml i robots.txt.

Użycie:  python3 build_site.py <katalog_wyjściowy>
"""
import html
import re
import json
import os
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_URL = "https://ogpompkaa.github.io/wild-rift-PROJECT/"
ROLE_PL = {"baron": "Baron", "jungle": "Dżungla", "mid": "Mid", "dragon": "Smok (ADC)", "support": "Wsparcie"}
ROLE_ORDER = ["baron", "jungle", "mid", "dragon", "support"]
TIER_POINTS = {"S+": 5, "S": 4, "A": 3, "B": 2, "C": 1}
TIER_FILE = {"S+": "splus", "S": "s", "A": "a", "B": "b", "C": "c"}
e = html.escape


def pct(v):
    return "—" if v is None else f"{v:.1f}%".replace(".", ",")


LANE_SVG = {
    "baron": '<path d="M3 3h15.5l-4 4H7v7.5l-4 4z"/><path d="M10 10h11v11H10z" opacity=".38"/>',
    "mid": '<path d="M16.5 3H21v4.5L7.5 21H3v-4.5z"/><path d="M3 3h8.5L3 11.5zM21 21h-8.5l8.5-8.5z" opacity=".38"/>',
    "dragon": '<path d="M21 21H5.5l4-4H17V9.5l4-4z"/><path d="M3 3h11v11H3z" opacity=".38"/>',
    "jungle": '<path d="M5.5 2.5c2.6 3.3 3.6 7.6 2.3 12.6L6.6 21c3.7-4.3 4.4-9.7 1.9-15.2zM12 2c1.6 4.2 1.7 8.8.1 13.6L12 22c2.6-5.3 2.8-11.4-.2-17.6zM18.5 2.5c-.6 4.4-2 8.6-4.4 12.4L12.9 21c4.2-4.5 6.2-10 5.8-16.2z"/>',
    "support": '<path d="M12 3.2l3.2 3.6L12 11 8.8 6.8z"/><path d="M1.8 7.6h6.6l2.3 3.3-2.3 3.2H4.8zM22.2 7.6h-6.6l-2.3 3.3 2.3 3.2h3.6z" opacity=".85"/><path d="M10.2 12.6h3.6l-.9 8.2h-1.8z"/>',
}


def lane_icon(role):
    return f'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">{LANE_SVG[role]}</svg>'


def page(cid, entries, meta):
    names = meta.get("names", {})
    icons = meta.get("itemIcons", {})
    name = entries[0]["name"]
    best = max(entries, key=lambda c: TIER_POINTS.get(c["tier"], 0))
    st = best["stats"].get("1") or best["stats"].get("0")
    roles_txt = ", ".join(ROLE_PL[c["role"]] for c in entries)
    k = meta.get("counters", {}).get(cid, {})
    weak = [names.get(x, x) for x in k.get("weak", [])]
    build = meta.get("builds", {}).get(cid, [])
    patch = meta.get("patch") or ""
    title = f"{name} – kontry, build i win rate · Wild Rift {patch} · Rift Meta"
    desc = (f"{name} w Wild Rift (patch {patch}): tier {best['tier']} na linii {ROLE_PL[best['role']]}"
            + (f", win rate {pct(st[0])} w Diament+" if st else "")
            + (f". Kontrują go: {', '.join(weak[:3])}" if weak else "")
            + ". Statystyki, kontry i build po polsku.")
    url = f"{SITE_URL}c/{cid}/"
    img = f"{SITE_URL}img/splash/{cid}.webp"

    role_rows = []
    for c in sorted(entries, key=lambda c: ROLE_ORDER.index(c["role"])):
        s = c["stats"].get("1") or c["stats"].get("0")
        role_rows.append(
            f'<tr><td><span class="lane">{lane_icon(c["role"])}{e(ROLE_PL[c["role"]])}</span></td>'
            f'<td><img class="tb" src="../../img/tiers/{TIER_FILE.get(c["tier"], "c")}.svg" alt="Tier {e(c["tier"])}" width="40" height="41"></td>'
            f'<td>{pct(s[0]) if s else "—"}</td><td>{pct(s[1]) if s else "—"}</td><td>{pct(s[2]) if s else "—"}</td></tr>')

    def champ_list(ids, cls):
        return "".join(
            f'<a class="ch {cls}" href="../{e(x)}/"><img src="../../img/champions/{e(x)}.webp" alt="" width="30" height="30" loading="lazy">{e(names.get(x, x))}</a>'
            for x in ids) or '<span class="mut">Brak danych.</span>'

    def item(i, n):
        f = icons.get(i)
        ic = f'<img src="../../img/items/{e(f)}" alt="" width="52" height="52" loading="lazy">' if f else ""
        return f'<li><span class="ii">{ic}<span class="n">{n}</span></span><span>{e(i)}</span></li>'

    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Rift Meta">
<meta property="og:title" content="{e(name)} – Wild Rift {e(patch)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(img)}"><meta property="og:image:width" content="960"><meta property="og:image:height" content="533"><meta property="og:locale" content="pl_PL">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800&family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap">
<style>
:root{{color-scheme:dark;--bg:#050c20;--bg2:#08304a;--fg:#f0e6d2;--fg2:#dfe8f1;--muted:#9aaec4;--line:rgba(140,220,240,.14);--line-hi:rgba(140,230,245,.45);--hex:#4fe0f0;--gold:#c8aa6e;
--gold-grad:linear-gradient(170deg,#f7ecd3 0%,#c8aa6e 42%,#8a6a2f 70%,#c8aa6e 100%);--up:#5fe3a1;--down:#ff7468;--t-splus:#ffcf5c;--t-s:#ff9a52;--t-a:#4fdca4;--t-b:#66a6ff;--t-c:#9aa7ba;
--hexpath:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%)}}
*{{box-sizing:border-box}}
body{{margin:0;padding:0 16px 56px;min-height:100vh;color:var(--fg2);font:15px/1.55 Barlow,system-ui,sans-serif;
background:radial-gradient(1000px 600px at 85% -10%,rgba(79,224,240,.18),transparent 60%),linear-gradient(172deg,var(--bg),#081a3a 45%,var(--bg2));background-attachment:fixed}}
.w{{max-width:780px;margin:0 auto}}a{{color:var(--hex)}}img{{display:block}}
.top{{display:flex;justify-content:space-between;align-items:center;padding:18px 0}}
.brand{{font:800 22px Cinzel,Georgia,serif;background:linear-gradient(180deg,#fff8e6,#c8aa6e);-webkit-background-clip:text;background-clip:text;color:transparent;text-decoration:none}}
.patch{{display:inline-flex;align-items:center;gap:9px;padding:4px 14px 4px 5px;border-radius:13px;border:1.5px solid transparent;background:linear-gradient(180deg,#16305a,#0a1830) padding-box,linear-gradient(160deg,#fff3d0,#c8aa6e 40%,#6e5020 75%,#c8aa6e) border-box;box-shadow:0 0 18px rgba(200,170,110,.22)}}
.pg{{width:26px;height:30px;position:relative;clip-path:var(--hexpath);background:linear-gradient(170deg,#fff3d0,#c8aa6e 45%,#6e5020)}}.pg::before{{content:"";position:absolute;inset:3px;clip-path:var(--hexpath);background:radial-gradient(70% 60% at 50% 30%,#d9fbff,#4fe0f0 45%,#0b6a86)}}
.pt2{{display:grid;gap:2px;line-height:1}}.pt2 small{{font:700 9px "Barlow Condensed",sans-serif;letter-spacing:.26em;color:var(--gold)}}.pt2 b{{font:800 17px Cinzel,serif;color:var(--fg)}}
.hero{{position:relative;border-radius:20px;overflow:hidden;min-height:280px;display:flex;align-items:flex-end;isolation:isolate;box-shadow:0 0 0 1px rgba(200,170,110,.45),0 18px 40px rgba(0,0,0,.4)}}
.hero>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:60% 25%;z-index:-2}}
.hero::after{{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(5,12,32,.05),rgba(5,12,32,.55) 55%,rgba(5,12,32,.96))}}
.hb{{display:flex;gap:16px;align-items:flex-end;padding:20px;width:100%}}
.av{{width:82px;height:82px;border-radius:50%;box-shadow:0 0 0 3px var(--gold),0 0 0 6px rgba(4,14,30,.95),0 0 24px rgba(79,224,240,.4);flex:none}}
h1{{font:800 clamp(30px,7vw,46px)/1 Cinzel,Georgia,serif;margin:0;color:#fff8e6;text-shadow:0 3px 18px rgba(0,0,0,.7)}}
.sub{{color:var(--fg2);margin:8px 0 0;font:600 13px "Barlow Condensed",sans-serif;letter-spacing:.12em;text-transform:uppercase}}
.card{{position:relative;background:rgba(9,22,46,.72);border-radius:18px;padding:18px;margin-top:12px;box-shadow:0 0 0 1px var(--line),0 10px 30px rgba(0,0,0,.25)}}
h2{{font:600 12.5px/1 "Barlow Condensed",sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:0 0 14px}}
table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
th,td{{text-align:right;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:middle}}th:first-child,td:first-child{{text-align:left}}
th{{font:600 11.5px "Barlow Condensed",sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}}
.lane{{display:inline-flex;align-items:center;gap:8px;font-weight:600;color:var(--fg)}}.ic{{width:18px;height:18px;fill:var(--hex)}}
.tb{{width:40px;height:auto;display:block;margin-left:auto;filter:drop-shadow(0 2px 4px rgba(0,0,0,.4))}}
[data-tier="S+"]{{--tc:var(--t-splus)}}[data-tier="S"]{{--tc:var(--t-s)}}[data-tier="A"]{{--tc:var(--t-a)}}[data-tier="B"]{{--tc:var(--t-b)}}[data-tier="C"]{{--tc:var(--t-c)}}
.list{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}}
.ch{{display:flex;align-items:center;gap:10px;padding:6px 10px 6px 6px;border-radius:12px;background:rgba(255,255,255,.045);border:1px solid var(--line);color:var(--fg);text-decoration:none;font-weight:600}}
.ch:hover{{border-color:var(--line-hi)}}.ch img{{border-radius:50%;box-shadow:0 0 0 1.5px var(--ring),0 0 0 3px rgba(4,14,30,.9)}}.weak{{--ring:var(--down)}}.strong{{--ring:var(--up)}}
.build{{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:14px 8px;margin:0;padding:0;list-style:none}}
.build li{{display:grid;justify-items:center;gap:7px;text-align:center;font-size:12.5px}}
.ii{{position:relative;width:52px;height:52px;border-radius:11px;overflow:hidden;background:#0a1830;box-shadow:0 0 0 1.5px var(--gold),0 0 0 3.5px rgba(4,14,30,.9)}}
.ii img{{width:100%;height:100%}}.ii .n{{position:absolute;top:0;left:0;padding:2px 5px;background:rgba(4,14,30,.85);border-bottom-right-radius:7px;font:700 11px "Barlow Condensed";color:var(--fg)}}
.cta{{display:inline-flex;margin-top:16px;padding:13px 20px;border-radius:12px;background:linear-gradient(180deg,#9af3fb,var(--hex) 45%,#1fb0cd);color:#04121f;font:700 14px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase;text-decoration:none;box-shadow:0 0 18px rgba(79,224,240,.38)}}
.mut,footer{{color:var(--muted);font-size:13px}}footer{{margin-top:28px}}
</style></head><body><div class="w">
<div class="top"><a class="brand" href="../../">Rift Meta</a><span class="patch"><span class="pg"></span><span class="pt2"><small>PATCH</small><b>{e(patch)}</b></span></span></div>
<div class="hero"><img src="../../img/splash/{e(cid)}.webp" alt=""><div class="hb"><img class="av" src="../../img/champions/{e(cid)}.webp" alt="{e(name)}" width="82" height="82"><div><h1>{e(name)}</h1><p class="sub">{e(roles_txt)} · Wild Rift {e(patch)}</p></div></div></div>
<div class="card"><h2>Tier i statystyki · Diament+ · serwer CN</h2>
<table><thead><tr><th>Linia</th><th>Tier</th><th>Win</th><th>Pick</th><th>Ban</th></tr></thead><tbody>{"".join(role_rows)}</tbody></table></div>
<div class="card"><h2>Ma trudno przeciwko</h2><div class="list">{champ_list(k.get("weak", []), "weak")}</div></div>
<div class="card"><h2>Dobrze radzi sobie z</h2><div class="list">{champ_list(k.get("strong", []), "strong")}</div></div>
{f'<div class="card"><h2>Podstawowy build</h2><ol class="build">{"".join(item(i, n + 1) for n, i in enumerate(build))}</ol></div>' if build else ""}
<a class="cta" href="../../#{e(cid)}">Trend win rate i tier lista →</a>
<footer>Statystyki: Tencent (serwer CN). Tier lista, kontry i buildy: <a href="https://www.wildriftmeta.com/">WildRiftMeta</a>.
Rift Meta to strona fanowska, niezwiązana z Riot Games ani Tencent. Grafiki są własnością Riot Games, Inc.</footer>
</div></body></html>
"""


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_site"))
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        index_html = f.read()
    for d in ("data", "img"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(out, d))
    with open(os.path.join(ROOT, "data", "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)

    # podgląd linku strony głównej: splash aktualnego „Króla patcha”
    cands = [c for c in meta["champions"] if (c["stats"].get("1") or [0, 0])[1] >= 2]
    if cands:
        k = max(cands, key=lambda c: (c["score"], c["stats"]["1"][0]))
        index_html = re.sub(r'(<meta property="og:image" content=")[^"]*', rf'\g<1>{SITE_URL}img/splash/{k["id"]}.webp', index_html, count=1)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    by_id = {}
    for c in meta["champions"]:
        by_id.setdefault(c["id"], []).append(c)
    for cid, entries in by_id.items():
        d = os.path.join(out, "c", cid)
        os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(cid, entries, meta))

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [SITE_URL] + [f"{SITE_URL}c/{cid}/" for cid in sorted(by_id)]
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.writelines(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        f.write("</urlset>\n")
    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")
    open(os.path.join(out, ".nojekyll"), "w").close()
    print(f"Zbudowano {len(by_id)} stron bohaterów w {out}")


if __name__ == "__main__":
    main()
