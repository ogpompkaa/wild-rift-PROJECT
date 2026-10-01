# Rift Meta

Fanowska strona z aktualną metą **League of Legends: Wild Rift**:

- **Tier lista bohaterów**: konsensus z kilku serwisów (WildRiftFire, WildRift Alpha), filtr po linii, wyszukiwarka, znacznik, gdy źródła się różnią.
- **Tier lista przedmiotów** (WildRiftFire).
- **Rangi**: od Żelaza do Suwerena, dywizje i znaki.

## Pliki

- `index.html`: strona (działa samodzielnie i jako Artifact na claude.ai).
- `data/meta.json`: ostatnia zapisana kopia danych.
- `scripts/update_meta.py`: pobiera tier listy i zapisuje `data/meta.json` (tylko biblioteka standardowa Pythona).

## Aktualizacja

```sh
python3 wild-rift/scripts/update_meta.py
```

Opublikowana wersja czyta dane z bazy artefaktu (`meta/current`). Zaplanowane zadanie Claude uruchamia skrypt
i wgrywa wynik do tej bazy, więc strona odświeża się sama.
Lokalnie (np. GitHub Pages) strona czyta `data/meta.json`.
