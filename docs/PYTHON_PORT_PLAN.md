# tinyMediaManager Python port -- implementation plan

## Context

tinyMediaManager is a Java/Swing desktop app for managing movie and TV show media
libraries. It scans directories for video files, scrapes metadata from online sources
(TMDB, TVDB, IMDB, Fanart.tv), and writes Kodi-compatible NFO files alongside the media.

This project is a complete rewrite in Python with PySide6. The design follows a clean
backend/frontend separation and a simpler "edit and forget" philosophy: **NFO files are
the single source of truth, no database.**

## Design philosophy

- **No database.** In-memory models during runtime; NFO files on disk are persistence.
- **No stored datasource config.** User provides a directory (CWD or argument) at launch.
- **On startup:** scan the given directory tree, read all NFO files, build in-memory
  movie list.
- **On edit/scrape:** modify in-memory model, write NFO back to disk immediately.
- **Movies first.** TV shows will be a future phase.
- **NFO format:** Kodi/XBMC XML (the de facto standard; Plex reads it via plugins).
- **Scrapers:** TMDB, IMDB, Fanart.tv (TVDB deferred to TV show phase).

## Scope

- Movie management only (no TV shows in initial release).
- Desktop GUI via PySide6.
- Kodi-compatible NFO read/write as the persistence layer.
- Scraping from TMDB (primary), IMDB (supplemental), Fanart.tv (artwork).
- Template-based file renaming.
- No database, no web server, no mobile client.

## Architecture boundaries

1. **`core/` and `scraper/` must never import PySide6.** If it needs Qt, it does not
   belong in backend.
2. **`api/` returns plain Python objects** (dataclasses, dicts, lists). Never Qt types.
3. **UI calls backend only through `api/` layer.** Never imports from `core.movie` or
   `scraper.tmdb` directly.
4. **Long operations go through `TaskManager`.** UI submits via `TaskAPI`, progress comes
   back via `EventBridge` Qt signals.
5. **NFO files are truth.** Every edit writes to NFO immediately. No lazy/deferred
   persistence.
6. **No stored config for datasources.** Directory is provided at launch (argument or
   file dialog).

## Project structure

```text
movie-media-manager/
  pyproject.toml
  VERSION
  README.md
  LICENSE
  pip_requirements.txt
  pip_requirements-dev.txt
  source_me.sh

  moviemanager/
    __init__.py

    core/
      __init__.py
      constants.py         # MediaFileType enum, extension sets, skip dirs, stopwords
      settings.py          # YAML-based runtime settings
      utils.py             # parse_title_year(), is_video_file(), clean_filename()
      event_bus.py         # Thread-safe publish/subscribe event system
      task_manager.py      # Thread pool for background work

      models/
        __init__.py
        movie.py           # Movie dataclass
        movie_set.py       # MovieSet dataclass
        media_file.py      # MediaFile dataclass

      movie/
        __init__.py
        movie_list.py      # In-memory movie collection manager
        scanner.py         # Directory traversal, video/NFO detection
        renamer.py         # Template-based file renaming

      nfo/
        __init__.py
        reader.py          # Parse Kodi NFO XML -> Movie model
        writer.py          # Movie model -> Kodi NFO XML

    scraper/
      __init__.py
      interfaces.py        # ABCs: MetadataProvider, ArtworkProvider
      types.py             # SearchResult, MediaMetadata, CastMember DTOs

      tmdb/
        __init__.py
        provider.py        # TMDB search + metadata + artwork

      imdb/
        __init__.py
        provider.py        # IMDB data via cinemagoer

      fanart_tv/
        __init__.py
        provider.py        # High-quality artwork from fanart.tv

    api/
      __init__.py
      movie_api.py         # Facade: scan, scrape, edit, rename, get movie list
      task_api.py          # Facade: submit tasks, query progress, cancel

    ui/
      __init__.py
      main_window.py       # QMainWindow with menu, vertical tabs, status bar
      resources.py         # Icon/image loading

      widgets/
        __init__.py
        image_label.py     # Artwork display with scaling
        star_rater.py      # Clickable star rating
        status_bar.py      # Task progress display
        search_field.py    # Search/filter text input

      movies/
        __init__.py
        movie_panel.py          # Splitter: table + detail
        movie_table_model.py    # QAbstractTableModel for movie list
        movie_detail_panel.py   # Info, artwork, cast, media files tabs

      dialogs/
        __init__.py
        movie_chooser.py        # Scraper search results picker
        movie_editor.py         # Full metadata editor
        image_chooser.py        # Artwork browser/downloader
        settings_dialog.py      # Scraper keys, language, renamer prefs
        about_dialog.py

      workers/
        __init__.py
        event_bridge.py    # Subscribes to EventBus, emits Qt signals

  tests/
    conftest.py
    test_nfo_round_trip.py
    test_filename_parser.py
    test_pyflakes_code_lint.py
    test_ascii_compliance.py
```

