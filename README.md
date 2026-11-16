# soundstages

Does audio-feature signal change across the popularity distribution once artist reach,
genre and era are held fixed? Regression on Spotify's 0–100 popularity score.

Every artist on Every Noise at Once with 100+ monthly listeners, and every track they
released. 2,635,971 tracks from 19,206 artists. Albums, tracks, popularity and audio
features from the ReccoBeats API.

| **Genre** | **Collected** | **MDN. Listeners** | **Tracks** |
| :--- | :---: | :---: | :---: |
| Electronic | 2260 | 77,805.5 | 269,190 |
| Latin | 2179 | 313,512 | 366,410 |
| Hip-Hop | 2057 | 112,018 | 292,756 |
| Pop | 1564 | 402,701.5 | 151,291 |
| Rock | 1226 | 268,095 | 245,126 |
| Jazz | 1124 | 24,686 | 260,405 |
| Folk | 1088 | 47,128 | 163,378 |
| Caribbean | 919 | 40,990 | 120,597 |
| Metal | 860 | 31,450 | 92,891 |
| Blues | 835 | 13,152 | 134,668 |
| Indie | 800 | 300,843 | 67,928 |
| African | 702 | 120,415 | 45,667 |
| Country | 690 | 185,207.5 | 113,166 |
| Punk | 632 | 22,427.5 | 68,995 |
| Ambient | 598 | 4,380 | 71,291 |
| Soul | 578 | 30,550 | 59,295 |
| R&B | 571 | 300,414 | 41,595 |
| Funk | 518 | 48,513 | 46,437 |
| Gospel | 409 | 12,556 | 24,885 |

## Pipeline

| Stage | Script | Output |
|---|---|---|
| Artists from Every Noise at Once | src/collect/artists.py | nominees.parquet |
| Monthly listeners | src/collect/listeners.py | listeners.parquet |
| Primary genre | src/collect/resolve.py | resolved.parquet |
| Dataset merging | src/prepare/merge.py | artists.parquet |
| Spotify ID to ReccoBeats ID | src/collect/ids.py | ids.parquet |
| Album collection | src/collect/albums.py | albums.parquet |
| Album cleaning | src/prepare/clean_albums.py | albums_clean.parquet |
| Track collection | src/collect/tracks.py | tracks.parquet |
| Track cleaning | src/prepare/clean_tracks.py | tracks_clean.parquet |
| Audio features | src/collect/features.py | features.parquet |
| Join, feature checks, flags | src/prepare/build.py | dataset.parquet |

src/collect/ scripts crawl (Every Noise, Spotify artist pages, ReccoBeats). They ran once
and aren't rerun. src/prepare/ scripts rebuild from the crawled files in minutes.
Paths are in config.py. Data isn't committed.

## Reproducing the data

With the collected files in data/inputs/, from the project root:

```
uv sync
uv run python src/prepare/merge.py
uv run python src/prepare/clean_albums.py
uv run python src/prepare/clean_tracks.py
uv run python src/prepare/build.py
```

Saving and checking outputs against a reference copy:

```
uv run python reference.py save
uv run python reference.py check
```

Tests: `uv run pytest`. Lint: `uv run ruff check .`
