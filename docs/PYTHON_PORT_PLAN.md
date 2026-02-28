# tinyMediaManager Python Port -- Implementation Plan

## Context

tinyMediaManager is currently a Java/Swing desktop app for managing movie and TV show media libraries. It scans directories for video files, scrapes metadata from online sources (TMDB, TVDB, IMDB, Fanart.tv), and writes Kodi-compatible NFO files alongside the media. The goal is a complete rewrite in Python with PySide6, with a clean backend/frontend separation and a simpler "edit and forget" philosophy: **NFO files are the single source of truth, no database.**

### Key Design Decisions
- **No database.** In-memory models during runtime, NFO files on disk are persistence.
- **No stored datasource config.** User provides a directory (CWD or argument) at launch.
- **On startup:** scan the given directory tree, read all NFO files, build in-memory movie list.
- **On edit/scrape:** modify in-memory model, write NFO back to disk immediately.
- **Movies first.** TV shows will be a future phase.
- **NFO format:** Kodi/XBMC XML (the de facto standard; Plex can read it via community plugins).
- **Scrapers:** TMDB, IMDB, Fanart.tv (TVDB deferred to TV show phase).

---

## Project Structure

```
tinymediamanager/
??? pyproject.toml
??? README.md
??? LICENSE
?
??? src/
?   ??? tmm/
?       ??? __init__.py
?       ??? __main__.py              # Entry point: python -m tmm [directory]
?       ??? version.py
?       ?
?       ??? core/                    # BACKEND -- pure Python, zero Qt imports
?       ?   ??? __init__.py
?       ?   ??? constants.py         # Enums: MediaFileType, MediaType, ArtworkType, Certification, etc.
?       ?   ??? settings.py          # Runtime settings (scraper prefs, language, renamer templates)
?       ?   ??? event_bus.py         # Thread-safe publish/subscribe event system
?       ?   ??? task_manager.py      # Thread pool for background work
?       ?   ??? utils.py             # Path helpers, string cleaning, file type detection
?       ?   ?
?       ?   ??? models/
?       ?   ?   ??? __init__.py
?       ?   ?   ??? movie.py         # Movie dataclass (title, year, plot, rating, cast, etc.)
?       ?   ?   ??? movie_set.py     # MovieSet dataclass
?       ?   ?   ??? media_file.py    # MediaFile dataclass (path, size, codec info)
?       ?   ?
?       ?   ??? movie/
?       ?   ?   ??? __init__.py
?       ?   ?   ??? movie_list.py    # In-memory movie collection manager
?       ?   ?   ??? scanner.py       # Directory traversal, video file detection, NFO discovery
?       ?   ?   ??? renamer.py       # Template-based file renaming
?       ?   ?
?       ?   ??? nfo/
?       ?       ??? __init__.py
?       ?       ??? reader.py        # Parse Kodi NFO XML -> Movie model
?       ?       ??? writer.py        # Movie model -> Kodi NFO XML
?       ?
?       ??? scraper/                 # SCRAPER LAYER -- pure Python, zero Qt imports
?       ?   ??? __init__.py
?       ?   ??? interfaces.py        # ABCs: MetadataProvider, ArtworkProvider
?       ?   ??? types.py             # Dataclasses: SearchResult, MediaMetadata, MediaArtwork, CastMember
?       ?   ??? http_client.py       # Shared httpx client with rate limiting
?       ?   ?
?       ?   ??? tmdb/
?       ?   ?   ??? __init__.py
?       ?   ?   ??? provider.py      # TMDB movie search + metadata + artwork + trailers
?       ?   ?
?       ?   ??? imdb/
?       ?   ?   ??? __init__.py
?       ?   ?   ??? provider.py      # IMDB HTML scraping (ratings, Top 250, extra data)
?       ?   ?
?       ?   ??? fanart_tv/
?       ?       ??? __init__.py
?       ?       ??? provider.py      # High-quality artwork from fanart.tv
?       ?
?       ??? api/                     # API LAYER -- bridge, pure Python, zero Qt imports
?       ?   ??? __init__.py
?       ?   ??? movie_api.py         # Facade: scan, scrape, edit, rename, get movie list
?       ?   ??? task_api.py          # Facade: submit tasks, query progress, cancel
?       ?
?       ??? ui/                      # FRONTEND -- PySide6 only
?           ??? __init__.py
?           ??? main_window.py       # QMainWindow: menu bar, vertical tabs, status bar
?           ??? resources.py         # Icon/image loading
?           ?
?           ??? widgets/
?           ?   ??? __init__.py
?           ?   ??? image_label.py   # Artwork display with scaling
?           ?   ??? star_rater.py    # Clickable star rating
?           ?   ??? status_bar.py    # Task progress display
?           ?   ??? search_field.py  # Search/filter text input
?           ?
?           ??? movies/
?           ?   ??? __init__.py
?           ?   ??? movie_panel.py       # Main tab: splitter with table + detail
?           ?   ??? movie_table_model.py # QAbstractTableModel for movie list
?           ?   ??? movie_detail_panel.py# Info, artwork, cast, media files tabs
?           ?
?           ??? dialogs/
?           ?   ??? __init__.py
?           ?   ??? movie_chooser.py     # Scraper search results picker
?           ?   ??? movie_editor.py      # Full metadata editor
?           ?   ??? image_chooser.py     # Artwork browser/downloader
?           ?   ??? settings_dialog.py   # Scraper keys, language, renamer prefs
?           ?   ??? about_dialog.py
?           ?
?           ??? workers/
?               ??? __init__.py
?               ??? event_bridge.py  # Subscribes to EventBus, emits Qt signals
?
??? resources/
?   ??? icons/
?
??? tests/
    ??? conftest.py
    ??? core/
    ?   ??? test_nfo_reader.py
    ?   ??? test_nfo_writer.py
    ?   ??? test_scanner.py
    ?   ??? test_renamer.py
    ??? scraper/
        ??? test_tmdb.py
```

