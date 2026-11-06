## 2026-03-03

### Additions and New Features

- Created [docs/OPENSUBTITLES_COM_API.md](OPENSUBTITLES_COM_API.md) with OpenSubtitles.com
  REST API reference covering authentication (API key + JWT), download limits,
  required headers, example curl requests, subtitle encoding/formats, and
  debugging tips.

- Added OpenSubtitles user authentication (JWT login) for subtitle downloads.
  The REST API requires a logged-in user token for `/download` requests;
  without it, downloads are limited to 5 per IP per 24 hours. Added
  `opensubtitles_username` and `opensubtitles_password` fields to settings,
  username/password inputs in the Settings dialog API Keys tab, a `login()`
  method on `SubtitleScraper`, and `auth_failed` category in `DownloadCategory`.
  Login is called automatically before subtitle search/download when credentials
  are configured.
- Created [docs/INSTALL.md](INSTALL.md) with setup steps, dependencies, and verify command.
- Created [docs/USAGE.md](USAGE.md) with CLI subcommand reference, GUI launch instructions,
  and common workflow examples.
- Rewrote [README.md](../README.md) with project overview, quick start, curated documentation
  links, testing command, and maintainer contact.
- Added `_has_poster_cache` and `_has_trailer_cache` fields to `Movie` dataclass.
  Scanner sets these during `os.walk()` using the filenames list, so `has_poster`
  and `has_trailer` properties skip filesystem re-stat when cached.
- Added NFO timing breakdown to scanner summary line:
  `[scan] 74 movies in 76 dirs, 2953ms (nfo=2400ms)`.
- Moved badge counting (`check_organized` + `has_poster` + `has_trailer` loop)
  to a background thread in `_finalize_scan`. Badge counts are computed off the
  main thread and applied via `_apply_badge_counts` callback.
- Reduced scan batch timer from 1000ms to 200ms so movies appear in the table
  within ~200ms of discovery instead of ~1s.
- Switched parental guide fetching from HTML scraping to the IMDB GraphQL API
  (`api.graphql.imdb.com`) via `curl_cffi`. The `__NEXT_DATA__` JSON on the
  parental guide page no longer contains severity data (IMDB moved it to
  lazy-loaded GraphQL). The new `_fetch_parental_guide_graphql()` function
  calls the API directly, returning structured data without HTML parsing.
  Movies without parental guide data now return an empty dict immediately
  instead of falling through to the browser transport and timing out after
  15 seconds.
- Added `curl_cffi` as primary transport for parental guide fetches in
  `imdb_scraper.py`. Uses `impersonate='chrome'` to bypass WAF without the
  QWebEnginePage browser engine, eliminating timeout failures from
  `loadFinished never fired`. Falls back to browser transport if `curl_cffi`
  fails. Parses `contentData.categories[].severitySummary.text` JSON path
  from the `curl_cffi` response.
- Created [docs/HOW_TO_PROPERLY_DOWNLOAD_IMDB_PARENTS_GUIDE_DATA.md](HOW_TO_PROPERLY_DOWNLOAD_IMDB_PARENTS_GUIDE_DATA.md)
  documenting lessons learned from parental guide scraping: what works
  (`curl_cffi`, QWebEnginePage, Selenium), what does not (plain requests,
  cookie transfer), the three `__NEXT_DATA__` JSON paths, and rate limiting.
- Updated [docs/WAF_CHALLENGES.md](WAF_CHALLENGES.md) with `curl_cffi` parental guide
  transport documentation and separated metadata/parental-guide WAF sections.
- Updated [docs/WAF_CHALLENGES.md](WAF_CHALLENGES.md) with diagnostic logging reference
  (stage table, timeout stage labels), timeout tuning guidance for parental guide fetches,
  and a note on IMDB data dumps as an alternative data source for structured data.

- Added `get_chosen_movies()` to `MoviePanel` for unified batch operation resolution:
  checked (2+) > selected (2+) > single checked > single selected > empty.
- Added "Check Selected" button that converts highlighted rows into checkboxes (additive).
- Added `check_movies()` to `MovieTableModel` for programmatic additive checking.
- Added [docs/MOVIE_ORGANIZATION_UI_UX_WORKFLOW.md](MOVIE_ORGANIZATION_UI_UX_WORKFLOW.md)
  documenting checkbox vs row selection, resolution order, and button bar reference.

- Added "Refresh Metadata" toolbar button and Movie menu item to re-fetch
  IMDB/TMDB metadata for matched movies with cache bypass
  (`moviemanager/ui/main_window.py`, `moviemanager/api/movie_api.py`).
- Added "Refresh Stats" toolbar button and Movie menu item to re-probe video
  files for codec, resolution, and duration (`moviemanager/ui/main_window.py`).
- Added `bypass_cache` parameter to `scrape_movie()` in `movie_api.py` to skip
  metadata and parental guide cache lookups when refreshing.
- Added runtime proximity scoring to match confidence
  (`moviemanager/api/match_confidence.py`). Uses a Gaussian bell curve
  (sigma=15 min) so close runtimes boost confidence and large mismatches
  penalize it. When runtime is unavailable (0), the signal is neutral (0.5).
- Added `runtime` field to `SearchResult` dataclass in
  `moviemanager/scraper/types.py` for future use when search APIs provide it.
- Rebalanced match confidence weights: title 0.45 (was 0.50), year 0.20
  (was 0.25), runtime 0.10 (new), token overlap 0.15 (unchanged),
  popularity 0.10 (unchanged).
- `MovieChooserDialog` now passes local movie runtime to search and
  broader-search calls for runtime proximity scoring.
- Added 3 new tests in `tests/test_match_confidence.py` for
  `_runtime_proximity()`, runtime-improves-match, and runtime-mismatch-hurts.
- Added "Min" runtime column to the movie chooser results table and a runtime
  label in the preview pane (`moviemanager/ui/dialogs/movie_chooser.py`).

- Added `shell_safe_filename()` to `moviemanager/core/utils.py` using a whitelist approach modeled
  on `rmspaces.py`: transliterates unicode to ASCII via `unidecode`, replaces `&` with `and`,
  replaces quotes with underscores, and strips any character not in `-./_0-9A-Za-z`.

- Added `<fileinfo><streamdetails>` read/write support to NFO reader and writer
  (`moviemanager/core/nfo/reader.py`, `moviemanager/core/nfo/writer.py`). Caches probe results
  (video codec, resolution, aspect ratio, duration, audio codec, channels) in NFO files using
  standard Kodi format. On subsequent scans, cached data is loaded from NFO, avoiding re-probing.
- Scanner now populates video MediaFile fields from NFO `<fileinfo>` data during merge
  (`moviemanager/core/movie/scanner.py`). Files with cached probe data skip pymediainfo probing.
- `probe_movie_list()` now sets `movie.runtime` from probe duration when runtime is not already
  set by NFO metadata (`moviemanager/core/media_probe.py`).

- Added Calibre-style background job system for scraping. Clicking "Accept Match" now runs
  `scrape_movie()` in a background worker thread instead of blocking the UI. Jobs are tracked
  by a new `JobManager` layer in `moviemanager/ui/task_api.py` with `submit_job()`, `active_count`,
  `all_jobs`, and `job_list_changed` signal.
- Added "Jobs: N" button to the status bar (`moviemanager/ui/widgets/status_bar.py`). The button
  text bolds when jobs are active and emits `jobs_clicked` when clicked.
- Created `moviemanager/ui/dialogs/jobs_dialog.py`: a non-modal popup listing running and completed
  background jobs with name, status, and elapsed time. Includes "Clear Completed" button.
- `MovieChooserDialog` now accepts an optional `task_api` parameter and submits scrape work through
  it for job tracking. Falls back to its own thread pool when no `task_api` is provided.
- `MainWindow` creates a shared `TaskAPI` instance, passes it to `MovieChooserDialog`, wires
  `job_list_changed` to the status bar count, and connects the jobs button to the popup dialog.
  `closeEvent` warns if background jobs are still running and calls `task_api.shutdown()`.

