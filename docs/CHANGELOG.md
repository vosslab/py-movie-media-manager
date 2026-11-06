# Changelog

## 2026-11-06

### Fixes and Maintenance

- Updated the GUI screenshot launcher with bounded capture attempts, process-specific cleanup,
  temporary PNG processing, and quality-90 WebP output capped at a 1920-pixel edge.
- Verified a native 1200x843 WebP capture (73 KB). Automatic window sizing was unavailable;
  retained the app's dimensions. Capture evidence stayed temporary because this update targets
  the launcher rather than a managed README or documentation screenshot block.
- Reviewed runtime dependencies: removed unused Pillow and tabulate, synchronized unidecode
  in package metadata, and declared MediaInfo, yt-dlp, and FFmpeg in the macOS Brewfile.
- Clarified system-library and trailer-tool installation requirements; retained the managed
  shared development dependency block and the required pytest-qt plugin.
- Began repository modernization: repaired changelog structure, removed obsolete maintenance tools, and updated code and test standards.
- Rotated prior dated history into `CHANGELOG-2026-03a.md` and `CHANGELOG-2026-02a.md`.
- Split movie matching by responsibility: `MovieChooserDialog` now coordinates prematch,
  navigation, and scraping; `MovieSearchPane` owns query, result, and preview state; and
  `MovieSearchPrefetch` owns cancellable next-movie caches.
- Refreshed the remaining documentation audit: documented jobs queue control, corrected
  the parental-guide scraper reference, and labeled the original Python port plan as
  historical context rather than a current roadmap.

## 2026-03-04

### Additions and New Features

- Wired ARTWORK providers into the scraper pipeline. `FanartScraper` is now added as a supplement
  in `create_pipeline()` when a `fanart_api_key` is configured. Added `get_artwork_providers()`
  to `ProviderPipeline` for targeted artwork provider access.
- Added artwork supplement step to `ScrapeService.scrape_movie()`: after metadata fetch, calls
  `get_artwork()` on each artwork provider and fills in missing URL fields (poster, fanart,
  banner, clearart, logo, discart, thumb) without overwriting existing URLs.
- Added `_apply_metadata_to_movie()` fields for banner, clearart, logo, and discart URLs so
  metadata from TMDB or other providers propagates to the Movie object.
- Replaced `_has_poster_cache` with `_artwork_types_cache` (set of artwork type strings) on the
  Movie model. Added `has_fanart` and `artwork_types_on_disk` properties for checking any artwork
  type presence.
- Rewrote `ArtworkService.download_artwork()` to iterate over all enabled artwork types (poster,
  fanart, banner, clearart, logo, discart) using a download map, instead of only poster and fanart.
- Fixed `DownloadController._build_download_tasks()` artwork gating: now checks all enabled artwork
  types via `artwork_types_on_disk` instead of only `has_poster`.
- Updated `MovieTableModel.check_no_artwork()` to check all enabled artwork types, not just poster.
- Three-color artwork status dot in the GUI: green (all enabled types present), yellow (some
  present), red (none present). Added tooltip breakdown listing each enabled artwork type and
  its presence. Settings-aware via `MovieTableModel.set_settings()`.

- Added pause/resume for the job queue. New `TaskAPI.pause()` and `resume()` methods hold
  submitted workers in a pending queue instead of starting them, while already-running jobs
  complete normally. Pause toggle button added to both the status bar and the Jobs dialog.
- Added `SubtitleService.shutdown()` to log out from OpenSubtitles on application exit, freeing
  JWT tokens and server resources per API docs.
- Added `MovieDetailPanel.shutdown()` to cancel in-flight image workers and drain the panel's
  private `QThreadPool` during application close.
- Added `MoviePanel.shutdown_detail_panel()` bridge method so `MainWindow` can call through to
  the detail panel's shutdown without reaching into internal panel structure.
- Added "Cancel Job" button to the Jobs dialog, wired to the existing `_cancel_selected()` method
  which now also handles jobs with "queued" status (previously only "running").
- Added "Pause All" / "Resume All" toggle button to the Jobs dialog with state synced to `TaskAPI`.
  Queued jobs show "Paused" status text when the queue is paused.