---

## Milestones

### Milestone 1: Foundation + Data Models + NFO Read/Write
**What:** Project skeleton, data models, NFO reader/writer, basic utilities.

**Files:**
- `pyproject.toml` -- deps: `lxml`, `httpx`, `Pillow`, `pymediainfo`, `PySide6`, `pytest`
- `src/tmm/__init__.py`, `__main__.py`, `version.py`
- `src/tmm/core/constants.py` -- port enums from `MediaFileType.java`, `Certification.java`
- `src/tmm/core/utils.py` -- video file extension detection, path normalization
- `src/tmm/core/models/movie.py` -- `@dataclass` with fields from `Movie.java` (title, original_title, year, plot, tagline, rating, votes, runtime, director, writer, watched, certification, genres, tags, cast, artwork_urls, provider_ids, path, media_source, etc.)
- `src/tmm/core/models/movie_set.py` -- `@dataclass`
- `src/tmm/core/models/media_file.py` -- `@dataclass` (path, size, codec, resolution, audio streams, subtitles)
- `src/tmm/core/nfo/reader.py` -- parse Kodi `<movie>` XML into Movie dataclass. Reference: `MovieToXbmcNfoConnector.java`
- `src/tmm/core/nfo/writer.py` -- serialize Movie dataclass to Kodi XML. Handles: title, originaltitle, sorttitle, set, rating, year, votes, outline, plot, tagline, runtime, thumb, fanart, mpaa, certification, id (IMDB), tmdbid, genres, country, credits, director, actor (name + role + thumb), trailer, watched, etc.
- `tests/core/test_nfo_reader.py`, `test_nfo_writer.py`

**Verification:** `pytest tests/core/test_nfo_*.py` -- round-trip: create Movie -> write NFO -> read NFO -> assert equal.

### Milestone 2: Directory Scanner + In-Memory Movie List
**What:** Scan a directory tree for video files and associated NFO/artwork files. Build in-memory movie collection.

**Files:**
- `src/tmm/core/event_bus.py` -- `EventBus` with `subscribe()`, `publish()`, thread-safe
- `src/tmm/core/movie/movie_list.py` -- `MovieList` class: holds `list[Movie]`, add/remove/get methods, publishes events on change
- `src/tmm/core/movie/scanner.py` -- `MovieScanner`: recursive directory walk, detect video files (by extension list from `Utils.java`), find adjacent NFO files, read them with nfo.reader, detect artwork files (poster.jpg, fanart.jpg, etc.), populate Movie objects. Skip hidden dirs, system dirs (RECYCLE.BIN, etc.)
- `src/tmm/core/utils.py` -- add: `is_video_file()`, `is_disc_folder()`, `VIDEO_EXTENSIONS` set
- `tests/core/test_scanner.py` -- create temp dir with sample video+nfo files, verify scan results

