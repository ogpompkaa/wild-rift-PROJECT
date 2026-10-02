#!/usr/bin/env python3
"""Buduje dane strony Rift Meta (wild-rift/data/*.json) i ikony bohaterów (wild-rift/img/champions/).

Źródła (tylko takie, które pozwalają na takie użycie):
  - Tencent, oficjalny feed rankingowy Wild Rift z serwera CN (mlol.qt.qq.com):
    win/pick/ban rate i ocena siły T0–T5 dla każdej linii i przedziału rang.
  - WildRiftMeta (wildriftmeta.com): tier listy per linia, kontry i buildy.
    Regulamin dopuszcza niekomercyjne korzystanie bez obciążania serwisu, z podaniem źródła.
  - Riot (wildrift.leagueoflegends.com): numer aktualnego patcha.

Użycie:
  python3 update_meta.py            # dane dzienne; kontry i buildy, gdy są starsze niż 6 dni lub zmienił się patch
  python3 update_meta.py --slow     # wymuś odświeżenie kontr i buildów
Tylko biblioteka standardowa; Pillow (opcjonalnie) zmniejsza ikony do 64 px WebP.
"""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "img", "champions")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 RiftMetaBot (+github.com/ogpompkaa/All)"
POLITE = 0.8  # s przerwy między zapytaniami do WildRiftMeta