- Split IMDB parental guide into a dedicated scraper:
  [moviemanager/scraper/imdb_parental_guide_scraper.py](../moviemanager/scraper/imdb_parental_guide_scraper.py)
  with `ImdbParentalGuideScraper(ParentalGuideProvider)`. Uses IMDB GraphQL API via curl_cffi
  as primary transport, falls back to QWebEnginePage browser transport for HTML parsing.
  Registered as "imdbparentalguide" in the scraper registry with `capabilities = {PARENTAL_GUIDE}`.
- `ImdbScraper` now handles only SEARCH and METADATA capabilities; parental guide functionality
  moved to `ImdbParentalGuideScraper`.

### Behavior or Interface Changes

- Improved `MainWindow.closeEvent()` shutdown sequence: now drains the task pool first, then the
  detail panel image pool, then calls `MovieAPI.shutdown()` which logs out from subtitle service
  before tearing down the IMDB browser transport.
- Extended `MovieAPI.shutdown()` to call `SubtitleService.shutdown()` before IMDB transport
  teardown, ensuring subtitle JWT logout happens while the network stack is still available.

- `MainWindow` reduced from 1,872 to ~1,056 lines. Now a thin shell that creates four controllers
  (`ScanController`, `MatchController`, `RenameController`, `DownloadController`) in `__init__`,
  wires their signals to UI update slots, and keeps only window setup, menu/toolbar creation,
  signal wiring, and simple UI update slots. All workflow logic moved to controllers. GUI behavior
  is unchanged.
- `moviemanager.core.utils.is_video_file()` now delegates to
  `moviemanager.core.file.classifier.is_video_file()`.
- `moviemanager.core.models.movie.Movie.has_subtitle` and `has_trailer` properties now
  use classifier functions instead of inline extension checks.
- Removed unused `os` import from `moviemanager/core/utils.py`.
- `MovieAPI` is now a thin composition root (~200 lines of delegation) that creates and
  delegates to `TrailerService`, `ArtworkService`, `SubtitleService`, `ScanService`,
  `SearchService`, and `ScrapeService`. All public method signatures remain unchanged.
  Scraper lifecycle (`_ensure_scraper`, `_ensure_imdb_transport`) and IMDB cookie management
  remain in MovieAPI.

- `ImdbScraper` now inherits from both `MetadataProvider` and
  `ParentalGuideProvider` (previously only `MetadataProvider`). The
  `get_parental_guide` method was already present; this formalizes the interface.
- `MovieAPI._ensure_scraper()` now uses `ScraperRegistry.create_pipeline()` to
  select providers instead of direct class imports. Behavior is identical: TMDB
  primary with IMDB supplement when tmdb_api_key is set, IMDB-only fallback
  otherwise.
- `TrailerService` now accepts an optional `provider` parameter (TrailerProvider
  instance) instead of embedding yt-dlp logic inline. Defaults to
  `YtdlpTrailerProvider` when no provider is given.
- `SubtitleService` now accepts an optional `provider` parameter (SubtitleProvider
  instance). When given, skips internal scraper creation and uses the injected
  provider directly. Falls back to internal settings-based creation when None.
- `MovieAPI` now resolves trailer and subtitle providers from
  `ProviderPipeline.get_for_capability()` and injects them into `TrailerService`
  and `SubtitleService`. `YtdlpTrailerProvider` is auto-discovered with no API
  keys required; `SubtitleScraper` is discovered when `opensubtitles_api_key`
  is configured.
- `ProviderPipeline.create_pipeline()` now adds trailer and subtitle providers
  as supplements alongside metadata providers.

### Fixes and Maintenance

- Extracted `toolbar_builder.py` from `main_window.py`: moved the 200-line `_setup_toolbar()`
  body into a standalone `build_toolbar(window)` function following the existing `menu_builder.py`
  pattern. `MainWindow._setup_toolbar()` is now a 5-line stub.
- Extracted `task_dispatcher.py` from `main_window.py`: moved the 3 task routing methods
  (`_on_task_finished`, `_on_task_error`, `_on_task_progress`) into a `TaskDispatcher(QObject)`
  class. `MainWindow` creates the dispatcher after controllers and connects `TaskAPI` signals to it.
- Extracted `PrematchWidget(QFrame)` from `movie_chooser.py` into
  `moviemanager/ui/widgets/prematch_widget.py`. Moves prematch card construction, poster download,
  and poster cache logic out of the dialog. Emits `rematch_requested` signal for the "Find Different
  Match" button.
