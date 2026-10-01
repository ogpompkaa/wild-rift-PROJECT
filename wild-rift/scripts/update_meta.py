#!/usr/bin/env python3
"""Pobiera aktualne tier listy Wild Rift z kilku serwisów i łączy je w jeden plik meta.json.

Źródła:
  - WildRiftFire  (https://www.wildriftfire.com/tier-list, /item-list)
  - WildRift Alpha (https://www.wildriftalpha.com/tier-list)

Użycie:  python3 update_meta.py [ścieżka_wyjściowa]   (domyślnie ../data/meta.json)
Tylko biblioteka standardowa. Kończy się błędem, jeśli żadne źródło nie zwróciło bohaterów.
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
TIER_POINTS = {"S+": 5, "S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
ROLE_MAP = {
    "solo": "baron", "baron": "baron", "top": "baron",
    "jungle": "jungle",
    "mid": "mid",
    "duo": "dragon", "adc": "dragon", "dragon": "dragon",
    "support": "support",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def wrf_tiers(page):
    """WildRiftFire: bloki <div class="tier splus|s|a|b|c"> z kafelkami data-role."""
    out = []
    blocks = re.finditer(r'<div class="tier (\w+)">(.*?)(?=<div class="tier |Tier List Explained)', page, re.S)
    for b in blocks:
        tier = {"splus": "S+"}.get(b.group(1), b.group(1).upper())
        tiles = re.finditer(
            r'class="ico-holder" data-role="(\w+)".*?(?:keystone"[^>]*alt="([^"]+)".*?)?<span>([^<]+)</span>',
            b.group(2), re.S)
        for t in tiles:
            role = ROLE_MAP.get(t.group(1).lower())
            if role:
                out.append({"name": html.unescape(t.group(3)).strip(), "role": role,
                            "tier": tier, "keystone": t.group(2)})
    return out


def wra_tiers(page):
    """WildRift Alpha: JSON-LD ItemList z pozycjami "Nazwa · Rola · Tier"."""
    out = []
    for n, r, t in re.findall(r'"name":"([^"]+) · (\w+) · (S\+|S|A|B|C|D)"', page):
        role = ROLE_MAP.get(r.lower())
        if role:
            out.append({"name": html.unescape(n).strip(), "role": role, "tier": t})
    return out


def wrf_items(page):
    out = {}
    for b in re.finditer(r'<div class="tier (\w+)">(.*?)(?=<div class="tier |Tier List Explained|</main)', page, re.S):
        tier = {"splus": "S+"}.get(b.group(1), b.group(1).upper())
        names = [html.unescape(x).strip() for x in re.findall(r"<span>([^<]+)</span>", b.group(2))]
        # ostatni <span> w bloku to opis tieru, nie przedmiot
        names = [n for n in names if len(n) < 40]
        if names:
            out[tier] = names
    return out


def patch_of(page):
    m = re.search(r"Patch (\d+\.\d+[a-z]?)", page)
    return m.group(1) if m else None


def consensus(points):
    avg = sum(points) / len(points)
    for tier, floor in (("S+", 4.6), ("S", 3.6), ("A", 2.6), ("B", 1.6)):
        if avg >= floor:
            return tier, avg
    return "C", avg


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "data", "meta.json")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sources, patches, per_source, items = [], [], {}, {}
    plan = [
        ("wrf", "WildRiftFire", "https://www.wildriftfire.com/tier-list", wrf_tiers),
        ("wra", "WildRift Alpha", "https://www.wildriftalpha.com/tier-list", wra_tiers),
    ]
    for key, name, url, parse in plan:
        try:
            page = fetch(url)
            rows = parse(page)
        except Exception as e:  # jedno źródło może paść – reszta dalej działa
            print(f"[{name}] błąd: {e}", file=sys.stderr)
            continue
        if not rows:
            print(f"[{name}] brak bohaterów – zmienił się układ strony?", file=sys.stderr)
            continue
        p = patch_of(page)
        if p:
            patches.append(p)
        per_source[key] = rows
        sources.append({"id": key, "name": name, "url": url, "patch": p, "count": len(rows)})
        print(f"[{name}] {len(rows)} wpisów, patch {p}", file=sys.stderr)

    try:
        items = wrf_items(fetch("https://www.wildriftfire.com/item-list"))
    except Exception as e:
        print(f"[WildRiftFire items] błąd: {e}", file=sys.stderr)

    if not per_source:
        sys.exit("Żadne źródło nie zwróciło danych – nie nadpisuję meta.json.")

    merged = {}
    for key, rows in per_source.items():
        for r in rows:
            m = merged.setdefault((r["name"], r["role"]), {"name": r["name"], "role": r["role"], "tiers": {}})
            # gdy źródło wymienia bohatera dwa razy w roli, bierz wyższy tier
            prev = m["tiers"].get(key)
            if prev is None or TIER_POINTS[r["tier"]] > TIER_POINTS[prev]:
                m["tiers"][key] = r["tier"]
            if r.get("keystone"):
                m["keystone"] = r["keystone"]

    champions = []
    for m in merged.values():
        pts = [TIER_POINTS[t] for t in m["tiers"].values()]
        tier, avg = consensus(pts)
        m["tier"] = tier
        m["score"] = round(avg, 2)
        m["split"] = (max(pts) - min(pts)) >= 2
        champions.append(m)
    champions.sort(key=lambda c: (-c["score"], -len(c["tiers"]), c["name"]))

    patch = max(patches, key=lambda p: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[a-z]", p)]) if patches else None
    meta = {"patch": patch, "updatedAt": now, "sources": sources, "champions": champions, "items": items}

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"Zapisano {len(champions)} wpisów (patch {patch}) -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
