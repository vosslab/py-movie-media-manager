# Code architecture

## Overview

Movie Media Manager is a local desktop application and command-line tool for maintaining movie
collections. Both entry points construct [moviemanager/api/movie_api.py](../moviemanager/api/movie_api.py)
`MovieAPI`, which composes the current-session movie list, provider pipeline, cache, and focused
operations. The GUI supplies interaction and background scheduling; the core package owns local
files, movie data, NFO XML, scanning, and rename planning.

## Major components

| Area | Responsibility | Main code |
| --- | --- | --- |
| Entry points | Parse CLI or GUI options and load settings. | [movie_organizer.py](../movie_organizer.py), [movie_organizer_gui.py](../movie_organizer_gui.py), [launch_gui.sh](../launch_gui.sh) |
| API facade | Compose services and present operations to both front ends. | [moviemanager/api/movie_api.py](../moviemanager/api/movie_api.py) |
| Core | Model movies and media files; scan folders; read/write NFO files; plan and perform renames. | [moviemanager/core/](../moviemanager/core/) |
| Scrapers | Declare provider capabilities, register providers, and build the configured pipeline. | [moviemanager/scraper/](../moviemanager/scraper/) |
| UI | Present the library, dialogs, controllers, and background work through PySide6. | [moviemanager/ui/](../moviemanager/ui/) |

`MovieAPI` is the boundary for front ends. Its scan, search, scrape, rename, artwork, trailer, and
subtitle methods delegate to API and core services. It also owns the scraper lifecycle, including
the optional Qt-based IMDb browser transport. Provider selection is data-driven by the capability
interfaces and registry; settings select an available primary provider and supplements.

The `core` package does not depend on PySide6. `Movie` and related data classes in
[moviemanager/core/models/](../moviemanager/core/models/) carry scan results, metadata, file
relationships, and scraper output. The scanner discovers local files and NFO data; the rename
service expands templates, collects associated media, returns a dry-run plan, and moves files only
when requested.

## Data flow

The usual collection workflow is:

1. The CLI or [moviemanager/ui/main_window.py](../moviemanager/ui/main_window.py) asks `MovieAPI`
   to scan a selected directory. The scan service creates `Movie` instances and adds them to the
   in-memory `MovieList` for the current session.
2. A match controller opens `MovieChooserDialog` for a movie or batch. It searches the configured
   provider pipeline through `MovieAPI`, shows candidate metadata, and starts a scrape after a
   selection is accepted.
3. Scraping merges provider data into the `Movie` and writes Kodi-compatible NFO XML through
   [moviemanager/core/nfo/writer.py](../moviemanager/core/nfo/writer.py). Artwork, trailers, and
   subtitles are separate API operations.
4. The movie panel refreshes the table and detail view from the same movie objects. Rename actions
   use the configured templates to preview or perform moves of video, NFO, artwork, subtitles, and
   trailers.

Persistent application state remains local:

- [moviemanager/core/settings.py](../moviemanager/core/settings.py) loads and saves YAML settings
  at `~/.config/movie_organizer.yaml` unless the entry point supplies a config path.
- [moviemanager/api/api_cache.py](../moviemanager/api/api_cache.py) stores search and metadata JSON
  responses below `~/.cache/movie_organizer/`; expired entries are removed while loading.
- [moviemanager/core/nfo/reader.py](../moviemanager/core/nfo/reader.py) and its writer keep movie
  metadata alongside the media collection as Kodi-compatible NFO XML.
- Qt stores window geometry, window state, and table state through `QSettings` in the main window.

## GUI work and ownership

`MainWindow` owns one `MovieAPI`, one shared `TaskAPI`, the movie panel, and the scan, match,
rename, and download controllers. Controllers submit blocking work through
[moviemanager/ui/task_api.py](../moviemanager/ui/task_api.py), which tracks jobs and uses a
`QThreadPool`; [moviemanager/ui/workers.py](../moviemanager/ui/workers.py) returns results and
errors through Qt signals. Widgets update only from those signals, while file and network work runs
in workers.

The main-window close path first asks about active jobs, then cancels and drains the task pool,
shuts down the detail-panel image work, and finally shuts down `MovieAPI`. This order lets the API
dispose of its IMDb browser transport after background work stops. Dialog-owned searches and poster
downloads are cancelled in `MovieChooserDialog.done()` before Qt destroys the dialog.

The matching dialog is a coordinator, not a result-table implementation:

- [moviemanager/ui/dialogs/movie_chooser.py](../moviemanager/ui/dialogs/movie_chooser.py) switches
  between an existing-match view and search, starts accepted scrapes, and advances or completes a
  batch.
- [moviemanager/ui/widgets/movie_search_pane.py](../moviemanager/ui/widgets/movie_search_pane.py)
  owns query controls, search state, the result table, and selection.
- [moviemanager/ui/widgets/search_result_preview.py](../moviemanager/ui/widgets/search_result_preview.py)
  owns selected-result metadata and its cancellable poster request.
- [moviemanager/ui/dialogs/movie_search_prefetch.py](../moviemanager/ui/dialogs/movie_search_prefetch.py)
  fetches and caches the next batch movie's results and first poster without manipulating widgets.
- [moviemanager/ui/dialogs/batch_navigator.py](../moviemanager/ui/dialogs/batch_navigator.py) is
  Qt-free state for the batch list, position, and match outcomes.

## Testing and extension points

Fast, deterministic tests live directly under [tests/](../tests/). Explicit end-to-end checks live
under [tests/e2e/](../tests/e2e/), including separate CLI, GUI, and live IMDb cases. See
[PYTEST_STYLE.md](PYTEST_STYLE.md) and [E2E_TESTS.md](E2E_TESTS.md) for the test boundaries.

Add a metadata, artwork, trailer, subtitle, or parental-guide provider by implementing the relevant
capability in [moviemanager/scraper/interfaces.py](../moviemanager/scraper/interfaces.py) and
registering it through [moviemanager/scraper/registry.py](../moviemanager/scraper/registry.py).
Add a user-facing operation behind `MovieAPI`; keep Qt widgets and signals in `ui`, and keep file
and movie-domain behavior in `core`.

## Known gaps

- Verify real-provider behavior with the explicitly marked live end-to-end tests before changing
  scraper transport or provider-selection behavior.
