# Changelog

## 2026-02-27

### Additions and New Features
- Added `edit` CLI subcommand to modify movie metadata fields (title, year, genre, director,
  rating) and write NFO files from the command line
- Added `artwork` CLI subcommand to batch-download poster.jpg and fanart.jpg for scraped movies
  using `MovieAPI.download_artwork()` method
- Added `list` CLI subcommand with `--filter` title substring and `--unscraped` flags for
  filtered movie listing with rich table output
- Added `download_artwork()` method to `MovieAPI` for downloading poster and fanart images
  based on settings and available URLs
- Added `rich.progress.track()` progress bars to `cmd_scrape()` and `cmd_rename()` batch loops
- Added empty state widget with folder icon, instruction text, and "Open Folder" button when no
  directory is loaded; uses QStackedWidget to swap between empty state and table content
- Added checkbox column (column 0) to the movie table for multi-select; includes
  check_all/uncheck_all/check_unscraped methods and Select All/None/Unscraped in Movie menu
- Added workflow Status column replacing NFO/Scraped columns; shows compact S/N/A indicators
  (Scraped/NFO/Artwork) with color coding (green=all done, orange=partial, gray=none) and tooltips
- Added right-click context menu on movie table with Scrape/Edit/Rename/Show in Finder actions
- Added double-click on movie row to open editor dialog
- Added rename preview dialog (`rename_preview.py`) with 2-column table (Current/New) replacing
  the QMessageBox.question approach
- Added rename undo: Edit > Undo Last Rename (Ctrl+Z) reverses file moves; history clears on
  directory change
- Added batch scrape: Movie > Scrape All Unscraped with QProgressDialog, auto-selects best
  TMDB match per movie, supports cancellation
- Added Cancel button to status bar for cancelling background operations
- Added `has_poster` property to Movie model checking for poster.jpg on disk
- Created `MediaFileTableModel` (QAbstractTableModel) in movie_detail_panel.py replacing
  QTableWidget with QTableView for the Media Files tab (#21)
- Added operation cancellation to Worker and ImageDownloadWorker with `cancel()` method
  and `_cancelled` flag
- Added scan progress reporting via progress_callback parameter in scanner.scan_directory

### Behavior or Interface Changes
- Toolbar now shows text-under-icon layout with 32x32 icons; workflow order is
  Open -> Scrape -> Edit -> Rename; Settings button removed from toolbar (kept in File menu)
- Movie table vertical header (row numbers) hidden; fixed row heights derived from font metrics
- Table selection mode changed from SingleSelection to ExtendedSelection for multi-select
- Settings dialog moved from toolbar-only to File > Settings with Ctrl+, shortcut
- Window title now shows current directory path after scan
- Help text in settings dialog uses palette-aware PlaceholderText color role instead of
  hardcoded gray (#23)
- ImageLabel shows "No artwork" placeholder text when image is missing or path is empty
- Movie chooser overview column now uses tooltip for full text instead of truncating
- Column widths and sort state persist across sessions via QSettings
- Error dialogs now show friendly summary (last traceback line) with expandable detail text

### Additions and New Features (keyboard shortcuts)
- Ctrl+A: Check all movies
- Ctrl+F: Focus search/filter field
- Escape: Clear filter text
- Ctrl+,: Open Settings (macOS convention)
- Ctrl+R: Re-scan current directory
- Return/Enter: Open editor for selected movie
- F1: Open About dialog

### Fixes and Maintenance
- Added dirty state indicator (" *" in title bar) to movie editor dialog, connected to all
  field change signals
- Replaced hardcoded `color: gray; font-size: 11px` stylesheet in settings_dialog.py with
  palette-aware font scaling and PlaceholderText foreground role (#23)

## 2026-02-27

### Additions and New Features
- Created `moviemanager/ui/workers.py` with `Worker` and `ImageDownloadWorker` QRunnable
  classes for running network/IO operations off the main thread
- Added image preview in `ImageChooserDialog` that downloads and displays thumbnails
  asynchronously when a URL is selected
- Added drag-and-drop support on `MainWindow` to accept directory drops for scanning
- Added window geometry and state persistence via `QSettings` (save on close, restore on open)
- Added toolbar icons using `QStyle.standardIcon()` for Open, Scrape, Edit, Rename, Settings
- Added tooltips to all toolbar buttons showing action name and keyboard shortcut
- Added template variable help text below Path Template and File Template fields in Settings
- Added "No results found" feedback label in `MovieChooserDialog` when TMDB returns zero results
- When GUI launches without a directory argument, it now prompts the user to open a folder

### Behavior or Interface Changes
- Moved directory scanning, TMDB search, movie scraping, and artwork downloading to background
  threads using `QThreadPool` and `Worker` classes to prevent UI freezing
- Changed Scrape shortcut from `Ctrl+S` to `Ctrl+Shift+S` to avoid conflict with
  standard Save convention
- Added `F2` keyboard shortcut for Rename action
- Connected `returnPressed` signal on search and year fields in `MovieChooserDialog` so
  pressing Enter triggers a search
- Extended movie table filter to match against year, genres, and director in addition to title
- Changed plot text area height from fixed 120px max to 80-300px range for better readability
- Set interactive column resize mode on movie table so users can manually adjust column widths
- Replaced TMDB ID `QLineEdit` with `QSpinBox` in movie editor to prevent non-numeric input
- Enhanced About dialog to show version from `pyproject.toml`, author, and license info

### Fixes and Maintenance
- Fixed `_rename_selected()` silently returning when no movie is selected; now shows
  "Please select a movie first" message like Scrape and Edit do
- Added error handling (`QMessageBox.critical`) around all network/API calls at the UI boundary
  to prevent unhandled exceptions from crashing the app
- Added unsaved-changes guard on movie editor Cancel: compares current field values to
  original snapshot and shows "Discard changes?" confirmation when dirty
- Added overwrite confirmation dialog before downloading artwork that would replace
  an existing file
- Added transient status bar messages ("Scan complete", "Scrape complete", "Rename complete",
  "Metadata saved") with 3-second timeout after successful operations
- Moved `time.sleep(random.random())` rate limiting from main thread into background
  download worker to prevent UI freezing

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
