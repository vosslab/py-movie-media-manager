# Changelog

## 2026-03-03

### Fixes and Maintenance
- Root-caused IMDB `HTTP 202` search failures to AWS WAF challenge responses
  (`x-amzn-waf-action: challenge`) on IMDB HTML endpoints such as `/find/`.
- Changed `ImdbScraper.search()` to query IMDB suggestion JSON endpoint
  (`https://v2.sg.media-imdb.com/suggestion/...`) first, which currently returns
  HTTP 200 under the same environment where `/find/` returns HTTP 202.
- Added fallback to legacy `/find/` HTML parsing only when suggestion results are unavailable.
- Added warning logging for failed IMDB search fetches with the original query text to make
  these degraded searches easier to diagnose from logs.
- Added explicit AWS WAF challenge detection in `_fetch_page()` and `_fetch_page_safe()` for
  IMDB HTTP 202 responses so errors/logs identify challenge blocking directly.
- Changed GUI startup behavior to auto-open `settings.last_directory` when it exists and no
  launch directory is provided, removing the "Reopen last folder?" confirmation dialog.
- Added an IMDB verification popup flow in match dialog scrape errors: when IMDB returns an
  AWS WAF challenge, users can complete the challenge in an embedded browser dialog and retry
  scraping with captured IMDB/AWS WAF cookies applied to the scraper session.
- Added Firefox-based IMDB cookie loading support via browser spec (for example
  `firefox:default-release`) and apply-on-start behavior for the IMDB scraper session.
- Replaced free-form IMDB cookie source with structured GUI settings:
  `Use Browser Cookies for IMDB` (yes/no) and `IMDB Cookie Browser`.
- Removed CLI cookie-spec override `--cookies-from-browser` from
  `movie_organizer_gui.py` to keep cookie configuration in GUI settings.
- Changed IMDB challenge popup to preload configured browser cookies into
  the embedded WebEngine profile before loading IMDB, so challenge retries
  do not start from a fresh cookie session.

### Developer Tests and Notes
- Updated IMDB search unit tests to mock `_fetch_page_safe()` instead of `_fetch_page()`.
- Added `test_search_http_failure_returns_empty` to verify graceful empty-result behavior
  when IMDB search page fetch fails.
- Added suggestion-parser tests for filtering non-title records and prioritizing exact year
  matches in search ordering.
- Added unit tests for HTTP helper behavior on IMDB AWS WAF challenge responses.
- Added GUI smoke test coverage for auto-opening last directory without invoking
  `QMessageBox.question`.
- Added unit tests for IMDB scraper cookie injection and MovieAPI cookie-apply behavior.
- Added browser-cookie utility tests for spec parsing and Firefox cookie DB loading/filtering.
- Added `tests/test_settings.py` coverage for new IMDB browser-cookie settings fields
  and for ignoring removed legacy config keys.

## 2026-02-28

### Additions and New Features
- Redesigned toolbar to reflect the 3-step workflow: Open | 1. Match | 2. Organize |
  3. Download | Settings | Quit. Numbered labels make the workflow order explicit.
- Added "3. Download" toolbar button that opens a new batch download dialog
  (`moviemanager/ui/dialogs/download_dialog.py`) for downloading artwork, trailers, and
  subtitles across multiple movies at once
- Added batch organize (rename) support: checking multiple movies and clicking Organize
  shows a single combined preview dialog with all file moves, instead of one at a time
- Added prefetching in MovieChooserDialog: while reviewing movie N, search results for
  movie N+1 are fetched in the background, along with the poster for the top result.
  Advancing to the next movie now feels instant when the prefetch completes in time.
- Added immediate advance in batch matching: clicking Accept Match now immediately shows
  the next movie while the scrape for the current movie runs in the background
- Added batch progress bar to MovieChooserDialog showing "Movie X of Y" and "N matched"
  counts with a visual progress bar during batch matching
- Added "Download" to the right-click context menu alongside Match, Edit, and Organize
- Added "Download Content" to the Movie menu (consolidates artwork + trailers + subtitles)
- Added `_download_content()` and `_rename_batch()` methods to `MainWindow`

### Behavior or Interface Changes
- Renamed toolbar buttons: "Scrape" -> "1. Match", "Rename" -> "2. Organize"
- Removed "Edit" from toolbar (still accessible via Ctrl+E, double-click, context menu,
  and Movie menu)
- Renamed menu labels: "Scrape Selected" -> "Match Selected", "Rename Selected" ->
  "Organize Selected", "Scrape All Unscraped" -> "Match All Unscraped"
- Renamed MovieChooserDialog buttons: "OK" -> "Accept Match", "Cancel" -> "Skip" in batch
  mode (clarifies that it advances without matching, not that it cancels the operation),
  "Abort Queue" -> "Stop Batch"