- Added "Min" (duration in minutes) column to movie table, sourced from pymediainfo file duration.
  Column is visible by default, sortable, and uses ResizeToContents mode
  (`moviemanager/ui/movies/movie_table_model.py`, `moviemanager/core/media_probe.py`).
- `probe_media_file()` now extracts `duration_seconds` from the General track in pymediainfo.
  Scanner stores this value in `MediaFile.duration` (`moviemanager/core/movie/scanner.py`).

- Created `moviemanager/core/media_probe.py` wrapping pymediainfo to extract video codec, audio
  codec, resolution, and audio channels from video files. Normalizes codec names to short labels
  (AVC -> h264, HEVC -> hevc, AAC -> aac, AC-3 -> ac3) and channel counts to labels (6 -> 5.1).
- Scanner now calls `probe_media_file()` during scan to populate MediaFile codec/resolution fields
  (`moviemanager/core/movie/scanner.py`).
- Renamer `expand_template()` now supports media tokens: `{resolution}`, `{vcodec}`, `{acodec}`,
  `{channels}`, plus aliases `{codec}` and `{audio}` (`moviemanager/core/movie/renamer.py`).
- Added `build_file_template()` function to assemble file template from base pattern plus enabled
  media token checkboxes with configurable separator (`moviemanager/core/movie/renamer.py`).
- Added settings fields: `media_separator`, `rename_resolution`, `rename_vcodec`, `rename_acodec`,
  `rename_channels` to Settings dataclass (`moviemanager/core/settings.py`).
- Settings dialog Renamer tab now includes a Token Separator combo box (hyphen, dot, underscore)
  and four media token checkboxes (Resolution, Video Codec, Audio Codec, Audio Channels). Live
  preview shows both folder and file name with example media values
  (`moviemanager/ui/dialogs/settings_dialog.py`).
- Redesigned status columns from D(Data) N(NFO) A S T to M(Matched) O(Organized) A S T, reflecting
  the Match -> Organize -> Download workflow. Column 4 now maps to `movie.scraped`, column 5 to
  the new `movie.is_organized` property.
- Added `is_organized` property to `Movie` model (`moviemanager/core/models/movie.py`). Returns True
  when `multi_movie_dir` is False and the folder name contains the movie title (normalized for
  underscores and hyphens).
- Added `spaces_to_underscores` setting (default True) to `Settings` dataclass. When enabled, the
  renamer replaces spaces with underscores and strips shell-unsafe characters from folder/file names.
- Changed default renamer templates from `{title} ({year})` to `{title}-{year}` for Unix-safe folder
  naming. Example output: `The_Matrix-1999/`.
- Added "Replace spaces with underscores" checkbox and live folder name preview to the Renamer tab
  in Settings dialog (`moviemanager/ui/dialogs/settings_dialog.py`).
- Renamer now collects subtitle and trailer files alongside video, NFO, and artwork when organizing
  movies into folders (`moviemanager/core/movie/renamer.py`).
- Renamer removes empty old directories after moving all files to the new location.
- Renamer skips generating rename pairs when source paths equal destination paths (movie already
  correctly named).

- Rebuilt `TaskAPI` (`moviemanager/api/task_api.py`) as a Qt-integrated task manager using
  `QThreadPool` and `Worker`/`WorkerSignals` instead of `ThreadPoolExecutor`. Emits Qt signals
  (`task_finished`, `task_error`, `task_progress`) for direct UI connection. Supports submit,
  cancel, is_running, is_done, get_result, and get_worker.
- Moved batch download loop in `DownloadDialog` off the main thread. Extracted download logic
  into `_run_batch_download()` standalone function, run via `Worker` in `QThreadPool`. UI stays
  responsive during downloads; cancel button calls `worker.cancel()`. Progress bar and status
  label update via signals.
- Moved batch scrape (`_batch_scrape_unscraped`) off the main thread. Replaced modal
  `QProgressDialog` with status bar progress. Extracted scraping loop into `_batch_scrape_loop()`
  method run via `Worker`. Results delivered via `_on_batch_scrape_done()` signal handler.
- Replaced generic toolbar icons with descriptive themed icons: Match uses `edit-find` (magnifying
  glass), Organize uses `folder-new`, Download uses `go-down`, Settings uses `preferences-system`,
  Quit uses `application-exit`. All use `QIcon.fromTheme()` with system fallbacks.
- Added separator between workflow buttons (Match/Organize/Download) and utility buttons
  (Settings/Quit) for clearer visual grouping.
- Changed column headers from cryptic single-letter abbreviations to readable compact labels:
  D/N/A/S/T became Data/NFO/Art/Sub/Trl; SN/VG/Pr/AD/FI became S&N/V&G/Prof/A&D/F&I. Updated
  `_COLUMN_DISPLAY_NAMES` in `movie_panel.py` to match.
- Renamed table columns 4-5 from Data/NFO (col headers "Data"/"NFO") to Mtch/Org (headers
  "Mtch"/"Org") in `movie_table_model.py` COLUMNS and STATUS_COLUMNS. Column 4 now maps to
  `scraped` attribute ("Matched" tooltip), column 5 maps to `is_organized` attribute ("Organized"
  tooltip). Updated `_COLUMN_DISPLAY_NAMES` in `movie_panel.py` accordingly.
- Locked Title (col 1) and all five status columns (cols 4-8) from being hidden via the header
  right-click context menu in `movie_panel.py`. Added `locked_columns = {1, 4, 5, 6, 7, 8}` set
  and skip logic in `_show_header_context_menu`.
- Added resize-mode reapplication in `restore_table_state` in `movie_panel.py` to prevent stale
  QSettings from giving Stretch resize mode to wrong columns after header state restore.
- Added `checked_changed` signal to `MovieTableModel`, emitted on check/uncheck/check_all/
  uncheck_all/check_unscraped. Bubbled through `MoviePanel` to `MainWindow` for status bar
  checked count display.
- Added Select All / Select None / Select Unmatched buttons above the movie table in
  `MoviePanel` for quick batch selection.
- Auto-select first movie row after scan completes so the detail panel shows info immediately
  instead of remaining blank.
- Added "No movie selected" placeholder text in detail panel title label when no movie is
  selected. Added placeholder text "No plot available" on the plot QTextEdit.
- Added workflow count badges on toolbar buttons: "1. Match (N)" shows unmatched count,
  "2. Organize (N)" shows matched-but-no-NFO count, "3. Download (N)" shows incomplete count.
  Badges update after scan, scrape, organize, and download operations.
- Added dark mode toggle button in toolbar between Settings and Quit. Uses checkable action
  with `weather-clear-night` themed icon.
- Enhanced dark theme with QSS stylesheet in `theme.py` for polished scrollbars, table headers,
  toolbar hover/pressed states, button styling, tab bar, status bar, progress bar, group boxes,
  and checkboxes. Light/system themes clear the stylesheet.
- Fixed tooltip background in dark theme: changed `ToolTipBase` from white to dark gray so
  tooltip text is readable against its background.
- Implemented progressive directory scanning. Movies now fill into the table incrementally as
  they are discovered, instead of waiting for the full scan to complete. Added `partial_result`
  signal to `WorkerSignals`, `movie_callback` parameter to `scanner.scan_directory()` and
  `MovieAPI.scan_directory()`, `append_movies()` to `MovieTableModel` and `MoviePanel`, and
  wired up incremental delivery in `MainWindow._scan_directory()`.
- Optimized `detect_artwork_files()` to accept the `filenames` list from `os.walk()` and use
  set membership checks instead of ~17 `os.path.isfile()` stat calls per directory.
- Cached stopwords set at module level in `moviemanager/core/utils.py` as `STOPWORDS_LOWER`
  frozenset, avoiding per-call set construction in `parse_title_year()`.
- Extracted `MovieTableModel._matches_filter()` helper for filter logic reuse between
  `_apply_filter()` and `append_movies()`.