## Key libraries

| Purpose | Library | Notes |
| --- | --- | --- |
| GUI | `PySide6` | Qt for Python, LGPL |
| XML (NFO) | `lxml` | Fast XML read/write |
| HTTP | `requests` | Simple HTTP client |
| TMDB API | `tmdbv3api` | TMDB v3 wrapper |
| IMDB data | `cinemagoer` | Formerly IMDbPY |
| Images | `pillow` | Thumbnail generation, format conversion |
| Media info | `pymediainfo` | Codec/resolution detection via libmediainfo |
| Config | `pyyaml` | YAML settings files |
| Console | `rich` | Pretty output and progress bars |
| Tables | `tabulate` | CLI table formatting |
| Testing | `pytest`, `pytest-qt` | Unit + UI tests |

## Milestones

### Milestone 1: foundation + data models + NFO read/write

**What:** Project skeleton, data models, NFO reader/writer, basic utilities.

**Files:**
- `pyproject.toml` -- version 26.02b1, dependencies listed
- `moviemanager/__init__.py`
- `moviemanager/core/constants.py` -- port enums from `MediaFileType.java`; video, audio,
  and subtitle extension sets; skip directories; artwork filenames; stopwords
- `moviemanager/core/utils.py` -- `parse_title_year()`, `is_video_file()`,
  `clean_filename()` ported from Java `ParserUtils`
- `moviemanager/core/settings.py` -- YAML-based configuration
- `moviemanager/core/models/movie.py` -- `@dataclass` with fields from `Movie.java`
- `moviemanager/core/models/movie_set.py` -- `@dataclass`
- `moviemanager/core/models/media_file.py` -- `@dataclass`
- `moviemanager/scraper/types.py` -- `SearchResult`, `MediaMetadata`, `CastMember`
- `moviemanager/scraper/interfaces.py` -- `MetadataProvider`, `ArtworkProvider` ABCs
- `moviemanager/core/nfo/reader.py` -- parse Kodi `<movie>` XML into Movie dataclass
- `moviemanager/core/nfo/writer.py` -- serialize Movie dataclass to Kodi XML
- `tests/test_nfo_round_trip.py`, `tests/test_filename_parser.py`

**Verification:**
```bash
source source_me.sh && python -m pytest tests/test_nfo_round_trip.py
source source_me.sh && python -m pytest tests/test_filename_parser.py
```

Round-trip: create Movie -> write NFO -> read NFO -> assert equal.

### Milestone 2: directory scanner + in-memory movie list

**What:** Scan a directory tree for video files and associated NFO/artwork files. Build
in-memory movie collection.

**Files:**
- `moviemanager/core/event_bus.py` -- `EventBus` with `subscribe()`, `publish()`,
  thread-safe
- `moviemanager/core/movie/movie_list.py` -- `MovieList` class: holds `list[Movie]`,
  add/remove/get methods, publishes events on change
- `moviemanager/core/movie/scanner.py` -- `MovieScanner`: recursive directory walk,
  detect video files by extension, find adjacent NFO files, read them with `nfo.reader`,
  detect artwork files (poster.jpg, fanart.jpg, etc.), populate Movie objects. Skip
  hidden dirs, system dirs (RECYCLE.BIN, etc.)
- `tests/test_scanner.py` -- create temp dir with sample video+NFO files, verify results

**Verification:**
```bash
source source_me.sh && python -m pytest tests/test_scanner.py
```

CLI test: scan a directory and print discovered movies with NFO data.

### Milestone 3: task manager + scraper infrastructure + TMDB

**What:** Background task system, scraper interface, working TMDB provider.

**Files:**
- `moviemanager/core/task_manager.py` -- `TaskManager` with serial main queue + parallel
  image pool. `TaskHandle` with progress reporting via EventBus.
- `moviemanager/scraper/tmdb/provider.py` -- `TmdbProvider(MetadataProvider,
  ArtworkProvider)`: search movies, get full metadata (credits, releases, images,
  trailers), get artwork list. Port from `TmdbMetadataProvider.java`.
- `moviemanager/api/movie_api.py` -- `MovieAPI`: `scan_directory(path)`,
  `search_movie(query, year)`, `scrape_movie(movie, provider_ids)`, `get_movies()`