- Extracted `BatchNavigator` from `movie_chooser.py` into
  `moviemanager/ui/dialogs/batch_navigator.py`. Pure Python class (no Qt dependency) managing batch
  traversal state: movie list, current index, and per-movie results. `MovieChooserDialog` delegates
  all index/state queries to it.
- Net result: `main_window.py` reduced from 1,083 to 810 lines (-25%),
  `movie_chooser.py` from 1,192 to 997 lines (-16%). No behavior changes.

- Fixed `TmdbScraper.get_metadata()` to resolve `tmdb_id` from `imdb_id` via `find_by_imdb_id()`
  when only an IMDB ID is available. Previously crashed with "The resource you requested could
  not be found" when movies matched with IMDB were re-scraped after switching to TMDB primary.
- Fixed `create_pipeline()` in registry to respect the `settings.scraper_provider` preference.
  Previously always used TMDB as primary when a TMDB API key existed, ignoring the user's
  IMDB selection in Settings. Now defaults to IMDB and only uses TMDB when explicitly chosen.
- Fixed pipeline to add TMDB as a supplement for artwork when IMDB is the primary scraper and
  a TMDB API key is available. Previously IMDB-primary mode lost all TMDB artwork capability.
- Added `logout()` method to `SubtitleScraper` (sends DELETE to `/logout` to free server
  resources per API docs).
- Added `Accept: */*` header to OpenSubtitles API requests as required by API docs.
- Added `quota_exceeded` category to `DownloadCategory` enum and specific 406 handling
  in subtitle downloads. Shows a clear "daily download quota exhausted" message instead of
  a raw HTTP error when the 20/day free-account limit is hit (resets midnight UTC).
- Improved subtitle download error messages to include the API response body for diagnostics.
- Added comprehensive error handling for all OpenSubtitles HTTP error codes: 401 (re-auth),
  406 (quota/invalid token/invalid file_id), 410 (expired link), 429 (rate limit).
  Session-level quota flag prevents further API requests after 406 quota or 429 rate limit.
- Updated [docs/OPENSUBTITLES_COM_API.md](OPENSUBTITLES_COM_API.md) with full error
  codes reference, rate limits, best practices, performance tips, and implementation notes.
- Fixed pre-existing bandit B108 warning in `tests/test_template_engine.py` (hardcoded `/tmp`
  replaced with `tempfile.gettempdir()`).
- Fixed OpenSubtitles 401 on subtitle downloads. Root cause: the pipeline-injected
  `SubtitleScraper` was created with only an API key but never authenticated (login was
  skipped because `_external_provider is not None`). Added `_ensure_provider_logged_in()`
  to authenticate injected providers before first download. Also added JWT token freshness
  check (23h max age on 24h lifetime) and automatic retry on 401 during download.
- Fixed GUI smoke tests (`test_gui_smoke.py`) crashing on WebEngine segfault by mocking
  `MovieAPI._ensure_imdb_transport` in scrape tests alongside the existing scraper method mocks.
- Updated `scrape_service.py` to use `ParentalGuideProvider` interface for parental guide
  type checks instead of concrete `ImdbScraper` isinstance checks.
- Updated `movie_api.py` to use `hasattr(scraper, "set_transport")` duck typing for transport
  injection instead of `isinstance(scraper, ImdbScraper)` checks, and to find
  `ParentalGuideProvider` supplements via the interface.
- Updated registry pipeline construction to discover and add parental guide providers as
  supplements separately from metadata providers.
- Updated [tests/test_scraper_imdb.py](../tests/test_scraper_imdb.py) parental guide tests to
  reference the new `imdb_parental_guide_scraper` module.
- Updated [tests/test_scraper_registry.py](../tests/test_scraper_registry.py) to verify the
  split: IMDB no longer has PARENTAL_GUIDE capability, `imdbparentalguide` provider discovered.
  Added `scraper_provider` to `_make_settings()` defaults. Added
  `test_create_pipeline_imdb_primary_with_tmdb_supplement` test for IMDB primary with TMDB
  artwork supplement.
- Added `test_get_metadata_resolves_tmdb_id_from_imdb_id` and
  `test_get_metadata_returns_empty_when_no_ids` to
  [tests/test_scraper_tmdb.py](../tests/test_scraper_tmdb.py) to verify imdb_id resolution
  and graceful empty return.