TIER_POINTS = {"S+": 5, "S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
CN_LANE = {"1": "mid", "2": "baron", "3": "dragon", "4": "support", "5": "jungle"}  # sprawdzone na danych
CN_BUCKETS = ["0", "1", "2", "3"]  # wszystkie rangi, Diament+, Mistrz+, Pretendent+
CN_LEVEL_TIER = {"0": "S+", "1": "S", "2": "A", "3": "B", "4": "C", "5": "C"}
WRM_PAGES = {"top": "baron", "jungle": "jungle", "mid": "mid", "adc": "dragon", "support": "support"}
WRM_LABEL = {"baron": "Baron", "jungle": "Jungle", "mid": "Mid", "dragon": "Dragon", "support": "Support"}
DEFAULT_BUCKET = "1"


def log(*a):
    print(*a, file=sys.stderr)


def fetch(url, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
                return body if binary else body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            err = e
        except Exception as e:  # sieć, timeout
            err = e
        time.sleep(2 ** i)
    raise err


def exists(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def text_of(page):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    t = re.sub(r"<[^>]+>", "|", t)
    return html.unescape(re.sub(r"\s*\|[\s|]*", "|", t))


def norm(name):
    return re.sub(r"[^a-z]", "", name.lower().replace("&", "").replace("willump", ""))


def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ── bohaterowie: identyfikatory, nazwy, ikony ──────────────────────────────

def champion_index():
    """id Tencent -> {id, name, avatar}. Nazwy angielskie z Data Dragon (Riot)."""
    heroes = json.loads(fetch("https://game.gtimg.cn/images/lgamem/act/lrlib/js/heroList/hero_list.js"))["heroList"]
    ver = json.loads(fetch("https://ddragon.leagueoflegends.com/api/versions.json"))[0]
    dd = json.loads(fetch(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json"))["data"]
    dd_names = {k.lower(): v["name"] for k, v in dd.items()}
    out = {}
    for hid, h in heroes.items():
        m = re.search(r"Posters/(.+?)_\d+\.jpg", h.get("poster", ""))
        key = m.group(1) if m else h.get("alias", hid)
        cid = key.lower()
        out[hid] = {"id": cid, "name": dd_names.get(cid, key), "avatar": h.get("avatar"),
                    "card": h.get("card"), "poster": h.get("poster")}
    return out


ART = {
    # rodzaj: (folder, pole w hero_list, rozmiar docelowy, jakość WebP)
    "icon": ("champions", "avatar", (128, 128), 84),
    "card": ("cards", "card", (300, 512), 76),
    "splash": ("splash", "poster", (960, 533), 70),
}


def save_webp(raw, path, size, quality):
    try:
        from PIL import Image
    except ImportError:  # bez Pillow zapisujemy oryginał (większy plik, ta sama nazwa)
        with open(path, "wb") as f:
            f.write(raw)
        return
    import io
    im = Image.open(io.BytesIO(raw))
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    im.save(path, "WEBP", quality=quality, method=6)


def needs(path, size):
    """Plik brakuje albo ma inny rozmiar niż docelowy (np. stare ikony 64 px)."""
    if not os.path.exists(path):
        return True
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size != size
    except Exception:
        return False


def ensure_art(index):
    """Oficjalne grafiki Wild Rift z Tencent: ikony 128 px, karty postaci 300×512, splash arty 960×533."""
    for kind, (folder, field, size, q) in ART.items():
        d = os.path.join(ROOT, "img", folder)
        os.makedirs(d, exist_ok=True)
        added = 0
        for c in index.values():
            path = os.path.join(d, c["id"] + ".webp")
            if not c.get(field) or not needs(path, size):
                continue
            try:
                save_webp(fetch(c[field], binary=True), path, size, q)
                added += 1
            except Exception as e:
                log(f"[{kind}] {c['name']}: {e}")
        log(f"[{kind}] nowe: {added}")


# Przedmioty: nazwy po chińsku z feedu Tencent -> angielskie nazwy z Wild Rift.
# Większość tłumaczy słownik Data Dragon (Riot, zh_CN -> en_US); przedmioty tylko z Wild Rift są tu ręcznie.
ITEM_ZH_EXTRA = {
    "兰德里的苦痛面具": "Liandry's Torment", "灭世者之帽": "Rabadon's Deathcap", "和音之律": "Harmonic Echo",
    "无限法球": "Infinity Orb", "峡谷制造者": "Riftmaker", "海灵之戟": "Oceanid's Trident",
    "幽梦之魂": "Youmuu's Ghostblade", "纳沃利迅刃": "Navori Quickblades", "冬之降临": "Winter's Approach",
    "芬布尔之冬": "Fimbulwinter", "炽阳法袍": "Dawnshroud", "永生花的双生守护": "Amaranth's Twinguard",
    "午时斗篷": "Mantle of the Twelfth Hour", "约德尔诱捕装置": "Yordle Trap", "贪婪之靴": "Gluttonous Greaves",
    "法力之靴": "Boots of Mana", "爆发之靴": "Boots of Dynamism", "不朽战靴": "Immortal Boots",
    "碎甲者之靴": "Armorcrusher Boots",
}
ITEM_ALIAS = {"dominiksregards": "lorddominiksregards"}


def item_key(name):
    k = re.sub(r"[^a-z]", "", re.sub(r"^the\s+", "", (name or "").lower()))
    return ITEM_ALIAS.get(k, k)


def ensure_item_icons(names):
    """Ikony przedmiotów (64 px) dla podanych angielskich nazw; zwraca {nazwa: plik}."""
    out = {}
    try:
        equip = json.loads(fetch("https://game.gtimg.cn/images/lgamem/act/lrlib/js/equip/equip.js"))["equipList"]
        ver = json.loads(fetch("https://ddragon.leagueoflegends.com/api/versions.json"))[0]
        zh = json.loads(fetch(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/zh_CN/item.json"))["data"]
        en = json.loads(fetch(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/item.json"))["data"]
    except Exception as e:
        log(f"[przedmioty] brak danych: {e}")
        return out
    z2e = {v["name"].strip(): en[k]["name"] for k, v in zh.items() if k in en}
    z2e.update(ITEM_ZH_EXTRA)
    by_key = {}
    for e in equip:
        eng = z2e.get(e["name"].strip())
        if eng and e.get("iconPath"):
            by_key.setdefault(item_key(eng), e)
    d = os.path.join(ROOT, "img", "items")
    os.makedirs(d, exist_ok=True)
    for n in names:
        e = by_key.get(item_key(n))
        if not e:
            continue
        fname = e["equipId"] + ".webp"
        path = os.path.join(d, fname)
        if needs(path, (64, 64)):
            try:
                save_webp(fetch(e["iconPath"], binary=True), path, (64, 64), 84)
            except Exception as ex:
                log(f"[przedmioty] {n}: {ex}")
                continue
        out[n] = fname
    log(f"[przedmioty] ikony: {len(out)}/{len(set(names))}")
    return out


# ── Tencent (CN) ───────────────────────────────────────────────────────────

def cn_stats(index):
    data = json.loads(fetch("https://mlol.qt.qq.com/go/lgame_battle_info/hero_rank_list_v2"))["data"]
    rows, stat_date = {}, None
    for b in CN_BUCKETS:
        for pos, lst in (data.get(b) or {}).items():
            role = CN_LANE.get(pos)
            if not role:
                continue
            for x in lst:
                c = index.get(x["hero_id"])
                if not c:
                    continue
                stat_date = stat_date or x.get("dtstatdate")
                r = rows.setdefault((c["id"], role), {"id": c["id"], "name": c["name"], "role": role, "stats": {}})
                r["stats"][b] = [round(float(x["win_rate"]) * 100, 1), round(float(x["appear_rate"]) * 100, 1),
                                 round(float(x["forbid_rate"]) * 100, 1), CN_LEVEL_TIER.get(x.get("strength_level"), "C")]
    return rows, stat_date


# ── WildRiftMeta ───────────────────────────────────────────────────────────

def wrm_tiers(name_to_id):
    out, updated = {}, None
    for page, role in WRM_PAGES.items():
        t = text_of(fetch(f"https://www.wildriftmeta.com/tierlist/{page}/"))
        updated = updated or (re.search(r"Updated (\d{4}-\d\d-\d\d)", t) or [None, None])[1]
        label = WRM_LABEL[role]
        for m in re.finditer(r"\|#\d+\|([^|]+)\|[^|]+\|((?:[A-Za-z]+ (?:S\+|S|A|B|C|D)\|)+)", t):
            tiers = dict(re.findall(r"([A-Za-z]+) (S\+|S|A|B|C|D)\|", m.group(2)))
            cid = name_to_id.get(norm(m.group(1)))
            if cid and label in tiers:
                out[(cid, role)] = tiers[label]
        time.sleep(POLITE)
    log(f"[WildRiftMeta] tiery: {len(out)}, aktualizacja {updated}")
    return out, updated


def wrm_slugs():
    page = fetch("https://www.wildriftmeta.com/counters/")
    # każda karta: <article …><a class="counter-directory-head" href="/champions/<slug>/countered-by/">…<strong>Nazwa</strong>
    return {norm(html.unescape(n)): s for s, n in re.findall(
        r'<a class="counter-directory-head" href="/champions/([a-z0-9-]+)/countered-by/">(?:(?!</a>).)*?<strong>([^<]+)</strong>',
        page, re.S)}


def wrm_list(t, start, stop):
    i = t.find(start)
    if i < 0:
        return []
    j = t.find(stop, i + len(start))
    seg = t[i:j if j > 0 else i + 4000]
    return [n for n in re.findall(r"\|#\d+\|([^|]+)\|", seg)]


def wrm_slow(name_to_id, ids):
    """Kontry (kto kontruje / kogo kontruje) i pierwszy build każdego bohatera."""
    slugs = wrm_slugs()
    counters, builds = {}, {}
    for cid, name in ids.items():
        slug = slugs.get(norm(name))
        if not slug:
            continue
        try:
            weak = wrm_list(text_of(fetch(f"https://www.wildriftmeta.com/champions/{slug}/countered-by/")),
                            "|Threats|", "|Countered By|Who Counters")
            time.sleep(POLITE)
            strong = wrm_list(text_of(fetch(f"https://www.wildriftmeta.com/champions/{slug}/counters/")),
                              "|Champions ", "|Counters|Who ")
            time.sleep(POLITE)
            main = text_of(fetch(f"https://www.wildriftmeta.com/champions/{slug}/"))
            time.sleep(POLITE)
        except Exception as e:
            log(f"[WildRiftMeta] {name}: {e}")
            continue
        to_ids = lambda names: [i for i in (name_to_id.get(norm(n)) for n in names) if i and i != cid][:5]
        counters[cid] = {"weak": to_ids(weak), "strong": to_ids(strong)}
        i = main.find("Final items in order|")
        if i >= 0:
            seg = main[i:i + 6000]
            builds[cid] = [n for _, n in re.findall(r"\|(\d)\|([^|]+)\|\+", seg)][:6]
    log(f"[WildRiftMeta] kontry: {len(counters)}, buildy: {len(builds)}")
    return counters, builds


# ── patch ──────────────────────────────────────────────────────────────────

def pkey(p):
    m = re.match(r"(\d+)\.(\d+)([a-z]?)", p or "")
    return (int(m.group(1)), int(m.group(2)), m.group(3)) if m else (0, 0, "")


def official_url(p):
    base = "https://wildrift.leagueoflegends.com/en-us/news/game-updates/"
    major, minor, letter = pkey(p)
    for slug in (f"wild-rift-patch-notes-{major}-{minor}{letter}", f"wild-rift-patch-notes-{major}{minor}{letter}"):
        if exists(base + slug + "/"):
            return base + slug + "/"
    return None


def current_patch(known):
    cands = [known] if known else []
    try:
        t = text_of(fetch("https://www.wildriftmeta.com/patch-notes/"))
        cands += re.findall(r"[Pp]atch (\d+\.\d+[a-z]?)", t)
    except Exception as e:
        log(f"[patch] WildRiftMeta: {e}")
    best = max(cands, key=pkey) if cands else None
    if not best:
        return None, None
    url = official_url(best)
    # sprawdź na stronie Riot, czy nie wyszło już coś nowszego (7.3 -> 7.3a, 7.3b … lub 7.4)
    major, minor, letter = pkey(best)
    nxt = [f"{major}.{minor}{chr(c)}" for c in range(ord(letter or "`") + 1, ord("h"))] + [f"{major}.{minor + 1}"]
    for p in nxt:
        u = official_url(p)
        if not u:
            if p[-1].isalpha():
                continue
            break
        best, url = p, u
    return best, url


# ── składanie ──────────────────────────────────────────────────────────────

def consensus(tiers):
    pts = [TIER_POINTS[t] for t in tiers if t] or [TIER_POINTS["C"]]
    avg = sum(pts) / len(pts)
    for tier, floor in (("S+", 4.6), ("S", 3.6), ("A", 2.6), ("B", 1.6)):
        if avg >= floor:
            return tier, avg
    return "C", avg


def main():
    force_slow = "--slow" in sys.argv
    now = datetime.now(timezone.utc)
    old = load("meta.json", {})
    prev = load("prev.json", {"patch": None, "tiers": {}})

    index = champion_index()
    ensure_art(index)
    name_to_id = {norm(c["name"]): c["id"] for c in index.values()}
    name_to_id.update({norm(c["id"]): c["id"] for c in index.values()})

    rows, stat_date = cn_stats(index)
    if len(rows) < 100:
        sys.exit(f"Feed Tencent zwrócił tylko {len(rows)} wpisów – nie nadpisuję danych.")
    log(f"[Tencent] {len(rows)} wpisów, dane z {stat_date}")

    try:
        wrm, wrm_updated = wrm_tiers(name_to_id)
    except Exception as e:
        log(f"[WildRiftMeta] tiery niedostępne: {e}")
        wrm, wrm_updated = {}, None

    patch, patch_url = current_patch(old.get("patch"))
    log(f"[patch] {patch} {patch_url}")

    # zmiana patcha: zapamiętaj tiery z poprzedniego patcha, żeby pokazać strzałki
    if old.get("patch") and patch and pkey(patch) > pkey(old["patch"]) and old.get("champions"):
        prev = {"patch": old["patch"], "tiers": {f'{c["id"]}|{c["role"]}': c["tier"] for c in old["champions"]}}
        save("prev.json", prev)
        log(f"[patch] nowy patch – zapisano tiery z {old['patch']}")

    champions = []
    for (cid, role), r in rows.items():
        cn_default = next((r["stats"][b] for b in (DEFAULT_BUCKET, "0", "2", "3") if b in r["stats"]), None)
        tiers = {"cn": cn_default[3] if cn_default else None}
        if (cid, role) in wrm:
            tiers["wrm"] = wrm[(cid, role)]
        tier, score = consensus(tiers.values())
        pts = [TIER_POINTS[t] for t in tiers.values() if t]
        c = {"id": cid, "name": r["name"], "role": role, "tier": tier, "score": round(score, 2),
             "tiers": {k: v for k, v in tiers.items() if v}, "stats": r["stats"], "split": max(pts) - min(pts) >= 2}
        pt = prev["tiers"].get(f"{cid}|{role}")
        if pt:
            c["prev"] = pt
        champions.append(c)
    # bohaterowie, których WildRiftMeta ocenia, a Tencent nie pokazuje na tej linii
    have = {(c["id"], c["role"]) for c in champions}
    names = {c["id"]: c["name"] for c in index.values()}
    for (cid, role), t in wrm.items():
        if (cid, role) not in have:
            champions.append({"id": cid, "name": names.get(cid, cid), "role": role, "tier": t,
                              "score": TIER_POINTS[t], "tiers": {"wrm": t}, "stats": {}, "split": False,
                              **({"prev": prev["tiers"][f"{cid}|{role}"]} if f"{cid}|{role}" in prev["tiers"] else {})})
    champions.sort(key=lambda c: (-c["score"], -(c["stats"].get(DEFAULT_BUCKET) or [0])[0], c["name"]))

    # kontry i buildy – raz w tygodniu albo po zmianie patcha
    slow = load("slow.json", {})
    slow_age = now - datetime.fromisoformat(slow["updatedAt"].replace("Z", "+00:00")) if slow.get("updatedAt") else None
    if force_slow or slow_age is None or slow_age > timedelta(days=6) or slow.get("patch") != patch:
        ids = {c["id"]: c["name"] for c in champions}
        counters, builds = wrm_slow(name_to_id, ids)
        if len(counters) > 50:
            slow = {"updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "patch": patch,
                    "counters": counters, "builds": builds}
            save("slow.json", slow)
        else:
            log("[WildRiftMeta] za mało kontr – zostawiam poprzednie")

    # przedmioty: jak często pojawiają się w buildach bohaterów z tierów S+/S/A
    strong_ids = {c["id"] for c in champions if c["tier"] in ("S+", "S", "A")}
    cnt, who = Counter(), {}
    for cid, items in (slow.get("builds") or {}).items():
        if cid in strong_ids:
            for it in items:
                cnt[it] += 1
                who.setdefault(it, []).append(cid)
    items = [{"name": n, "count": k, "champs": who[n][:8]} for n, k in cnt.most_common(30)]
    all_item_names = sorted({i for b in (slow.get("builds") or {}).values() for i in b})
    item_icons = ensure_item_icons(all_item_names)

    meta = {
        "patch": patch, "patchUrl": patch_url, "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "statDate": stat_date, "prevPatch": prev.get("patch"), "defaultBucket": DEFAULT_BUCKET,
        "sources": [
            {"id": "cn", "name": "Tencent (serwer CN)", "url": "https://lolm.qq.com/", "date": stat_date},
            {"id": "wrm", "name": "WildRiftMeta", "url": "https://www.wildriftmeta.com/tierlist/", "date": wrm_updated},
        ],
        "champions": champions,
        "items": items,
        "itemIcons": item_icons,
        "names": {c["id"]: c["name"] for c in index.values()},
        "counters": slow.get("counters", {}),
        "builds": slow.get("builds", {}),
        "countersUpdatedAt": slow.get("updatedAt"),
    }
    save("meta.json", meta)
    save("history.json", update_history(champions, stat_date))
    log(f"Zapisano {len(champions)} wpisów, patch {patch}, przedmioty {len(items)}, kontry {len(meta['counters'])}")


HISTORY_DAYS = 90


def update_history(champions, stat_date):
    """Dzienna historia statystyk (Diament+): {"dates": [...], "series": {"id|rola": [[wr, pr, br] | null, ...]}}.
    Jeden punkt na dzień danych Tencent; ponowne uruchomienie tego samego dnia nadpisuje ostatni punkt."""
    hist = load("history.json", {"dates": [], "series": {}})
    dates, series = hist["dates"], hist["series"]
    if not stat_date:
        return hist
    if dates and dates[-1] == stat_date:
        idx = len(dates) - 1
    else:
        dates.append(stat_date)
        idx = len(dates) - 1
        for s in series.values():
            s.append(None)
    for c in champions:
        st = c["stats"].get(DEFAULT_BUCKET)
        if not st:
            continue
        s = series.setdefault(f'{c["id"]}|{c["role"]}', [None] * len(dates))
        s += [None] * (len(dates) - len(s))
        s[idx] = st[:3]
    if len(dates) > HISTORY_DAYS:
        cut = len(dates) - HISTORY_DAYS
        hist["dates"] = dates[cut:]
        hist["series"] = {k: v[cut:] for k, v in series.items() if any(v[cut:])}
    return hist


if __name__ == "__main__":
    main()
