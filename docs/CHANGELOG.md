# Changelog

## 2026-03-03

### Additions and New Features
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

### Behavior or Interface Changes
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

### Fixes and Maintenance
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

### Additions and New Features
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

### Behavior or Interface Changes
- Jobs dialog now refreshes every 1 second via a `QTimer` so the elapsed time
  column stays current while jobs are running. Timer stops when the dialog is
  hidden or closed (`moviemanager/ui/dialogs/jobs_dialog.py`).

### Fixes and Maintenance
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

### Additions and New Features
- Added `shell_safe_filename()` to `moviemanager/core/utils.py` using a whitelist approach modeled
  on `rmspaces.py`: transliterates unicode to ASCII via `unidecode`, replaces `&` with `and`,
  replaces quotes with underscores, and strips any character not in `-./_0-9A-Za-z`.

### Behavior or Interface Changes
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

### Developer Tests and Notes
- Added 8 new tests in `tests/test_renamer.py` for `shell_safe_filename()` covering ampersands,
  apostrophes, double quotes, parentheses, unicode, dots/hyphens, leading/trailing cleanup, and
  template expansion with shell-safe mode.

### Additions and New Features
- Added `<fileinfo><streamdetails>` read/write support to NFO reader and writer
  (`moviemanager/core/nfo/reader.py`, `moviemanager/core/nfo/writer.py`). Caches probe results
  (video codec, resolution, aspect ratio, duration, audio codec, channels) in NFO files using
  standard Kodi format. On subsequent scans, cached data is loaded from NFO, avoiding re-probing.
- Scanner now populates video MediaFile fields from NFO `<fileinfo>` data during merge
  (`moviemanager/core/movie/scanner.py`). Files with cached probe data skip pymediainfo probing.
- `probe_movie_list()` now sets `movie.runtime` from probe duration when runtime is not already
  set by NFO metadata (`moviemanager/core/media_probe.py`).

### Behavior or Interface Changes
- Min column now falls back to NFO/scraped `movie.runtime` when probe duration is unavailable
  (`moviemanager/ui/movies/movie_table_model.py`). Previously the column was empty until probing
  completed; now scraped movies show runtime immediately on scan.
- Media probe now uses `TaskAPI.submit_job()` instead of raw `QThreadPool`, so it appears in the
  Jobs dialog with proper progress tracking and error handling (`moviemanager/ui/main_window.py`).

### Fixes and Maintenance
- Fixed `_get_duration_minutes()` to prefer probe duration but fall back to NFO runtime instead
  of returning 0 when no probe data exists (`moviemanager/ui/movies/movie_table_model.py`).
- Fixed `probe_movie_list()` variable scoping: changed from collecting bare MediaFile objects to
  `(movie, mf)` pairs so `movie.runtime` update references the correct movie
  (`moviemanager/core/media_probe.py`).

### Additions and New Features
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

### Behavior or Interface Changes
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

### Additions and New Features
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

### Fixes and Maintenance
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

### Behavior or Interface Changes
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

### Fixes and Maintenance
- Updated `tests/test_gui_smoke.py` assertions to match new default template format
  (`The_Dark_Knight-2008` instead of `The Dark Knight (2008)`).

### Previous additions
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

### Behavior or Interface Changes
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

### Behavior or Interface Changes
- Rating column in the movie table now displays one decimal place (e.g., "7.3" instead of "7.258")
  for cleaner, more consistent formatting.
- Movie editor dialog now shows the poster image alongside the metadata form. Poster is displayed
  on the left side of the dialog, loaded from the movie's `poster_url` or `poster.jpg` in the
  movie directory.
- IMDB ID and TMDB ID fields in the movie editor now have "Open" buttons that launch the
  corresponding IMDB or TMDB page in the default browser. Buttons are disabled when no ID is set.

### Fixes and Maintenance
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

### Additions and New Features
- Created [docs/NFO_FILE_FORMAT.md](docs/NFO_FILE_FORMAT.md) documenting the Kodi NFO XML
  file format. Covers tag reference table, full sample NFO, reader/writer implementation
  details, combination NFO behavior, round-trip element preservation, and differences from
  the modern Kodi v17+ format. Includes parental guide custom extension documentation.
- Created `moviemanager/ui/format_movie.py` with pure formatting functions for movie
  metadata display. Consolidates duplicated `int->str` / `float->str` conversion logic
  from `MovieDetailPanel.set_movie()` and `MovieChooserDialog._show_prematch_view()` into
  shared functions: `format_rating()`, `format_genres()`, `format_runtime()`, `format_ids()`,
  and `format_movie_fields()`. Added `tests/test_format_movie.py` with 13 tests.

### Behavior or Interface Changes
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
- Created [docs/WAF_CHALLENGES.md](docs/WAF_CHALLENGES.md) documenting how AWS WAF
  JavaScript challenges work, why curl_cffi and cookie transfer fail, how the app
  handles WAF via QWebEnginePage transport, the thread bridging pattern, and the
  CAPTCHA fallback flow.

### Behavior or Interface Changes
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

### Fixes and Maintenance
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

### Developer Tests and Notes
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

### Fixes and Maintenance
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

### Behavior or Interface Changes
- `MovieAPI.compute_match_confidence()` now delegates to the standalone
  `moviemanager.api.match_confidence` module instead of using its own inline logic.
  The static method signature is preserved for backward compatibility.
- `_batch_scrape_unscraped()` in `main_window.py` now uses pre-computed
  `best.match_confidence` from search results instead of calling
  `MovieAPI.compute_match_confidence()` separately.
- TMDB scraper selection is now automatic based on API key presence; the
  `scraper_provider` setting is no longer checked. TMDB key exists = TMDB primary.

### Developer Tests and Notes
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