- `moviemanager/api/task_api.py` -- `TaskAPI`: `submit(name, fn)`, `cancel(task_id)`,
  `get_active_tasks()`
- `tests/test_tmdb_provider.py`

**Verification:**
```bash
source source_me.sh && python -m pytest tests/test_tmdb_provider.py
```

CLI: scan directory, pick unscraped movie, search TMDB, fetch metadata, write NFO.

### Milestone 4: IMDB + Fanart.tv scrapers

**What:** Additional metadata and artwork sources.

**Files:**
- `moviemanager/scraper/imdb/provider.py` -- `ImdbProvider(MetadataProvider)`: uses
  cinemagoer for ratings, Top 250, additional cast info
- `moviemanager/scraper/fanart_tv/provider.py` -- `FanartTvProvider(ArtworkProvider)`:
  clearart, disc art, logos, HD artwork
- Tests for both providers

**Verification:**
```bash
source source_me.sh && python -m pytest tests/test_imdb_provider.py
source source_me.sh && python -m pytest tests/test_fanart_provider.py
```

## Patch plan

Work proceeds in milestone order. Each milestone produces a testable increment.

| Patch | Milestone | Deliverable |
| --- | --- | --- |
| 1 | M1 | Skeleton, models, NFO round-trip |
| 2 | M2 | Scanner, movie list, event bus |
| 3 | M3 | Task manager, TMDB provider, API layer |
| 4 | M4 | IMDB + Fanart.tv scrapers |
| 5 | M5 (future) | PySide6 UI shell + movie table |
| 6 | M6 (future) | Scrape/edit/chooser dialogs |
| 7 | M7 (future) | Renamer, movie sets, polish |

## Parallelism summary

Within Milestone 1, the following can proceed in parallel:

- **Stream A:** `constants.py`, `models/`, `utils.py` (no cross-dependencies)
- **Stream B:** `scraper/types.py`, `scraper/interfaces.py` (depends only on stdlib)
- **Stream C:** `nfo/reader.py`, `nfo/writer.py` (depends on models from Stream A)
- **Stream D:** `settings.py` (independent)

Streams A and B can run fully in parallel. Stream C starts once models land.

## Risk register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `tmdbv3api` lacks needed endpoints | Medium | Fall back to raw `requests` calls |
| `cinemagoer` rate-limited or unstable | Medium | Add `time.sleep(random.random())` |
| `pymediainfo` requires system lib | Low | Document in [docs/INSTALL.md](docs/INSTALL.md) |
| PySide6 packaging on macOS | Medium | Test early in M5, use `pyinstaller` if needed |
| NFO format edge cases | Low | Test against real NFO files from tinyMediaManager |

## Verification strategy

- Every milestone has pytest-based verification before moving on.
- `tests/test_pyflakes_code_lint.py` runs on every change.
- `tests/test_ascii_compliance.py` enforces ASCII-only source files.
- NFO round-trip tests use real-world sample NFO files.
- Scraper tests use mocked HTTP responses for deterministic results.
- UI tests (M5+) use `pytest-qt` fixtures.

## Reference Java files

These files from the tinyMediaManager Java codebase contain the logic to port:

- `MediaEntity.java` -- base model fields
- `Movie.java` -- movie model
- `MediaFileType.java` -- file type enums
- `MovieUpdateDatasourceTask.java` -- scanner logic, skip-folder lists, video detection
- `MovieToXbmcNfoConnector.java` -- NFO XML format
- `TmdbMetadataProvider.java` -- TMDB API integration
- `ImdbMetadataProvider.java` -- IMDB scraping
- `FanartTvMetadataProvider.java` -- Fanart.tv artwork
- `MovieRenamer.java` -- renaming templates
- `TmmTaskManager.java` -- threading model
- `MainWindow.java` -- UI layout reference
- `MoviePanel.java` -- movie tab layout

The Java source is available under `tinyMediaManager/` in the repo root for reference.

## Resolved decisions

| Decision | Resolution |
| --- | --- |
| Package name | `moviemanager` |
| Version scheme | CalVer `26.02b1` |
| Persistence | NFO files only, no database |
| TMDB client | `tmdbv3api` PyPI package |
| IMDB client | `cinemagoer` PyPI package |
| HTTP library | `requests` (not httpx) |
| GUI framework | PySide6 |
| Config format | YAML via `pyyaml` |
| Python version | 3.12 |
| Initial scope | Movies only, TV shows deferred |