- Created [docs/NFO_FILE_FORMAT.md](NFO_FILE_FORMAT.md) documenting the Kodi NFO XML
  file format. Covers tag reference table, full sample NFO, reader/writer implementation
  details, combination NFO behavior, round-trip element preservation, and differences from
  the modern Kodi v17+ format. Includes parental guide custom extension documentation.
- Created `moviemanager/ui/format_movie.py` with pure formatting functions for movie
  metadata display. Consolidates duplicated `int->str` / `float->str` conversion logic
  from `MovieDetailPanel.set_movie()` and `MovieChooserDialog._show_prematch_view()` into
  shared functions: `format_rating()`, `format_genres()`, `format_runtime()`, `format_ids()`,
  and `format_movie_fields()`. Added `tests/test_format_movie.py` with 13 tests.

### Behavior or Interface Changes

- Added pre-flight credential check before subtitle downloads. Both single-movie
  and batch download paths now check for API key, username, and password before
  queuing jobs. If anything is missing, a warning dialog tells the user what is
  needed and offers to open Settings.

- Renamed all "Select X" buttons to "Check X" (Check All, Check None, Check Unmatched,
  Check Unorganized, Check No PG, Check No Artwork, Check No Subs) to clarify they toggle
  checkboxes, not row highlighting.
- Updated `_scrape_selected()`, `_rename_selected()`, `_download_content()`,
  `_fetch_parental_guides()`, and `_refresh_metadata()` in `MainWindow` to use
  `get_chosen_movies()` instead of inline checked/selected logic.
- `_fetch_parental_guides()` and `_refresh_metadata()` now respect row selection in addition
  to checkboxes; previously they only checked checkboxes and fell back to all movies.

- Added parental guide color bar to the movie edit dialog below the poster. Shows 5 colored
  circles (S&N, V&G, Prof, A&D, F&I) with severity colors reused from `status_delegate.py`,
  tooltips with full category names, and the `parental_guide_checked` date.
- Redesigned the right-side detail panel Info tab: poster image on top with compact metadata form
  and scrollable plot below. Poster removed from Artwork tab (fanart only now).
- Narrowed default detail panel splitter ratio from 60/40 to 75/25 (poster-width panel).
- Added four new selection buttons: "Select Unorganized", "Select No PG", "Select No Artwork",
  "Select No Subs" with corresponding `check_*` methods on `MovieTableModel` and `MoviePanel`.
- Added [docs/TASK_API.md](TASK_API.md): developer reference for `TaskAPI`, worker system,
  priority constants, job metadata, signals, error categorization, and error log format.
- Added [docs/BACKGROUND_JOBS.md](BACKGROUND_JOBS.md): user-facing guide to the background jobs
  dialog, job types and priorities, download error categories, error summary, and error log.
- Added `moviemanager/api/download_errors.py` with `DownloadCategory` enum and `DownloadError`
  exception for categorized download failure reporting. Categories: `no_url`, `no_api_key`,
  `no_imdb_id`, `no_results`, `network_error`, `api_error`, `download_failed`, `timeout`, `no_path`.
- `download_trailer()` and `download_subtitles()` now raise `DownloadError` with specific
  categories instead of returning empty values or letting raw exceptions propagate. yt-dlp errors
  include the last stderr line; subtitle API errors are caught and categorized.
- Workers prefix `CATEGORY:name` in error signals for `DownloadError` exceptions so the task API
  can parse and store the category separately from the traceback.
- `TaskAPI` job metadata now includes `error_category` field. `_on_error()` parses the category
  prefix and appends one-line entries to `/tmp/movie_manager_errors.log`.
- Jobs dialog status column shows `"Error: No Url"` style category labels instead of truncated
  tracebacks. Full traceback remains in tooltip.
- Added "Error Summary" button to jobs dialog that shows a `QMessageBox` with error counts grouped
  by category (e.g. "No Url: 40, Download Failed: 10, Timeout: 4").
- Removed `trailer_url` and `imdb_id` pre-filters from `_build_download_tasks()` so movies
  without these fields still get queued and fail with descriptive `DownloadError` messages
  visible in the jobs dialog.
- Added `parental_guide_checked` field to `Movie` model and `MediaMetadata` dataclass. Stores
  ISO date string when parental guide was last checked, distinguishing "no data on IMDB" from
  "fetch failed." Movies confirmed to have no parental guide data are not re-fetched until
  90 days after the check date (`_PARENTAL_GUIDE_RECHECK_DAYS`).
- Added `parental_guide_checked` element to NFO reader/writer for persistence across sessions.
- Added `fetch_parental_guides()` method to `MovieAPI` for standalone parental guide fetching
  with cache awareness, progress callbacks, and per-movie NFO updates.
- Added "Parental Guide" toolbar button in `MainWindow` (between Refresh Metadata and Refresh
  Stats) with `security-medium` theme icon. Launches background job to fetch parental guide
  data from IMDB for matched movies, with summary dialog on completion showing
  fetched/no_data/failed/skipped counts.
- Updated `scrape_movie()` parental guide section to set `parental_guide_checked` date on
  successful fetch or cache hit (whether guide is empty or populated), and skip fetch when
  movie was confirmed empty within the 90-day recheck window.
- Added job priority constants to `moviemanager/ui/task_api.py`: `PRIORITY_CRITICAL` (100),
  `PRIORITY_HIGH` (75), `PRIORITY_NORMAL` (50), `PRIORITY_LOW` (25), `PRIORITY_BACKGROUND` (0).
  `QThreadPool.start(worker, priority)` schedules higher-priority jobs first.
- Added `_priority` keyword parameter to `TaskAPI.submit()` and `TaskAPI.submit_job()`.
  Priority is stored in job metadata for display in the Jobs dialog.
- Added "Priority" column to the Jobs dialog table between Name and Status, showing
  human-readable labels (Critical, High, Normal, Low, Background).
- Migrated directory scan, batch scrape, and refresh metadata from direct `Worker`/`_pool`
  usage to `TaskAPI.submit_job()` with priority. Scan uses `PRIORITY_CRITICAL`, scrape and
  refresh use `PRIORITY_HIGH`, media probe uses `PRIORITY_NORMAL`, and downloads use
  `PRIORITY_LOW`.
- Added central signal dispatchers (`_on_task_finished`, `_on_task_error`,
  `_on_task_progress`) in `MainWindow` to route TaskAPI signals by task ID to the
  appropriate handler, replacing per-worker signal connections.
- Assigned explicit priorities to all `pool.start()` calls in dialogs:
  `movie_chooser.py` (search: HIGH, posters: BACKGROUND, scrape: HIGH),
  `download_dialog.py` (LOW), `image_chooser.py` (BACKGROUND),
  `movie_detail_panel.py` (BACKGROUND).

- Added `download_image_bytes()` helper function to `moviemanager/ui/workers.py`, extracting
  the HTTP download logic from `ImageDownloadWorker` into a plain callable for use with TaskAPI.
- Migrated remaining local `QThreadPool` instances to TaskAPI:
  - `main_window.py`: 4 rename operations (single/batch preview and execution) via
    `submit_job()` with `PRIORITY_CRITICAL` and `_rename_mode` discriminator for signal routing.
  - `movie_chooser.py`: 7 operations (search, broader search, prematch poster, poster preview,
    scrape, prefetch search, prefetch poster) via `submit()` and `submit_job()`. Removed
    fallback scrape branch that used the local pool when `task_api` was `None`.
  - `image_chooser.py`: 2 operations (preview download, artwork download) via `submit()` and
    `submit_job()`. Added `task_api` constructor parameter.
  - `download_dialog.py`: 1 batch download operation via `submit_job()` with `PRIORITY_LOW`.
    Added `task_api` constructor parameter.
- Removed `self._pool = QThreadPool()` from `MainWindow`, `MovieChooserDialog`,
  `ImageChooserDialog`, and `DownloadDialog`. Only `MovieDetailPanel` retains a local pool
  for image loading.
