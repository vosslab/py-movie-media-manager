# Changelog

## 2026-02-28

### Fixes and Maintenance
- Fixed batch mode never triggering from row selection in `_scrape_selected()`:
  added fallback to selection model when fewer than 2 checkboxes are toggled,
  so Shift/Cmd-click multi-select now activates batch mode
- Fixed pre-existing `TypeError` in `MoviePanel.save_table_state()` where
  `int(header.sortIndicatorOrder())` failed with PySide6 `SortOrder` enum;
  changed to use `.value` attribute

### Additions and New Features
- Added `get_selected_movies()` method to `MoviePanel` that returns Movie
  objects for all rows selected via the table view's selection model
- Added `tests/test_gui_smoke.py` with 8 smoke tests covering the full
  scan/scrape/rename pipeline (5 API-level, 3 GUI-level with pytest-qt):
  scan detection, metadata scraping with mocked IMDB, file renaming,
  end-to-end pipeline, MainWindow scan, and MovieChooserDialog batch/single mode

## 2026-02-27

### Fixes and Maintenance
- Fixed `AttributeError` crash in `MovieChooserDialog` when selecting search results:
  replaced non-existent `QTableWidget.currentRowChanged` signal with `currentCellChanged`
  and a lambda to extract the row index
- Fixed `TypeError: unhashable type: 'Movie'` in `_on_scrape_done` by using `movie.path`
  as the dict key in `_batch_results` instead of the unhashable `Movie` dataclass instance

### Additions and New Features
- Redesigned `MovieChooserDialog` with a horizontal `QSplitter` split-pane layout: 3-column
  results table (Title, Year, Rating) on the left, poster preview pane with title, year, and
  overview detail labels on the right; dialog widened to 900x550
- Added `set_image_data(data: bytes)` method to `ImageLabel` widget for loading poster images
  from raw bytes downloaded via HTTP
- Added poster download on selection change in movie chooser using `ImageDownloadWorker`;
  cancels in-flight downloads when selection changes to avoid stale images
- Redesigned movie chooser button row: single mode shows Cancel + OK; batch mode shows
  Abort Queue + Back + Cancel + OK with spacer between left and right groups
- Auto-selects first search result after search to immediately populate the preview pane
- Added Ctrl-C signal handling to GUI: `signal.signal(signal.SIGINT, signal.SIG_DFL)` plus
  a 200ms QTimer to allow Python signal processing during the Qt event loop
- Added `curl_cffi` session reuse in IMDB scraper (`self._session`) for connection
  pooling across search and metadata requests; added HTTP 429 rate-limit detection
  in `_fetch_page()` with a specific warning log before raising `ConnectionError`
- Added `_upgrade_poster_url()` to IMDB scraper that strips resize parameters from
  poster URLs using regex `._V1_[^.]+\.jpg` to get full-resolution images; applied
  in both detail and search result parsing
- Added `_extract_cast_roles()` to enrich actor objects with character names from
  `mainColumnData.castV2` in `__NEXT_DATA__`; added `html.unescape()` decoding for
  JSON-LD actor names to match `__NEXT_DATA__` plain-text names
- Added `_extract_producers()` to parse producer credits from `principalCredits`
  in `__NEXT_DATA__` where `category.id == "producer"`; builds `CastMember` objects
  with `department="Production"`
- Added unit tests for poster URL upgrade, actor character roles, poster URL in
  metadata, and producers extraction in `tests/test_scraper_imdb.py`
- Added live test assertions for poster URL (no resize params), actor roles (at
  least one with non-empty role), and producers (lenient) in
  `tests/test_scraper_imdb_live.py::test_get_metadata_clerks`
- Added `_parse_next_data_detail()` and `_extract_next_data_fields()` to IMDB
  scraper for parsing `__NEXT_DATA__` on detail pages; extracts original_title,
  tagline, country, spoken_languages, studio, top250, and keyword tags from
  `aboveTheFoldData` and `mainColumnData` sections
- Added 7 unit tests for __NEXT_DATA__ detail field extraction in
  `tests/test_scraper_imdb.py` (original_title, tagline, country/languages,
  studio, top250, tags, graceful degradation without __NEXT_DATA__)
- Added live test assertions for country, spoken_languages, and tags in
  `tests/test_scraper_imdb_live.py::test_get_metadata_clerks`
- Added parental guide severity level scraping to IMDB scraper; fetches the
  `/title/ttXXXX/parentalguide/` page and parses category severity summaries
  (Sex & Nudity, Violence & Gore, Profanity, Alcohol/Drugs/Smoking,
  Frightening & Intense Scenes) into a `parental_guide` dict field
- Added `parental_guide` dict field to `MediaMetadata` dataclass in
  `moviemanager/scraper/types.py` and `Movie` dataclass in
  `moviemanager/core/models/movie.py`
- Added `_fetch_page_safe()` helper in IMDB scraper for graceful HTTP failure
  handling without try/except blocks
- Added `_parse_parental_guide()` function to parse __NEXT_DATA__ JSON from
  the IMDB parental guide page
- Added unit tests for parental guide parsing and failure degradation in
  `tests/test_scraper_imdb.py`
- Added live test `test_get_metadata_clerks_parental_guide` in
  `tests/test_scraper_imdb_live.py`