**Verification:** CLI test: `python -m tmm /path/to/movies` prints discovered movies with NFO data.

### Milestone 3: Task Manager + Scraper Infrastructure + TMDB
**What:** Background task system, scraper interface, working TMDB provider.

**Files:**
- `src/tmm/core/task_manager.py` -- `TaskManager` with serial main queue + parallel image pool. `TaskHandle` with progress reporting via EventBus.
- `src/tmm/core/settings.py` -- runtime settings: TMDB API key, preferred language, preferred country
- `src/tmm/scraper/interfaces.py` -- `MetadataProvider(ABC)`: `search(options) -> list[SearchResult]`, `get_metadata(options) -> MediaMetadata`; `ArtworkProvider(ABC)`: `get_artwork(options) -> list[MediaArtwork]`
- `src/tmm/scraper/types.py` -- `SearchResult`, `MediaMetadata`, `MediaArtwork`, `CastMember`, `SearchOptions`, `ScrapeOptions` dataclasses
- `src/tmm/scraper/http_client.py` -- shared `httpx.Client` with timeout, retry, rate-limit support
- `src/tmm/scraper/tmdb/provider.py` -- `TmdbProvider(MetadataProvider, ArtworkProvider)`: search movies, get full metadata (credits, releases, images, trailers), get artwork list. Port from `TmdbMetadataProvider.java`.
- `src/tmm/api/movie_api.py` -- `MovieAPI`: `scan_directory(path)`, `search_movie(query, year)`, `scrape_movie(movie, provider_ids)`, `get_movies()`, `get_movie(index)`
- `src/tmm/api/task_api.py` -- `TaskAPI`: `submit(name, fn)`, `cancel(task_id)`, `get_active_tasks()`
- `tests/scraper/test_tmdb.py`

**Verification:** CLI: scan directory, pick unscraped movie, search TMDB, fetch metadata, write NFO.

### Milestone 4: IMDB + Fanart.tv Scrapers
**What:** Additional metadata and artwork sources.

**Files:**
- `src/tmm/scraper/imdb/provider.py` -- `ImdbProvider(MetadataProvider)`: HTML scraping with BeautifulSoup for ratings, Top 250, additional cast info. Port from `ImdbMetadataProvider.java`.
- `src/tmm/scraper/fanart_tv/provider.py` -- `FanartTvProvider(ArtworkProvider)`: clearart, disc art, logos, HD artwork. Port from `FanartTvMetadataProvider.java`.
- Tests for both

**Verification:** `pytest tests/scraper/` -- search IMDB, fetch Fanart.tv artwork.

### Milestone 5: PySide6 UI Shell + Movie Table
**What:** Running desktop window with movie table populated from scanned data. No editing yet.

**Files:**
- `src/tmm/ui/main_window.py` -- `QMainWindow` with: menu bar (File > Open Directory, Quit; Tools > Scrape All; Help > About), vertical tab widget on left, status bar at bottom
- `src/tmm/ui/workers/event_bridge.py` -- `EventBridge(QObject)`: subscribes to EventBus, emits Qt signals for movie_list_changed, task_progress, task_finished
- `src/tmm/ui/movies/movie_panel.py` -- `QSplitter`: left = toolbar + search + QTableView, right = detail panel
- `src/tmm/ui/movies/movie_table_model.py` -- `QAbstractTableModel` backed by MovieAPI.get_movies(). Columns: title, year, rating, watched, certification, path
- `src/tmm/ui/movies/movie_detail_panel.py` -- `QTabWidget`: Info tab (labels for title, year, plot, tagline, director, cast list), Artwork tab (poster + fanart ImageLabels), Media Files tab (file list)
- `src/tmm/ui/widgets/image_label.py` -- `QLabel` subclass: loads image from file path, scales to fit, placeholder when empty
- `src/tmm/ui/widgets/status_bar.py` -- shows active task name + QProgressBar, connected to EventBridge signals
- `src/tmm/ui/widgets/search_field.py` -- `QLineEdit` with clear button, filters table model
- `src/tmm/ui/resources.py` -- icon loading helper

**Verification:** Run `python -m tmm ~/Movies` -- window opens, table shows movies with NFO data, clicking a row shows details and artwork.

### Milestone 6: Scrape + Edit + Chooser Dialogs
**What:** Full movie workflow: scrape with search dialog, edit metadata, download artwork.