- Extracted MainWindow workflow handlers into controller classes (Milestone 6):
  - [moviemanager/ui/controllers/scan_controller.py](../moviemanager/ui/controllers/scan_controller.py):
    `ScanController(QObject)` handles directory scanning, incremental movie delivery with batch
    buffering, post-scan finalization, background media probe for codec/resolution, and toolbar
    badge computation.
  - [moviemanager/ui/controllers/match_controller.py](../moviemanager/ui/controllers/match_controller.py):
    `MatchController(QObject)` handles interactive single/batch scrape via movie chooser dialog,
    batch auto-scrape with confidence scoring, metadata refresh with cache bypass, and parental
    guide fetching from IMDB.
  - [moviemanager/ui/controllers/rename_controller.py](../moviemanager/ui/controllers/rename_controller.py):
    `RenameController(QObject)` handles single and batch rename preview/execution, undo history
    stack, and error reporting.
  - [moviemanager/ui/controllers/download_controller.py](../moviemanager/ui/controllers/download_controller.py):
    `DownloadController(QObject)` handles batch artwork/trailer/subtitle downloads, per-movie
    content checks, subtitle credential validation, and batch completion tracking.
  - [moviemanager/ui/controllers/__init__.py](../moviemanager/ui/controllers/__init__.py): package
    docstring only, following `__init__.py` minimalism rules.
- Created [moviemanager/core/file/](../moviemanager/core/file/) package with file services layer:
  - [moviemanager/core/file/classifier.py](../moviemanager/core/file/classifier.py): centralized file
    type detection with `classify_file()`, `is_video_file()`, `is_subtitle_file()`,
    `is_artwork_file()`, `is_trailer_file()`, `is_nfo_file()`. Uses extension sets from constants.py.
  - [moviemanager/core/file/collector.py](../moviemanager/core/file/collector.py): directory-level file
    collection with `collect_artwork_files()`, `collect_artwork_file_paths()`,
    `collect_subtitle_files()`, `collect_trailer_files()`, `collect_nfo_files()`,
    `collect_all_movie_files()`. Merges scanner and renamer artwork collection logic.
  - [moviemanager/core/file/walker.py](../moviemanager/core/file/walker.py): directory traversal with
    `DirEntry` dataclass and `walk_movie_directories()` iterator. Extracts walk logic from scanner.
- Created [tests/test_file_classifier.py](../tests/test_file_classifier.py) with 55 parametrized tests.
- Created [tests/test_file_collector.py](../tests/test_file_collector.py) with 11 tests.
- Decomposed scanner and renamer into focused service modules (Milestone 2):
  - [moviemanager/core/movie/scan_service.py](../moviemanager/core/movie/scan_service.py): replaces
    scanner.py, composes DirectoryWalker, FileCollector, nfo.reader, and utils.parse_title_year()
    for directory scanning. Public API: `scan_directory()` and `detect_artwork_files()`.
  - [moviemanager/core/movie/template_engine.py](../moviemanager/core/movie/template_engine.py): pure
    template logic extracted from renamer.py with `expand_template()` and `build_file_template()`.
    No filesystem operations.
  - [moviemanager/core/file/mover.py](../moviemanager/core/file/mover.py): file movement operations
    extracted from renamer.py with `move_file()` (cross-device fallback) and
    `update_movie_paths()`.
  - [moviemanager/core/movie/rename_service.py](../moviemanager/core/movie/rename_service.py): replaces
    renamer.py, orchestrates TemplateEngine, FileCollector, and FileMover. Public API:
    `rename_movie()`.
- Created [tests/test_template_engine.py](../tests/test_template_engine.py) with 15 tests covering
  expand_template() and build_file_template() with various token combinations, empty fields,
  shell-safe mode, media tokens, and separator options.