- Added `started` signal to `WorkerSignals` in `moviemanager/ui/workers.py`, emitted in
  `Worker.run()` just before the callable executes.
- Added `started_at` and `"queued"` initial status to `TaskAPI` job metadata. Jobs now
  transition through queued -> running -> done/error. The `_on_started()` handler sets
  `started_at` timestamp and flips status to `"running"` when the worker begins execution.
- Added failed parental guide tracking to `MovieAPI`: `_failed_parental_guides` list populated
  in `scrape_movie()` on timeout, with `retry_failed_parental_guides()`,
  `has_failed_parental_guides()`, and `clear_failed_parental_guides()` methods.
- Added automatic deferred retry for failed parental guide fetches: `_on_batch_scrape_done()`
  submits a `PRIORITY_LOW` retry job when failures occurred. Retry result includes
  succeeded/still_failed counts. Parental guide timeout count shown in batch scrape summary.
- Jobs dialog now shows 5 columns: Name, Priority, Status, Queued, Active. "Queued" shows
  time since submission, "Active" shows time since worker started (or "--" while waiting).
  Error text truncation increased from 60 to 120 chars. Error status cells have a tooltip
  with the full error text.

- Added "Progress" column to the Jobs Dialog showing `"N/M"` or `"N/M (X failed)"` for
  running jobs with progress callbacks. `TaskAPI` now stores per-task progress tuples and
  exposes them via `all_jobs`.
- Parental guide progress messages now include running success/fail tallies in both the
  status bar and Jobs Dialog (e.g., `"Parental guide: Title (3/42) - 1 fetched, 2 failed"`).
- Each parental guide fetch outcome (cached, fetched, empty, failed) is logged at INFO level
  with a running tally for terminal/log visibility.
- Reduced parental guide page timeout from 30s to 15s in `imdb_scraper.py`, halving
  wall-clock time for WAF-blocked failures.
- Routed all downloads (artwork, trailers, subtitles) through `TaskAPI.submit_job()`
  so each appears as an individual tracked job in the Jobs dialog
  (`moviemanager/ui/main_window.py`).
