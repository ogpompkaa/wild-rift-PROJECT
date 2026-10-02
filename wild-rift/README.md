# Rift Meta

Fanowska strona z aktualną metą **League of Legends: Wild Rift** po polsku.

- **Tier lista**: konsensus z oficjalnych statystyk Tencent (serwer CN) i WildRiftMeta; filtr linii i przedziału rang
  (Wszystkie / Diament+ / Mistrz+ / Pretendent+), win/pick/ban rate, strzałki zmian od poprzedniego patcha.
- **Panel bohatera**: statystyki we wszystkich przedziałach rang, kontry i podstawowy build.
- **Zmiany w patchu**: polski skrót wzmocnień i osłabień.
- **Przedmioty**: jak często przedmiot pojawia się w buildach silnych bohaterów.
- **Rangi**: od Żelaza do Suwerena.

## Pliki

- `index.html`: strona (GitHub Pages oraz Artifact na claude.ai).
- `data/meta.json`: tier lista, statystyki, kontry, buildy. `data/patch.json`: polski skrót patcha.
- `data/prev.json`: tiery z poprzedniego patcha (do strzałek). `data/slow.json`: pamięć kontr i buildów.
- `img/champions/`: ikony bohaterów (64 px WebP).
- `scripts/update_meta.py`: pobiera dane (biblioteka standardowa; Pillow opcjonalnie do ikon).

## Aktualizacja

```sh
python3 wild-rift/scripts/update_meta.py          # codziennie
python3 wild-rift/scripts/update_meta.py --slow   # wymusza odświeżenie kontr i buildów (normalnie co 6 dni)
```

Codziennie rano zaplanowane zadanie Claude uruchamia skrypt, przy nowym patchu pisze polski skrót do `data/patch.json`,
wypycha zmiany (GitHub Actions publikuje stronę na Pages) i aktualizuje bazę wersji na claude.ai.

## Źródła i zasady

Dane z WildRift Alpha, WildRiftFire i Pocket Tactics **nie są używane**: ich regulaminy nie pozwalają na pobieranie
i publikowanie treści. WildRiftMeta dopuszcza niekomercyjne korzystanie bez obciążania serwisu (skrypt robi przerwy
między zapytaniami). Strona jest fanowska i niezwiązana z Riot Games ani Tencent.

## Grafiki

`img/champions` (ikony 128 px), `img/cards` (karty postaci 300×512), `img/splash` (splash arty 960×533) i `img/items`
(ikony przedmiotów 64 px) to oficjalne grafiki Wild Rift z serwerów Tencent, zmniejszone do WebP. Skrypt pobiera tylko
brakujące pliki, więc nowi bohaterowie i przedmioty dochodzą automatycznie. Nazwy przedmiotów tłumaczy słownik Data Dragon
(Riot); przedmioty dostępne tylko w Wild Rift są przypisane ręcznie w `ITEM_ZH_EXTRA` w `update_meta.py`.

## Aplikacja na telefonie (PWA)

`manifest.webmanifest`, `sw.js` i `img/icons/` pozwalają dodać stronę do ekranu głównego (Android: przycisk
„Zainstaluj”, iPhone: Udostępnij → Do ekranu początkowego). Service worker trzyma kopię strony, danych i grafik,
więc ostatnio pobrana meta działa bez internetu. Po zmianach w liście plików podbij `VERSION` w `sw.js`.