**Files:**
- `src/tmm/ui/dialogs/movie_chooser.py` -- `QDialog`: search field + results table + preview panel. User searches TMDB, picks a result, metadata is fetched and applied to movie. NFO written on confirm.
- `src/tmm/ui/dialogs/movie_editor.py` -- `QDialog`: form fields for all metadata (title, year, plot, tagline, rating, genres, cast table with add/remove, etc.). Save writes NFO.
- `src/tmm/ui/dialogs/image_chooser.py` -- `QDialog`: grid of artwork thumbnails from scraper. User picks artwork, it's downloaded to movie directory and NFO updated.
- `src/tmm/ui/widgets/star_rater.py` -- clickable 0-10 star widget for rating
- `src/tmm/ui/dialogs/settings_dialog.py` -- `QDialog`: TMDB API key, preferred language, scraper order, renamer template
- Toolbar actions: Scan, Scrape Selected, Edit, Rename

**Verification:** Full workflow: open directory, see movies, right-click > Scrape, pick from TMDB results, see metadata + artwork update in detail panel. Edit metadata manually, save, verify NFO on disk.

### Milestone 7: Renamer + Movie Sets + Polish
**What:** File renaming, movie set grouping, UI polish.

**Files:**
- `src/tmm/core/movie/renamer.py` -- template-based renaming (e.g., `{title} ({year})/{title} ({year}).{ext}`). Rename video file, NFO, and artwork files together.
- `src/tmm/ui/dialogs/about_dialog.py`
- Movie set support in movie_detail_panel (show set membership)
- Filter panel enhancements: filter by genre, watched, year range, has NFO, unscraped
- Context menus on movie table (scrape, edit, rename, open folder)

**Verification:** Rename a movie, verify files moved correctly and NFO updated with new paths. Filter movies by various criteria.

---

## Key Libraries

| Purpose | Library | Notes |
|---|---|---|
| GUI | `PySide6` | Qt for Python, LGPL |
| XML (NFO) | `lxml` | Fast XML read/write |
| HTTP | `httpx` | Async-capable, modern |
| HTML scraping | `beautifulsoup4` + `lxml` | For IMDB |
| Images | `Pillow` | Thumbnail generation, format conversion |
| Media info | `pymediainfo` | Codec/resolution detection via libmediainfo |
| String similarity | `rapidfuzz` | Fuzzy matching for scraper results |
| Rate limiting | `tenacity` | Retry/backoff for API calls |
| Testing | `pytest`, `pytest-qt` | Unit + UI tests |

## Architecture Rules

1. **`core/` and `scraper/` must never import PySide6.** If it needs Qt, it doesn't belong in backend.
2. **`api/` returns plain Python objects** (dataclasses, dicts, lists). Never Qt types.
3. **UI calls backend only through `api/` layer.** Never imports from `core.movie` or `scraper.tmdb` directly.
4. **Long operations go through `TaskManager`.** UI submits via `TaskAPI`, progress comes back via `EventBridge` Qt signals.
5. **NFO files are truth.** Every edit writes to NFO immediately. No lazy/deferred persistence.
6. **No stored config for datasources.** Directory is provided at launch (argument or file dialog).

## Reference Files (Current Java Codebase)

These files contain the logic to port:
- `src/org/tinymediamanager/core/entities/MediaEntity.java` -- base model fields
- `src/org/tinymediamanager/core/movie/entities/Movie.java` -- movie model
- `src/org/tinymediamanager/core/movie/tasks/MovieUpdateDatasourceTask.java` -- scanner logic, skip-folder lists, video detection
- `src/org/tinymediamanager/core/nfo/MovieToXbmcNfoConnector.java` -- NFO XML format
- `src/org/tinymediamanager/scraper/tmdb/TmdbMetadataProvider.java` -- TMDB API integration
- `src/org/tinymediamanager/scraper/imdb/ImdbMetadataProvider.java` -- IMDB scraping
- `src/org/tinymediamanager/scraper/fanarttv/FanartTvMetadataProvider.java` -- Fanart.tv
- `src/org/tinymediamanager/core/movie/MovieRenamer.java` -- renaming templates
- `src/org/tinymediamanager/core/threading/TmmTaskManager.java` -- threading model
- `src/org/tinymediamanager/ui/MainWindow.java` -- UI layout reference
- `src/org/tinymediamanager/ui/movies/MoviePanel.java` -- movie tab layout
- `src/org/tinymediamanager/core/MediaFileType.java` -- file type enums
