# Changelog

## 2026-02-28

### Additions and New Features
- Created PySide6 GUI application with `movie_organizer_gui.py` entry point and `launch_gui.sh`
- Created `moviemanager/ui/main_window.py` with menu bar, toolbar, and action wiring
- Created `moviemanager/ui/movies/movie_panel.py` with QSplitter table + detail layout
- Created `moviemanager/ui/movies/movie_table_model.py` QAbstractTableModel with filtering
- Created `moviemanager/ui/movies/movie_detail_panel.py` with Info, Artwork, Media Files tabs
- Created `moviemanager/ui/widgets/` with `image_label.py`, `search_field.py`, `status_bar.py`
- Created `moviemanager/ui/dialogs/movie_chooser.py` for TMDB search result picking
- Created `moviemanager/ui/dialogs/movie_editor.py` for full metadata editing with NFO write
- Created `moviemanager/ui/dialogs/image_chooser.py` for artwork browsing and downloading
- Created `moviemanager/ui/dialogs/settings_dialog.py` for API keys, language, renamer prefs
- Created `moviemanager/scraper/imdb_scraper.py` wrapping `cinemagoer` for IMDB ratings,
  votes, Top 250, cast, and certifications
- Created `moviemanager/scraper/fanart_scraper.py` using `requests` for Fanart.tv HD artwork
- Created `tests/test_no_pyside6_in_core.py` import guard (24 tests) verifying core/scraper/api
  never import PySide6
- Added `tests/test_scraper_imdb.py` (6 tests) and `tests/test_scraper_fanart.py` (4 tests)
- Wired CLI end-to-end: `scan`, `scrape`, `rename`, and `info` subcommands fully functional
- `movie_api.py`: `search_movie()` calls `TmdbScraper.search()`, `scrape_movie()` fetches
  metadata and writes Kodi NFO, `rename_movie()` delegates to `renamer.rename_movie()`
- `cmd_scrape`: interactive or batch TMDB search with result table and NFO writing
- `cmd_rename`: preview table with dry-run default, confirmation prompt, and file move execution
- `cmd_info`: now shows poster and fanart artwork counts
- Created `tests/test_cli_integration.py` with scan, info, rename dry-run, and empty-dir tests
- Created `moviemanager/core/movie/scanner.py` with `scan_directory()` and `detect_artwork_files()`
- Created `moviemanager/core/movie/renamer.py` with `expand_template()` and `rename_movie()`
- Created `moviemanager/scraper/tmdb_scraper.py` wrapping `tmdbv3api` for TMDB search,
  metadata, and artwork retrieval
- Created `moviemanager/api/movie_api.py` facade and `moviemanager/api/task_api.py` for
  background task management
- Created `moviemanager/core/movie/movie_list.py` in-memory movie collection
- Created `movie_organizer.py` CLI entry point with scan, info, scrape, rename subcommands
- Added `tests/test_scanner.py` (8), `tests/test_renamer.py` (7), `tests/test_scraper_tmdb.py` (7),
  `tests/test_cli.py` (5)
- Updated `tests/conftest.py` to use `git_file_utils.get_repo_root()`

### Fixes and Maintenance
- Removed unnecessary shebangs from library and test modules
- Fixed `conftest.py` to use `git_file_utils.get_repo_root()` instead of path derivation
- Fixed `imdb` import alias in `test_import_requirements.py` to map to `cinemagoer`
- Fixed mixed indentation and unused imports in `test_cli_integration.py` and `test_scanner.py`

### Behavior or Interface Changes
- `cmd_scrape` and `cmd_rename` are no longer placeholder stubs
- `scrape_movie()` converts `CastMember` dataclasses to dicts for NFO writer compatibility

### Decisions and Failures
- CLI uses argparse subcommands (scan, info, scrape, rename) per repo style
- Used `requests` directly for Fanart.tv instead of vendoring `python3-fanart`
- PySide6 is a required dependency, not optional
- Backend/frontend separation enforced by `test_no_pyside6_in_core.py` import guard

## 2026-02-27

### Additions and New Features
- Created project skeleton with `pyproject.toml` (version 26.02b1) and `VERSION` file
- Added `moviemanager/` package with core, scraper, api, ui subpackages
- Created `moviemanager/core/constants.py` with `MediaFileType` enum, video/audio/subtitle
  extension sets, skip directories, artwork filenames, and filename parser stopwords
- Created `moviemanager/core/models/` with `Movie`, `MovieSet`, and `MediaFile` dataclasses
  ported from Java reference
- Created `moviemanager/scraper/types.py` with `SearchResult`, `MediaMetadata`, `CastMember` DTOs
- Created `moviemanager/scraper/interfaces.py` with `MetadataProvider` and `ArtworkProvider` ABCs
- Created `moviemanager/core/utils.py` with `parse_title_year()`, `is_video_file()`,
  `clean_filename()` ported from Java `ParserUtils`
- Created `moviemanager/core/nfo/reader.py` and `writer.py` for Kodi-format NFO XML read/write
- Created `moviemanager/core/settings.py` for YAML configuration
- Added `pip_requirements.txt` with runtime dependencies: cinemagoer, lxml, pillow, pymediainfo,
  PySide6, pyyaml, requests, rich, tabulate, tmdbv3api
- Added `pytest-qt` to `pip_requirements-dev.txt`
- Added `tests/test_nfo_round_trip.py` and `tests/test_filename_parser.py`

### Decisions and Failures
- Chose CalVer `26.02b1` as initial version
- NFO files are single source of truth, no database
- Using PyPI packages (`tmdbv3api`, `cinemagoer`) instead of custom scrapers
- Backend (core/, scraper/) never imports PySide6