- Changed dialog window title from "Scrape - {title}" to "Match - {title}" with improved
  position format "3 of 5" (was "3/5")
- Escape key in batch mode now skips to the next movie (was closing the entire dialog)
- Status bar messages now include workflow hints after each step: "ready to organize
  (Step 2)" after matching, "ready to download content (Step 3)" after organizing
- Context menu items renamed: "Scrape" -> "Match", "Rename" -> "Organize"
- "Scraping..." button text during match changed to "Saving..."

### Fixes and Maintenance
- Updated `test_gui_smoke.py` assertions from "Abort Queue" to "Stop Batch" and added
  progress bar and "Accept Match" button text assertions for both batch and single modes
- Added `download_content` action mapping to `menu_builder.py`
- Fixed "Signal source has been deleted" RuntimeError in `Worker.run()` by guarding signal
  emission against RuntimeError when the receiver is destroyed before the worker finishes
- Added `done()` override to `MovieChooserDialog` to cancel in-flight prefetch and poster
  workers before the dialog is destroyed

### Additions and New Features
- Added 5 parental guide columns (SN, VG, Pr, AD, FI) to the movie table showing
  IMDb content severity for Sex & Nudity, Violence & Gore, Profanity, Alcohol/Drugs/
  Smoking, and Frightening & Intense Scenes with colored circle indicators (green=None,
  yellow=Mild, orange=Moderate, red=Severe, gray=no data)
- Added `SeverityDelegate` in `moviemanager/ui/movies/status_delegate.py` for painting
  color-coded severity circles in parental guide columns
- Added right-click column chooser on the table header: users can show/hide any column
  (except checkbox) via checkmark menu; visibility persists across sessions via QSettings
- Added `visible_columns` field to `Settings` dataclass with all columns visible by default
- Added `PG_COLUMNS` and `SEVERITY_ORDER` mappings to `movie_table_model.py` for parental
  guide column data, tooltips, and sort support

### Behavior or Interface Changes
- Fixed column sizing: Title column now stretches to fill available space while checkbox,
  Year, Rating, status icon (D/N/A/S/T), and parental guide columns resize to contents;
  replaced `setStretchLastSection(True)` with per-column resize modes
- Parental guide columns show full category name in header tooltip on hover
- Column visibility is saved/restored alongside header state and sort order in QSettings

### Additions and New Features
- Redesigned status column with expanded `D N A S T` indicators (Data, NFO, Artwork,
  Subtitles, Trailer) replacing the previous `S N A` (Scraped, NFO, Artwork) set
- Split single status column into 5 separate icon columns matching tinyMediaManager
  layout: each column (D, N, A, S, T) shows a green circle when present or red circle
  when missing via `StatusIconDelegate` in `moviemanager/ui/movies/status_delegate.py`
- Added column header sorting to the movie table: clicking any column header sorts by
  that column (title, year, rating, or individual status flags); sort order persists
  through filter changes
- Added `has_subtitle` property to `Movie` model that scans the movie directory for
  files with subtitle extensions (`.srt`, `.sub`, `.ssa`, `.ass`, `.vtt`, etc.)
- Added `has_trailer` property to `Movie` model that checks for files with "trailer"
  in the name and a video extension in the movie directory
- Status column tooltip now shows individual indicator label with Yes/No
- Added `has_data` property to `Movie` model that returns `True` when meaningful
  metadata exists (scraped via API or loaded from NFO with title plus plot or external
  ID), so movies with NFO files correctly show `D N` instead of `- N`

### Behavior or Interface Changes
- `MovieChooserDialog` batch mode buttons now right-aligned: all buttons (Abort Queue,
  Back, Cancel, OK) grouped on the right side instead of split across both sides
- Status display changed from single combined `D N A S T` letter column to 5 separate
  icon columns with colored circle indicators (green=present, red=missing)
- Checkbox tracking now uses `id(movie)` instead of row indices so check state
  survives column sorting
- Status column `UserRole` data now returns a boolean per column for delegate
  consumption; removed combined flags dict and `ForegroundRole`

### Fixes and Maintenance
- Fixed poster images showing "Invalid image" in `MovieChooserDialog`: added
  browser-like `User-Agent` header to `ImageDownloadWorker` HTTP requests so IMDB
  CDN serves actual image bytes instead of HTML error pages; added content-type
  validation to reject non-image responses before passing to `QPixmap`
- Fixed poster not loading for the first search result in `MovieChooserDialog`:
  `currentCellChanged` signal does not fire when `setCurrentCell(0, 0)` is called
  and the cell index is already (0, 0) from a previous search; added explicit
  `_on_result_selected(0)` call after setting the current cell
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
