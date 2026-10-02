#!/usr/bin/env python3
"""Składa wersję strony na GitHub Pages: kopiuje aplikację i generuje osobną, statyczną stronę dla każdego bohatera
(c/<id>/index.html) z tytułem, opisem i podglądem linku, plus sitemap.xml i robots.txt.

Użycie:  python3 build_site.py <katalog_wyjściowy>
"""
import html
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
e = html.escape


def pct(v):
    return "—" if v is None else f"{v:.1f}%".replace(".", ",")


def page(cid, entries, meta):
    names = meta.get("names", {})
    name = entries[0]["name"]
    best = max(entries, key=lambda c: TIER_POINTS.get(c["tier"], 0))
    st = best["stats"].get("1") or best["stats"].get("0")
    roles_txt = ", ".join(ROLE_PL[c["role"]] for c in entries)
    k = meta.get("counters", {}).get(cid, {})
    weak = [names.get(x, x) for x in k.get("weak", [])]
    strong = [names.get(x, x) for x in k.get("strong", [])]
    build = meta.get("builds", {}).get(cid, [])
    patch = meta.get("patch") or ""
    title = f"{name} – kontry, build i win rate · Wild Rift {patch} · Rift Meta"
    desc = (f"{name} w Wild Rift (patch {patch}): tier {best['tier']} na linii {ROLE_PL[best['role']]}"
            + (f", win rate {pct(st[0])} w Diament+" if st else "")
            + (f". Kontrują go: {', '.join(weak[:3])}" if weak else "")
            + ". Statystyki, kontry i build po polsku.")
    url = f"{SITE_URL}c/{cid}/"
    img = f"{SITE_URL}img/champions/{cid}.webp"

    role_rows = []
    for c in sorted(entries, key=lambda c: ROLE_ORDER.index(c["role"])):
        s = c["stats"].get("1") or c["stats"].get("0")
        role_rows.append(
            f'<tr><td>{e(ROLE_PL[c["role"]])}</td><td><b class="t" data-tier="{e(c["tier"])}">{e(c["tier"])}</b></td>'
            f'<td>{pct(s[0]) if s else "—"}</td><td>{pct(s[1]) if s else "—"}</td><td>{pct(s[2]) if s else "—"}</td></tr>')

    def champ_list(ids):
        return "".join(
            f'<a class="ch" href="../{e(x)}/"><img src="../../img/champions/{e(x)}.webp" alt="" width="28" height="28">{e(names.get(x, x))}</a>'
            for x in ids) or '<span class="mut">Brak danych.</span>'

    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Rift Meta">
<meta property="og:title" content="{e(name)} – Wild Rift {e(patch)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(img)}"><meta property="og:locale" content="pl_PL">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@600;700&display=swap">
<style>
:root{{color-scheme:dark;--bg:#081226;--bg2:#0b3346;--fg:#eef3f8;--muted:#9fb3c8;--line:rgba(120,220,240,.18);--glass:rgba(255,255,255,.05);--hex:#4fe0f0;--gold:#e8c46a;
--t-splus:#ffd36b;--t-s:#ff9d5c;--t-a:#5fdcaa;--t-b:#6aa8ff;--t-c:#9aa6b8}}
*{{box-sizing:border-box}}
body{{margin:0;padding:0 16px 48px;min-height:100vh;color:var(--fg);font:15px/1.55 Barlow,system-ui,sans-serif;
background:radial-gradient(900px 500px at 80% -10%,rgba(79,224,240,.18),transparent 60%),linear-gradient(170deg,var(--bg),var(--bg2));background-attachment:fixed}}
.w{{max-width:760px;margin:0 auto}}
a{{color:var(--hex)}}
.top{{display:flex;justify-content:space-between;align-items:center;padding:20px 0}}
.brand{{font:700 20px Cinzel,Georgia,serif;color:var(--gold);text-decoration:none}}
.hero{{display:flex;gap:16px;align-items:center;margin:12px 0 20px}}
.hero img{{width:84px;height:84px;border-radius:50%;border:2px solid var(--gold);box-shadow:0 0 24px rgba(79,224,240,.35)}}
h1{{font:700 clamp(28px,6vw,40px)/1.1 Cinzel,Georgia,serif;margin:0}}
.sub{{color:var(--muted);margin:4px 0 0}}
.card{{background:var(--glass);border:1px solid var(--line);border-radius:16px;padding:16px;margin-bottom:12px;backdrop-filter:blur(8px)}}
h2{{font:700 13px/1 "Barlow Condensed",sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}}
table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
th,td{{text-align:right;padding:7px 6px;border-bottom:1px solid var(--line)}}th:first-child,td:first-child{{text-align:left}}
th{{font:600 12px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}}
.t{{display:inline-block;min-width:30px;text-align:center;padding:2px 6px;border-radius:6px;color:#081226;background:var(--tc)}}
[data-tier="S+"]{{--tc:var(--t-splus)}}[data-tier="S"]{{--tc:var(--t-s)}}[data-tier="A"]{{--tc:var(--t-a)}}[data-tier="B"]{{--tc:var(--t-b)}}[data-tier="C"]{{--tc:var(--t-c)}}
.list{{display:flex;flex-wrap:wrap;gap:8px}}
.ch{{display:inline-flex;align-items:center;gap:8px;padding:4px 12px 4px 4px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid var(--line);color:var(--fg);text-decoration:none}}
.ch img{{border-radius:50%}}
.build{{display:flex;flex-wrap:wrap;gap:6px;margin:0;padding:0;list-style:none}}
.build li{{padding:6px 10px;border-radius:10px;background:rgba(255,255,255,.06);border:1px solid var(--line);font-size:14px}}
.cta{{display:inline-block;margin:8px 0 0;padding:12px 18px;border-radius:999px;background:linear-gradient(90deg,var(--hex),#2bb3d6);color:#06202b;font-weight:700;text-decoration:none}}
.mut,footer{{color:var(--muted);font-size:13px}}footer{{margin-top:24px}}
</style></head><body><div class="w">
<div class="top"><a class="brand" href="../../">Rift Meta</a><span class="mut">Patch {e(patch)}</span></div>
<div class="hero"><img src="../../img/champions/{e(cid)}.webp" alt="{e(name)}"><div><h1>{e(name)}</h1><p class="sub">{e(roles_txt)} · Wild Rift, patch {e(patch)}</p></div></div>
<div class="card"><h2>Tier i statystyki (Diament+, serwer CN)</h2>
<table><thead><tr><th>Linia</th><th>Tier</th><th>Win</th><th>Pick</th><th>Ban</th></tr></thead><tbody>{"".join(role_rows)}</tbody></table></div>
<div class="card"><h2>Kontrują go</h2><div class="list">{champ_list(k.get("weak", []))}</div></div>
<div class="card"><h2>Dobrze radzi sobie z</h2><div class="list">{champ_list(k.get("strong", []))}</div></div>
{f'<div class="card"><h2>Podstawowy build</h2><ol class="build">{"".join(f"<li>{e(i)}</li>" for i in build)}</ol></div>' if build else ""}
<a class="cta" href="../../#{e(cid)}">Zobacz w tier liście z wykresem trendu →</a>
<footer>Statystyki: Tencent (serwer CN). Tier lista, kontry i buildy: <a href="https://www.wildriftmeta.com/">WildRiftMeta</a>.
Rift Meta to strona fanowska, niezwiązana z Riot Games ani Tencent.</footer>
</div></body></html>
"""


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_site"))
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    shutil.copy(os.path.join(ROOT, "index.html"), out)
    for d in ("data", "img"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(out, d))
    with open(os.path.join(ROOT, "data", "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)

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