- Decomposed MovieAPI god object into focused service classes (Milestone 4):
  - [moviemanager/api/trailer_service.py](../moviemanager/api/trailer_service.py): `TrailerService`
    with `download_trailer()`, wraps yt-dlp subprocess.
  - [moviemanager/api/artwork_service.py](../moviemanager/api/artwork_service.py): `ArtworkService`
    with `download_artwork()`, downloads poster and fanart images.
  - [moviemanager/api/subtitle_service.py](../moviemanager/api/subtitle_service.py): `SubtitleService`
    with `download_subtitles()` and thread-safe JWT auth lifecycle for OpenSubtitles.
  - [moviemanager/api/scan_service.py](../moviemanager/api/scan_service.py): API-level `ScanService`
    wrapping core scan_service and MovieList with `scan_directory()`, `get_movies()`,
    `get_unscraped()`, and count methods.
  - [moviemanager/api/search_service.py](../moviemanager/api/search_service.py): `SearchService`
    with `search_movie()`, `search_movie_with_fallback()`, TMDB poster lookup, and match
    confidence scoring.
  - [moviemanager/api/scrape_service.py](../moviemanager/api/scrape_service.py): `ScrapeService`
    with `scrape_movie()`, `fetch_parental_guides()`, `retry_failed_parental_guides()`, cache
    handling, IMDB parental guide supplement, and metadata-to-movie mapping.

### Removals and Deprecations

- Deleted `moviemanager/core/movie/scanner.py`, replaced by
  [moviemanager/core/movie/scan_service.py](../moviemanager/core/movie/scan_service.py).
- Deleted `moviemanager/core/movie/renamer.py`, replaced by
  [moviemanager/core/movie/template_engine.py](../moviemanager/core/movie/template_engine.py),
  [moviemanager/core/file/mover.py](../moviemanager/core/file/mover.py), and
  [moviemanager/core/movie/rename_service.py](../moviemanager/core/movie/rename_service.py).
- Updated imports in `moviemanager/api/movie_api.py` to use `scan_service`,
  `rename_service`, and `template_engine` instead of `scanner` and `renamer`.
- Updated `moviemanager/core/models/movie.py` `check_organized()` lazy import to use
  `template_engine.expand_template()` instead of `renamer.expand_template()`.
- Updated [tests/test_scanner.py](../tests/test_scanner.py) and
  [tests/test_renamer.py](../tests/test_renamer.py) imports to use new module paths.

- Added `ProviderCapability` enum to
  [moviemanager/scraper/interfaces.py](../moviemanager/scraper/interfaces.py) with values:
  SEARCH, METADATA, ARTWORK, PARENTAL_GUIDE, SUBTITLES, TRAILER.
- Added `ParentalGuideProvider` ABC to
  [moviemanager/scraper/interfaces.py](../moviemanager/scraper/interfaces.py) with abstract
  `get_parental_guide(imdb_id)` method.
- Created [moviemanager/scraper/registry.py](../moviemanager/scraper/registry.py) with
  `ScraperRegistry` (register, get_available, create_provider, create_pipeline) and
  `ProviderPipeline` (primary + supplements routing by capability).
- Added `build_default_registry()` auto-discovery function that scans
  `moviemanager/scraper/` for classes with a `capabilities` attribute using
  importlib + inspect, avoiding hardcoded imports.
- Added class-level `capabilities` sets to scrapers: TmdbScraper
  (SEARCH, METADATA, ARTWORK), ImdbScraper (SEARCH, METADATA),
  ImdbParentalGuideScraper (PARENTAL_GUIDE), FanartScraper (ARTWORK),
  SubtitleScraper (SUBTITLES).
- Added class-level `requires_keys` lists to all scrapers for registry-based
  availability filtering.
- Created [tests/test_scraper_registry.py](../tests/test_scraper_registry.py) with 14
  tests covering registration, capability filtering, settings key filtering,
  provider creation, pipeline creation, auto-discovery, and capability correctness.
- Added `TrailerProvider` and `SubtitleProvider` ABCs to
  [moviemanager/scraper/interfaces.py](../moviemanager/scraper/interfaces.py) with abstract
  methods `download_trailer(url, output_path)`, `search_subtitles(imdb_id, languages)`,
  and `download_subtitle(file_id, output_path)` (Milestone 5).
- Created [moviemanager/scraper/trailer_provider.py](../moviemanager/scraper/trailer_provider.py)
  with `YtdlpTrailerProvider` implementing `TrailerProvider`: extracts yt-dlp subprocess
  logic from `TrailerService` into a pluggable provider with `capabilities = {TRAILER}`
  and `requires_keys = []`.
- `SubtitleScraper` now implements `SubtitleProvider` ABC via wrapper methods
  `search_subtitles()` and `download_subtitle()` that delegate to existing
  `search()` and `download()` methods.