- Batch downloads now submit one job per content type per movie (e.g., "Artwork:
  The Matrix", "Trailer: The Matrix") instead of one opaque background worker.
- Single-movie trailer and subtitle downloads from the context menu are now queued
  via TaskAPI and visible in the Jobs dialog, instead of blocking with a wait cursor.
- Removed the separate "downloads in progress" close warning from `closeEvent`;
  download jobs are now covered by the existing TaskAPI active-count check.

- Jobs dialog now refreshes every 1 second via a `QTimer` so the elapsed time
  column stays current while jobs are running. Timer stops when the dialog is
  hidden or closed (`moviemanager/ui/dialogs/jobs_dialog.py`).

- Rename preview dialog (`moviemanager/ui/dialogs/rename_preview.py`) now displays relative paths
  instead of full absolute paths. Computes the common base directory of all source and destination
  paths and shows it in the info label (e.g., "3 file(s) will be renamed (in .../Movies/Collection/):")
  while table cells use `os.path.relpath()` for shorter, more readable entries.
- Renamer shell-safe mode now uses the new `shell_safe_filename()` function instead of inline
  regex in both `moviemanager/core/movie/renamer.py` and the settings dialog preview
  (`moviemanager/ui/dialogs/settings_dialog.py`). Handles unicode, quotes, ampersands, and more
  shell-unsafe characters than the previous implementation.
- Renamed the shell-safe checkbox label from "Replace spaces with underscores (shell-safe)" to
  "Shell-safe filenames (ASCII, no spaces or special characters)".

- Min column now falls back to NFO/scraped `movie.runtime` when probe duration is unavailable
  (`moviemanager/ui/movies/movie_table_model.py`). Previously the column was empty until probing
  completed; now scraped movies show runtime immediately on scan.
- Media probe now uses `TaskAPI.submit_job()` instead of raw `QThreadPool`, so it appears in the
  Jobs dialog with proper progress tracking and error handling (`moviemanager/ui/main_window.py`).

- Deferred media probing to a background worker so movies appear in the table immediately after scan.
  Removed synchronous `probe_media_file()` call from `moviemanager/core/movie/scanner.py`. Added
  `probe_movie_list()` in `moviemanager/core/media_probe.py` that iterates all video MediaFiles and
  populates codec/resolution fields in-place. `_on_scan_done()` in `moviemanager/ui/main_window.py`
  now launches a background Worker that runs `probe_movie_list()` with status bar progress, then
  refreshes the table when complete.
- Reduced status and parental guide icon column widths from ~65px (ResizeToContents) to 36px (Fixed)
  in `moviemanager/ui/movies/movie_panel.py`. Frees ~300px for the Title column.
- Shortened status column headers from Mtch/Org/Art/Sub/Trl to single-character M/O/A/S/T in
  `moviemanager/ui/movies/movie_table_model.py` to fit narrow fixed-width columns.
- Updated default `visible_columns` in `moviemanager/core/settings.py` to match new single-character
  header names.

- Title and all five status columns (Mtch, Org, Art, Sub, Trl) are now locked and cannot be hidden
  via the header right-click context menu (`moviemanager/ui/movies/movie_panel.py`).
- `restore_table_state()` now re-applies programmatic resize modes after restoring QSettings header
  state, preventing stale settings from giving Stretch size to the wrong column.
- Toolbar badge counts updated: Organize badge counts `scraped and not is_organized`, Download badge
  counts `is_organized and not (has_poster and has_trailer)`.
- `_update_movie_paths()` now sets `movie.multi_movie_dir = False` after rename, since the movie is
  in its own dedicated folder by definition.
- Replaced modal `DownloadDialog` with non-blocking background download worker. Downloads run via
  status bar progress while user can continue matching and organizing. Confirmation dialog shown
  before starting.
- `closeEvent` now warns if background downloads are still running and allows user to cancel quit.
- Updated `visible_columns` default list in Settings to use new column keys: Mtch, Org instead of
  D, N.

- Replaced modal `DownloadDialog` with non-blocking background worker in `MainWindow._download_content()`.
  User confirms with a question dialog then downloads run in `QThreadPool` via `_run_background_downloads()`.
  Progress shown in status bar; completion and errors handled by `_on_background_download_done()` and
  `_on_background_download_error()`. Added `_download_worker` attribute initialized in `__init__` to
  track and guard against concurrent downloads. `closeEvent` now warns and asks confirmation if a
  download is still running.
- Fixed `_update_toolbar_badges()` unorganized count: now uses `not m.is_organized` instead of
  `not m.has_nfo`. Incomplete count now requires `m.is_organized` as a prerequisite (only organized
  movies that lack poster or trailer are counted). Removed incorrect `else` nesting that caused all
  scraped movies regardless of organization state to be counted for incomplete.
- Moved all lazy dialog imports in `main_window.py` to top-level module imports. Eliminates
  ~500ms first-click delay on Match, Organize, Download, Edit, Settings, and Dark Mode toggle
  buttons. Affected imports: `movie_chooser`, `movie_editor`, `rename_preview`, `download_dialog`,
  `settings_dialog`, `theme`, `os`, `shutil`.
- Replaced full table model resets (`set_movies`) with targeted `refresh_data()` after scrape,
  edit, and download operations. New `MovieTableModel.refresh()` emits `dataChanged` for all
  visible cells without resetting the model, preserving selection, scroll position, and checked
  state. Full `set_movies()` is now only used on initial directory scan and rename (where paths
  change).
- Moved rename dry-run computation and rename execution to background threads. Single and batch
  rename now compute file pairs via `Worker` in `QThreadPool`, show preview dialog on completion,
  and execute renames in background. UI remains responsive during file I/O operations.
- Loaded detail panel artwork (poster.jpg, fanart.jpg) asynchronously in background threads.
  `MovieDetailPanel.set_movie()` now reads image files via `Worker` and updates `ImageLabel`
  via `set_image_data()` on completion. Cancels in-flight image loads on selection change.
  Eliminates main-thread blocking from disk I/O during row navigation.
- Optimized `_update_toolbar_badges()` from three separate list comprehensions over all movies
  to a single pass, reducing iterations by 2/3.
- Fixed auto-select first row behavior: now only auto-selects on initial table load (when table
  was previously empty), not on every refresh. Prevents selection jumping to row 0 after scrape,
  edit, or download when user was viewing a different movie.
- Removed redundant `resizeColumnsToContents()` call from `MoviePanel.set_movies()` since column
  resize modes are already configured in `_build_content()`.

- Rating column in the movie table now displays one decimal place (e.g., "7.3" instead of "7.258")
  for cleaner, more consistent formatting.
- Movie editor dialog now shows the poster image alongside the metadata form. Poster is displayed
  on the left side of the dialog, loaded from the movie's `poster_url` or `poster.jpg` in the
  movie directory.
- IMDB ID and TMDB ID fields in the movie editor now have "Open" buttons that launch the
  corresponding IMDB or TMDB page in the default browser. Buttons are disabled when no ID is set.

- Refactored `MovieDetailPanel.set_movie()` in `moviemanager/ui/movies/movie_detail_panel.py`
  and `MovieChooserDialog._show_prematch_view()` in `moviemanager/ui/dialogs/movie_chooser.py`
  to use shared `moviemanager.ui.format_movie.format_movie_fields()` instead of inline
  formatting. No visible behavior change.
- Persist parents guide severity data in NFO files. Writer emits `<parental_guide>`
  with `<advisory category="...">` children, reader parses them back, and scanner
  merges them on startup. Data now survives app restarts instead of being discarded
  every session. Added round-trip test in `tests/test_nfo_round_trip.py`.
- Created `moviemanager/ui/imdb_browser_transport.py` with `ImdbBrowserTransport`
  class that uses `QWebEnginePage` (Chromium engine) to load IMDB pages. The browser
  engine solves AWS WAF JavaScript challenges automatically, bypassing blocks that
  defeat curl_cffi. Features persistent `QWebEngineProfile` with disk-based cookie
  storage at `~/.cache/movie_organizer/webengine/`, custom Chrome User-Agent to avoid
  IMDB banning QtWebEngine/HeadlessChrome identifiers, and thread-safe `fetch_html()`
  using Signal + `threading.Event` pattern for Qt main thread bridging.
- Replaced IMDB GraphQL API with CDN suggestion API for search and QWebEnginePage
  transport for metadata/parental guide. The suggestion endpoint
  (`v2.sg.media-imdb.com/suggestion/titles/x/{query}.json`) has no WAF protection,
  so search uses plain HTTP via `requests`. Metadata and parental guide pages are
  loaded through the browser transport which handles WAF JS challenges automatically.
- Added `set_transport()` method to `ImdbScraper` for injecting the browser transport.
  Search still works without transport (uses CDN suggestion API). Metadata and parental
  guide require the transport for page loads.
- Added `_parse_metadata_html()` and `_parse_parental_guide_html()` functions that
  extract structured data from IMDB page HTML by parsing the `__NEXT_DATA__` JSON
  embedded in script tags.
- Added `_fetch_suggestion()` and `_parse_suggestion_results()` for CDN suggestion API.
  Filters results to movie types only (movie, short, tvMovie). Computes popularity
  score from suggestion rank.
- Updated `ImdbChallengeDialog` to accept optional `profile` parameter for sharing
  `QWebEngineProfile` with the browser transport. When shared, cookies and WAF
  immunity tokens persist across both transport and manual challenge dialog sessions.
- Updated `MovieAPI._ensure_scraper()` to create `ImdbBrowserTransport` lazily via
  `_ensure_imdb_transport_on_scraper()`. Transport is only created when metadata or
  parental guide fetch is needed, not during search. Silently skips transport creation
  when no Qt application is running (CLI mode or tests).
- Fixed `MovieAPI.apply_imdb_cookies()` to report whether any IMDB scraper exists
  for cookie application, covering both primary and supplement scrapers.
- Created [docs/WAF_CHALLENGES.md](WAF_CHALLENGES.md) documenting how AWS WAF
  JavaScript challenges work, why curl_cffi and cookie transfer fail, how the app
  handles WAF via QWebEnginePage transport, the thread bridging pattern, and the
  CAPTCHA fallback flow.

- Redesigned prematch view in `MovieChooserDialog` to show a structured metadata
  card with poster, rating, director, genres, certification, runtime, IDs, and
  plot instead of a plain text summary. Uses `QFrame` with `StyledPanel` border
  and a banner row with checkmark icon for visual distinction.
- Replaced small "Re-match" button with prominent "Find Different Match" button
  in prematch view.
- Added "Keep Original Match" button that appears in search mode when user came
  from prematch, allowing return to the original match without re-scraping.
- Added matched/unmatched indicator in batch progress label (e.g. "Movie 2 of 5
  (matched)").
- Prematch poster uses a movie-specific cache file named
  `{video_basename}-poster.jpg` (e.g. `The.Dark.Knight.2008.BluRay.x264-poster.jpg`)
  instead of the generic `poster.jpg` which is ambiguous in multi-movie directories
  and before the organize step. Downloads from `poster_url` on first view and
  caches to disk for instant loading on subsequent opens.
- IMDB search now uses CDN suggestion API instead of GraphQL. The suggestion API
  is faster and has no WAF protection, eliminating search failures from JavaScript
  challenges. Result format is slightly different: no plot overview, scores derived
  from suggestion rank instead of aggregate rating.
- IMDB metadata and parental guide now load full HTML pages via QWebEnginePage
  instead of GraphQL queries. This is slower (full page load vs JSON POST) but
  immune to WAF blocking since the Chromium engine executes challenge JavaScript
  automatically.
- Rate limiting increased for page loads: `time.sleep(1 + random.random())` before
  each QWebEnginePage load (max ~1 req/sec) vs `time.sleep(random.random())` for
  the old GraphQL approach. CDN suggestion API retains the lighter rate limiting.
- `ImdbScraper` no longer uses `curl_cffi`. The `set_cookies()` method and
  `_session` attribute are removed. Cookie management is handled by the
  `QWebEngineProfile`'s persistent cookie store.
- `_apply_configured_imdb_browser_cookies()` in `MovieAPI` is now a no-op. Browser
  cookies are managed automatically by the transport's persistent profile. The
  method is kept for backward compatibility.
- `ImdbBrowserTransport` is in `moviemanager/ui/` (not `moviemanager/scraper/`)
  to maintain the PySide6 import guard on core/scraper/api packages.

- `MovieAPI.compute_match_confidence()` now delegates to the standalone
  `moviemanager.api.match_confidence` module instead of using its own inline logic.
  The static method signature is preserved for backward compatibility.
- `_batch_scrape_unscraped()` in `main_window.py` now uses pre-computed
  `best.match_confidence` from search results instead of calling
  `MovieAPI.compute_match_confidence()` separately.
- TMDB scraper selection is now automatic based on API key presence; the
  `scraper_provider` setting is no longer checked. TMDB key exists = TMDB primary.

### Fixes and Maintenance

- Fixed OpenSubtitles 429 rate-limit errors during batch subtitle downloads.
  Previously each `download_subtitles()` call created a new scraper and called
  `login()`, triggering the 1 req/sec rate limit. Now the authenticated scraper
  is cached on the `MovieAPI` instance (JWT valid 24h) and reused across jobs.
- Added `threading.Lock` to `_get_subtitle_scraper()` using double-checked
  locking pattern. When multiple subtitle jobs run concurrently, only the first
  thread performs login; the rest wait on the lock and reuse the cached scraper.
  Previously concurrent threads all raced to login simultaneously, causing 429s.
- Enforced minimum 1-second gap (plus jitter) between all OpenSubtitles API
  requests in `SubtitleScraper`. Replaced `time.sleep(random.random())` with a
  timestamp-based rate limiter that tracks elapsed time since last request.

- Enforced credential requirement for subtitle downloads. The OpenSubtitles
  `/download` endpoint requires JWT auth; previously missing credentials caused
  silent 401 errors. Now raises a clear `auth_failed` error early if username or
  password is not configured.
- Wrapped `scraper.download()` call with exception handling matching the existing
  `scraper.search()` pattern (401 -> auth_failed, timeout, connection error,
  generic request error). Previously raw `HTTPError` tracebacks propagated
  uncategorized.
- Fixed `UnboundLocalError` in `download_subtitles()` caused by inline
  `import moviemanager.scraper.subtitle_scraper` inside the method. Python
  treated `moviemanager` as local to the entire function, breaking earlier
  references on lines 795-796. Moved the import to top-level with the other
  `moviemanager.scraper.*` imports.
- Improved error display in jobs dialog for uncategorized errors (e.g.
  tracebacks). Now finds the last non-empty line instead of blindly taking
  the final line, which could be empty.

- Fixed segfault on application exit caused by Qt destroying QWebEngineProfile
  before QWebEnginePage. Added `shutdown()` methods to `ImdbBrowserTransport`,
  `MovieAPI`, and wired them into `MainWindow.closeEvent()`. The page is now
  explicitly deleted before its profile, eliminating the "Release of profile
  requested but WebEnginePage still not deleted" warning and the segfault.
- Fixed `_update_toolbar_badges` bottleneck (317ms -> <10ms for 74 movies).
  Added `check_organized(settings=None)` method to `Movie` so callers can pass
  pre-loaded settings. The badge loop now loads settings YAML once instead of
  per-movie, and caches the `is_organized` result to avoid a duplicate call.
- Fixed media probe UI freeze (~5s for 74 movies). Removed `processEvents()`
  call from `_on_probe_task_progress` and reduced table refresh frequency from
  every 5 files to every 25 files, letting Qt repaint asynchronously.
- Replaced verbose per-step `[SCAN-TIMER]` instrumentation with concise
  `[scan]` and `[probe]` summary lines: scanner reports movie/dir count and
  wall time, finalize reports its duration and total scan-to-done time, and
  media probe reports probed/skipped counts with total and per-file averages.

- Fixed job timer not stopping on completion in the jobs dialog. Added `completed_at`
  timestamp to `task_api.py` `_on_finished()` and `_on_error()` methods. Updated
  `jobs_dialog.py` `_refresh()` to use `completed_at` instead of `now` for elapsed
  time calculations on finished jobs, so Queued and Active columns freeze at final values.
- Fixed `FakeTransport` test mock in `test_imdb_browser_transport.py` to include
  `_fetch_start`, `_load_finished_fired`, and `_timeout_stage_label` attributes
  added by the diagnostic logging changes.
- Replaced hardcoded `/tmp` path in `task_api.py` error log with `tempfile.gettempdir()`
  to satisfy bandit B108 security check.
- Fixed `_-` separator collision in movie filenames when `spaces_to_underscores` is enabled.
  `shell_safe_filename()` is now applied to each template token value individually before
  substitution instead of on the fully-assembled string. This preserves template separators
  (hyphens, dots) so `{title}-{year}` produces `After_the_Hunt-2025` instead of
  `After_the_Hunt_2025_`.
- Fixed UI unresponsiveness during directory scan by batching `partial_result` signals
  in `MainWindow`. Incoming movies are now buffered and flushed every 1000ms via a `QTimer`
  instead of triggering one `beginInsertRows`/`endInsertRows` cycle per movie. The event
  loop can now process clicks, sorts, and scrolling while the scan is in progress.
- Added chunked insertion to `_flush_scan_batch()` in `main_window.py`. Each flush now
  inserts movies in chunks of 50 with `QTimer.singleShot(0, ...)` between chunks, yielding
  to the event loop so the UI stays responsive during large batch inserts. Extracted
  `_finalize_scan()` from `_on_scan_done()` so post-scan cleanup (re-enable sorting, update
  status, start media probe) runs after all chunked inserts have drained.
- Further reduced scan-time UI lag with three additional fixes: (1) throttled progress
  signal emission to at most once per 500ms so `os.walk` subdirectory callbacks no longer
  flood the main-thread event queue, (2) disabled table sorting during scan to avoid an
  O(N log N) re-sort on every batch flush, re-enabling it once on scan completion, and
  (3) added `set_sorting_enabled()` to `MoviePanel` to toggle interactive sorting.

- Fixed `_fetch_parental_guides()` using all movies instead of only the checked ones. When
  movies were checked but none passed the `scraped and imdb_id` filter, the fallback incorrectly
  queried all movies. Now the fallback to all movies only triggers when no movies are checked.
- Fixed rename settings (resolution, video codec, audio codec, channels checkboxes) being ignored
  during actual renames. `MovieAPI.rename_movie()` now calls `build_file_template()` to assemble
  the file template with media tokens, matching the settings dialog preview behavior.
- Added missing `_stop_requested` mock to `FakeTransport` in
  `tests/test_imdb_browser_transport.py`, fixing 2 test failures
  (`test_transport_fetch_html_timeout`, `test_transport_fetch_html_load_failure`).
- Monkeypatched `QMessageBox.question` to return Yes in `TestMainWindowScan`
  and `TestMainWindowLastDirectory` in `tests/test_gui_smoke.py`, preventing
  the "quit anyway?" dialog from blocking teardown when background media probe
  is still running.

- Added `objectName("MainToolBar")` to the main toolbar in `main_window.py` so
  `saveState()` during `closeEvent` no longer crashes with `Trace/BPT trap: 5`.
- Added timeout cleanup to `imdb_browser_transport.py`: on timeout or load
  failure, navigate to `about:blank` to stop IMDB ad/tracker scripts that would
  otherwise crash the Chromium renderer (`Trace/BPT trap: 5`). Worker threads
  use a `_stop_requested` signal to safely invoke navigation on the main thread.
- Fixed `StatusIconDelegate` column range in `moviemanager/ui/movies/movie_panel.py` from
  `range(4, 9)` to `range(5, 10)` so the Min (duration) column no longer gets an icon delegate
  that paints nothing. Similarly fixed `SeverityDelegate` range from `range(9, 14)` to
  `range(10, 15)` to align PG severity columns correctly.
- Fixed `locked_columns` sets in `movie_panel.py` from `{1, 4, 5, 6, 7, 8}` to `{1, 5, 6, 7, 8, 9}`
  so the Trailer column (index 9) is locked and the Min column (index 4) can be hidden.
- Probe results are now auto-saved to existing NFO files after background probing
  (`moviemanager/core/media_probe.py`). Subsequent scans load cached `<fileinfo><streamdetails>`
  from NFO and skip re-probing, improving scan performance.

- Fixed `_get_duration_minutes()` to prefer probe duration but fall back to NFO runtime instead
  of returning 0 when no probe data exists (`moviemanager/ui/movies/movie_table_model.py`).
- Fixed `probe_movie_list()` variable scoping: changed from collecting bare MediaFile objects to
  `(movie, mf)` pairs so `movie.runtime` update references the correct movie
  (`moviemanager/core/media_probe.py`).

- Scanner now skips video files with "trailer" in the filename stem (e.g. `movie-trailer.mkv`,
  `trailer.mp4`). Prevents trailers from appearing as standalone movie entries in the table
  (`moviemanager/core/movie/scanner.py`).
- Added common video/audio file extensions (`mp4`, `mkv`, `avi`, `mov`, `m4v`, `webm`, `wmv`,
  `mpg`, `mpeg`, `m2ts`, `vob`, `aac`, `flac`, `mp3`) and common release tags (`hybrid`, `yts`,
  `lt`) to the filename parser STOPWORDS list. Prevents file extensions from leaking into parsed
  movie titles when filenames contain embedded extensions (e.g. `Jay_Kelly.mp4_2025.mp4` now parses
  as "Jay Kelly" instead of "Jay Kelly mp4") (`moviemanager/core/constants.py`).
- Fixed organize button moving files OUT of multi-movie directories (e.g. TODO_MOVIES) into the
  parent directory. Now creates the subfolder inside the multi-movie directory when
  `multi_movie_dir` is True (`moviemanager/core/movie/renamer.py`).
- Fixed artwork collector missing video-basename-prefixed artwork files (e.g.
  `Movie.Name-poster.jpg`, `Movie.Name.fanart.jpg`) in multi-movie directories. The collector
  now matches both exact artwork names and prefixed variants (`moviemanager/core/movie/renamer.py`).
- Fixed `is_organized` property using a loose title substring match that would incorrectly mark
  misnamed folders as organized (e.g. `Anaconda_blah_2025`). Now compares the folder name exactly
  against the expanded path template from settings (`moviemanager/core/models/movie.py`).
- Moved `task_api.py` from `moviemanager/api/` to `moviemanager/ui/` because it depends on PySide6
  and violates the rule that `api/` must not import Qt. Fixes `test_no_pyside6_in_core.py` failure.
- Fixed `FakeTransport` in `tests/test_imdb_browser_transport.py` to include all attributes
  referenced by bound methods: `_fetch_done`, `_navigating_away`, `_lock`. Added `_bind_fetch_methods()`
  helper to bind all fetch methods at once. Tests now use the worker-thread path directly to avoid
  QEventLoop conflicts when a QApplication exists from other tests.
- Added `RuntimeError` guards to `ImageDownloadWorker.run()` signal emissions
  (`moviemanager/ui/workers.py`). The `Worker` class already had these guards but
  `ImageDownloadWorker` did not, causing sporadic "Signal source has been deleted" errors when a
  dialog closes while a download worker is still running.
- Fixed `restore_table_state()` to force locked columns (Title + Mtch/Org/Art/Sub/Trl) visible
  after both `restoreState()` and the visibility list restore. Stale QSettings from before the
  column rename (D/N to Mtch/Org) were hiding the new status columns on startup.

- Updated `tests/test_gui_smoke.py` assertions to match new default template format
  (`The_Dark_Knight-2008` instead of `The Dark Knight (2008)`).

- Fixed prematch view not showing for NFO-loaded movies. `_merge_nfo_into_movie()` in
  `scanner.py` now sets `movie.scraped = True` when the NFO provides an external ID (`imdb_id` or
  `tmdb_id`). Previously the `scraped` flag stayed `False` after NFO loading, so the movie chooser
  never showed the "Existing Match" card with Keep/Re-match options for previously matched movies.
- Fixed prematch poster not loading for NFO-loaded movies. `_merge_nfo_into_movie()` was not
  copying `poster_url` or `fanart_url` from the parsed NFO data, so the prematch card had no URL
  to download from. Also updated `_get_movie_poster_path()` in `movie_chooser.py` to check for
  standard `poster.jpg` first before falling back to movie-specific cache path.
- Fixed segfault when clicking Accept Match in movie chooser. The QWebEnginePage continued
  executing IMDB ad/tracker JavaScript after HTML extraction, eventually crashing the Chromium
  renderer process. Now navigates to `about:blank` after extracting HTML to stop all scripts.
- Fixed deadlock when auto-match or main-thread code called `fetch_html()` on the IMDB browser
  transport. The signal+`threading.Event` pattern only works from worker threads. Added
  `QEventLoop`-based main-thread path that detects caller thread automatically.
- Fixed race condition in batch mode where multiple background scrape workers shared one
  transport instance. Concurrent `fetch_html()` calls corrupted shared state. Added
  `threading.Lock` to serialize concurrent calls.
- Fixed batch hang at end of movie chooser queue. Replaced background scrape worker with
  synchronous main-thread scrape using `QEventLoop`-based `fetch_html()`. Removed
  `_pending_scrape_count` and `_is_last_movie_scraping` tracking since scrapes complete
  before the dialog advances.

- Fixed GUI crash on launch (Bus error / QPainter segfault) caused by
  `_on_scan_progress_callback()` in `main_window.py` directly calling GUI
  widget methods from the scanner worker thread. Changed to emit the worker's
  `signals.progress` signal instead, which marshals the update to the main
  thread via Qt's signal-slot mechanism.
- Fixed segfault when clicking Accept Match in the movie chooser dialog.
  The scrape worker thread called `_ensure_imdb_transport()` which created
  `QWebEngineProfile` and `QWebEnginePage` from a non-main thread. Added
  eager `get_imdb_transport()` call in `_start_scrape_worker()` on the main
  thread before launching the worker, so the transport already exists when
  the worker runs.
- Fixed batch match count including in-flight "pending" scrapes as matched by
  using `is True` check instead of truthiness (which counted `"pending"` strings).
- Fixed progress bar showing current position instead of completed count in batch
  mode. Now uses `self._current_index` (0-based completed) instead of `pos`
  (1-based current).
- Added failed scrape count display in batch mode match count label (e.g. "3
  matched, 1 failed") in both `_on_scrape_done()` and `_on_scrape_error()`.
- Added Escape key tooltip to Skip/Cancel buttons for discoverability.
- Removed GraphQL queries (`_METADATA_QUERY`, `_SEARCH_QUERY`,
  `_PARENTAL_GUIDE_QUERY`) and `_fetch_graphql()` from `imdb_scraper.py`.
  Replaced with CDN suggestion API for search and HTML parsing for metadata.
- Removed `curl_cffi` dependency from `imdb_scraper.py`. The scraper now uses
  `requests` for the CDN suggestion API (no TLS fingerprinting needed) and
  `QWebEnginePage` transport for HTML page loads.
- Updated `_retry_after_imdb_challenge()` in `MovieChooserDialog` to use the
  shared transport profile when available, so cookies from challenge solving
  persist in the transport's profile.

- Fixed unreadable Match column in search results table: pastel background colors
  (light green/yellow/pink) made white-on-light text invisible in dark themes.
  Now sets black foreground text on all colored confidence cells.
- Fixed blank entries appearing in TMDB search results. The TMDB API can return
  items with no title; `tmdb_scraper.py` now skips results where both `title`
  and `original_title` are empty.
- Fixed `api_cache.py` crash during `json.dump` when scraper results contain
  non-JSON-serializable objects (e.g., `tmdbv3api` `AsObj` bound methods).
  Added a `default` handler to `json.dump` that converts non-serializable
  objects to `str()` and logs a warning instead of crashing the UI.
- Fixed `tmdb_scraper.py` `AttributeError` crash where `tmdbv3api` `AsObj`
  objects returned bound methods instead of strings via `getattr()`. Added
  `_safe_str()` helper that detects callable non-string values and returns
  the fallback. Applied to all string field extractions in `search()` and
  `get_metadata()` to prevent non-data types from leaking into dataclasses.
- Added validation guards in `movie_api.py` to only cache non-empty search
  results, metadata with meaningful content (title or imdb_id), and non-empty
  parental guide data. Prevents caching error/empty responses that may contain
  non-serializable objects.
- Fixed batch mode premature close in `MovieChooserDialog`: the `_on_scrape_done()`
  callback unconditionally called `self.accept()`, closing the dialog when ANY
  background scrape finished even if the user was still working on later movies.
  Now tracks in-flight scrapes with `_pending_scrape_count` and only closes when
  the last movie's scrape completes. Non-last movie scrape errors are silently
  recorded instead of showing disruptive popups mid-batch.
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
- When poster image decode fails in `ImageLabel` (including Qt allocation-limit
  rejects), the app now prints the source poster URL to CLI for direct debugging.
- IMDB provider now prefers TMDB poster URLs by default (when a TMDB API key is
  configured): top search results are rewritten to TMDB poster URLs, and scrape
  metadata poster URLs are replaced with the TMDB poster when an imdb_id match exists.
- Added a hard decode cap for artwork images: `ImageLabel` now constrains source
  images so the largest dimension is at most 4096 pixels before creating the pixmap,
  preventing Qt allocation-limit failures on oversized posters.

### Removals and Deprecations

- Removed the free-form "File Template" text field from Settings > Renamer tab.
  File templates are now hardcoded as `{title}{sep}{year}` plus any enabled media
  tokens, all joined by the configured separator. This prevents users from
  introducing shell-unsafe literal characters (spaces, parens) that conflict with
  shell-safe mode. The `file_template` field was also removed from the Settings
  dataclass and YAML persistence. The `--template` CLI flag now only sets the
  path template.

### Developer Tests and Notes

- Added diagnostic logging to `imdb_browser_transport.py` fetch pipeline: each stage
  (fetch start, loadFinished, toHtml callback, event loop exit) now logs with elapsed
  time via `time.monotonic()`. Timeout error messages now indicate which stage stalled
  ("loadFinished never fired" vs "toHtml callback never returned") to help diagnose
  WAF blocking, renderer crashes, and Qt event loop starvation.

- Added 8 new tests in `tests/test_renamer.py` for `shell_safe_filename()` covering ampersands,
  apostrophes, double quotes, parentheses, unicode, dots/hyphens, leading/trailing cleanup, and
  template expansion with shell-safe mode.

- Added `TestChooserDialogPrematchMode` test class to `tests/test_gui_smoke.py`
  with 4 tests: prematch view shown for scraped movie, keep match in single mode,
  rematch switches to search, return to prematch.
- Added `TestChooserDialogBatchBugFixes` test class with 2 tests: pending scrapes
  not counted as matched, progress bar starts at zero.
- Rewrote `tests/test_scraper_imdb.py` with 41 tests covering: CDN suggestion
  API parsing (filtering, poster URLs, scores, empty results), `__NEXT_DATA__`
  extraction, metadata HTML parsing (all fields, empty HTML, empty data), cast
  extraction, principal credits, producers, studio, parental guide HTML parsing
  (primary and fallback paths), advisory ID mapping, keyword extraction, top250
  handling, transport integration (requires transport, mock transport), and
  parental guide transport integration.
- Created `tests/test_imdb_browser_transport.py` with 11 tests covering: module
  import, User-Agent validation (no QtWebEngine/HeadlessChrome), storage dir,
  method existence, fetch timeout, fetch load failure, HTML received event,
  load finished failure/success, CAPTCHA detection, and normal page (no signal).
- Rewrote `tests/test_scraper_imdb_live.py` with 5 CDN suggestion API live tests
  (search, IMDB ID verification, type filtering, poster URLs, empty query). Removed
  metadata and parental guide live tests that required QWebEnginePage transport with
  a Qt event loop -- those are covered by mocked unit tests in `test_scraper_imdb.py`.
- Created `moviemanager/api/api_cache.py` with persistent JSON-file caching for API
  metadata responses. Uses 6 cache files under `~/.cache/movie_organizer/` (IMDB/TMDB
  search, metadata, parental guide, poster lookup) with a 182-day TTL. Features atomic
  writes via temp file + rename, automatic expired entry purging, case-insensitive key
  normalization, and graceful corrupt JSON recovery.
- Integrated `ApiCache` into `MovieAPI` in `moviemanager/api/movie_api.py`: search
  results, metadata, parental guide, and TMDB poster lookups are now cached persistently.
  Repeated test runs and scrape operations avoid redundant HTTP requests to IMDB/TMDB.
  Metadata is keyed by `imdb_id` for both scrapers since TMDB returns IMDB IDs.
- Added `tests/test_api_cache.py` with 21 unit tests covering round-trip serialization,
  TTL expiration, cache miss behavior, key normalization, clear/remove operations,
  corrupt JSON handling, and automatic directory creation.
- Created `moviemanager/api/match_confidence.py` with API-agnostic Bayesian-inspired
  match confidence scoring. Uses four weighted signals: title similarity (0.50 weight
  via `difflib.SequenceMatcher`), year proximity (0.25 weight via Gaussian bell curve
  with sigma=2), token overlap (0.15 weight via Jaccard similarity), and popularity
  prior (0.10 weight from provider rating). Includes exact-match bonus and low-similarity
  clamp. Works with plain strings/floats, no scraper type dependencies.
- Added `match_confidence` field to `SearchResult` dataclass in
  `moviemanager/scraper/types.py` for storing computed match scores.
- Updated `MovieAPI.search_movie()` to compute match confidence for each result and
  sort results by confidence descending, so the best match is always first.
- Renamed "Rating" column to "Match" in the movie chooser results table, now displaying
  confidence percentages with color coding (green >= 70%, yellow 40-69%, red < 40%).
- Added pre-match view to `MovieChooserDialog`: when a movie already has scraped
  metadata, the dialog shows existing match info (title, year, IDs, rating, director,
  genres, certification, runtime, poster) with "Keep Match" and "Re-match" buttons
  instead of immediately searching. "Keep Match" advances without re-scraping;
  "Re-match" switches to normal search mode.
- Added TMDB-primary scraper mode with IMDB parental guide supplement:
  `MovieAPI._ensure_scraper()` now auto-detects TMDB when a TMDB API key
  is configured, using TMDB for search and metadata with IMDB GraphQL as
  a supplement for parental guide data only. Falls back to IMDB-only when
  no TMDB key is available.
- Added `_PARENTAL_GUIDE_QUERY` GraphQL constant and `get_parental_guide()`
  method to `ImdbScraper` for fetching only parental guide severity data
  without pulling full movie metadata.
- Added parental guide supplement logic in `MovieAPI.scrape_movie()`: when
  using TMDB as the primary scraper and the metadata lacks parental guide
  data, the IMDB supplement scraper fetches it automatically.
- Updated `_apply_configured_imdb_browser_cookies()` to apply browser
  cookies to both the primary IMDB scraper and the IMDB supplement scraper.
- Rebuilt IMDB scraper from scratch using IMDB's GraphQL API
  (`graphql.imdb.com`) instead of HTML scraping. The GraphQL endpoint
  currently bypasses AWS WAF challenges that blocked all HTML endpoints.
- New `moviemanager/scraper/imdb_scraper.py` fetches full movie metadata
  (title, year, rating, votes, runtime, certification, genres, cast with
  character roles, director, writer, studio, countries, languages, tagline,
  keywords, parental guide, poster URL, top250 rank) in a single GraphQL
  request per movie.
- New `moviemanager/scraper/browser_cookies.py` loads IMDB cookies from
  Firefox profiles by reading `cookies.sqlite` via temp-copy to avoid
  WAL lock conflicts with running Firefox.
- New `moviemanager/ui/dialogs/imdb_challenge_dialog.py` provides an
  embedded QWebEngineView dialog for solving WAF challenges manually
  when the GraphQL endpoint gets blocked.
- Search filters results to Movie/Short/TV Movie types, excluding
  TV episodes and podcasts from search results.
- WAF detection: any HTTP 202 from GraphQL raises `ConnectionError` with
  "AWS WAF challenge" text, triggering the existing challenge dialog flow.

- Created `tests/test_match_confidence.py` with 12 tests covering: exact match,
  year off-by-1, article normalization, different titles, token reorder, missing
  year, popularity tiebreaker, original title matching, empty titles, score bounds,
  internal `_normalize_title()`, and Gaussian `_year_proximity()` bell curve.
- Added 3 unit tests for `get_parental_guide()` method in `tests/test_scraper_imdb.py`:
  mocked GraphQL response parsing, empty IMDB ID handling, and null guide data handling.
  Test suite now has 32 tests.
- Added `tests/test_scraper_imdb.py` with 29 unit tests covering GraphQL metadata
  parsing, search result filtering, parental guide extraction, cast/producer mapping,
  WAF detection, poster URL cleanup, cookie injection, and top250 handling.
- Added `tests/test_browser_cookies.py` with 8 unit tests covering Firefox profile
  discovery, cookie database reading with IMDB domain filtering, unsupported browser
  rejection, and full pipeline integration.
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