- Rewrote `moviemanager/scraper/imdb_scraper.py` to use `curl_cffi` with browser impersonation
  and direct JSON parsing (`__NEXT_DATA__` for search, JSON-LD for movie details), replacing
  the broken cinemagoer library entirely
- Added `search_movie_with_fallback()` to `MovieAPI` with three-strategy fallback: title+year,
  title only, simplified title (removes parenthetical text and leading articles)
- Added `compute_match_confidence()` static method to `MovieAPI` for scoring search result
  matches; batch scrape now skips low-confidence matches (< 0.7) and shows summary
- Added batch navigation to `MovieChooserDialog` with Previous/Skip buttons, position indicator
  in title bar (e.g. "2/4"), and auto-advance on scrape success
- Added "Try broader search" button in movie chooser when initial search returns no results
- Added `-l`/`--open-last` flag to `movie_organizer_gui.py` that silently opens the last used
  directory, bypassing the reopen confirmation popup
- Created `tests/test_scraper_imdb_live.py` with live IMDB tests for Clerks (1994, tt0109445)
  marked with `@pytest.mark.slow`
- Added `[tool.pytest.ini_options]` markers config to `pyproject.toml` for slow test marker

### Behavior or Interface Changes
- IMDB scraper now reuses a single `curl_cffi` session across all requests for better
  connection pooling; HTTP 429 responses produce a specific rate-limit warning log
- IMDB scraper poster URLs are now upgraded to full resolution by stripping resize
  parameters (e.g. `._V1_UY300_.jpg` becomes `._V1_.jpg`)
- IMDB scraper actor objects now include character role names extracted from
  `__NEXT_DATA__` `castV2` data; JSON-LD actor names are HTML-entity-decoded for
  reliable matching
- `MovieAPI.scrape_movie()` now maps `parental_guide` and producer fields from
  `MediaMetadata` onto `Movie` objects
- IMDB scraper no longer depends on cinemagoer; uses `curl_cffi` for HTTP and parses IMDB
  embedded JSON directly, fixing TLS fingerprint blocking and broken HTML parsers
- Batch scrape (GUI and CLI) now uses confidence scoring: only auto-selects results with
  confidence >= 0.7; shows summary dialog with scraped/skipped/no-results counts
- GUI Scrape button now detects multiple checked movies and opens chooser in batch mode
  with Previous/Skip/Next navigation instead of single-movie mode
- CLI `scrape` command now tries fallback search strategies when initial search returns empty
- Movie chooser results table ID column now shows IMDB ID or TMDB ID (whichever is available)
- Replaced `cinemagoer` with `curl_cffi` in `pyproject.toml` dependencies and
  `pip_requirements.txt`
- Created `moviemanager/ui/menu_builder.py` with YAML-driven menu and shortcut construction
  from `moviemanager/ui/menu_config.yaml`; replaces hardcoded menu setup in main_window.py
- Created `moviemanager/ui/theme.py` with dark/light/system palette support and
  `apply_theme()` function
- Added dark mode toggle: View > Dark Mode menu item toggles between dark and system theme,
  persists preference in settings
- Added YAML menu configuration (`menu_config.yaml`) defining all menus, shortcuts, and
  checkable/storable actions
- Added new settings fields: `theme`, `scraper_provider`, `last_directory`,
  `download_trailer`, `download_subtitles`, `subtitle_languages`, `opensubtitles_api_key`
- Added scraper provider selection (IMDB/TMDB) in settings; IMDB is default and needs no key;
  TMDB falls back to IMDB when key is missing
- Added "Get Key" buttons next to TMDB, Fanart.tv, and OpenSubtitles API key fields in settings
  dialog, opening provider sign-up pages in browser
- Added theme combobox (System/Light/Dark) to API Keys settings tab
- Added trailer and subtitle download checkboxes and subtitle language field to Downloads tab
- Renamed "Artwork" tab to "Downloads" in settings dialog; now includes trailer and subtitle
  options alongside artwork checkboxes
- Added toolbar Settings (SP_DialogApplyButton) and Quit (SP_DialogCloseButton) buttons
  pushed to the right with a flexible spacer
- Added last-directory memory: saves `last_directory` on scan, offers to reopen on next launch
  if no CLI directory was provided
- Added `setOrganizationName` and `setOrganizationDomain` calls before QApplication creation
  for proper macOS app identification
- Applied saved theme on application startup via `moviemanager.ui.theme.apply_theme()`
- Added poster URL extraction to IMDB scraper from cinemagoer `full-size cover url` /
  `cover url` fields
- Added `imdb_id` parameter to `MovieAPI.scrape_movie()` for IMDB-based scraping
- Updated batch scrape and movie chooser to pass `imdb_id` when TMDB ID is unavailable
- Added stub methods `_download_trailer()` and `_download_subtitles()` to MainWindow for
  menu wiring
- Added `trailer_url` field to Movie dataclass and `subtitle_urls` field to MediaMetadata
- Added TMDB trailer extraction: `get_metadata()` now requests videos and extracts YouTube trailer URL
- Added `trailer_url` mapping from MediaMetadata to Movie in `scrape_movie()`
- Added `download_trailer()` method to MovieAPI using yt-dlp for trailer downloads
- Created `moviemanager/scraper/subtitle_scraper.py` with SubtitleScraper class for OpenSubtitles
  REST API (search and download by IMDB ID)
- Added `download_subtitles()` method to MovieAPI for downloading subtitles grouped by language
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
