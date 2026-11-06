# File structure

## Top-level layout

```text
py-movie-media-manager/
+- movie_organizer.py        CLI entry point
+- movie_organizer_gui.py    PySide6 entry point
+- launch_gui.sh             GUI launcher
+- moviemanager/             native application package
+- tests/                    focused and end-to-end verification
+- docs/                     user and maintainer documentation
+- devel/                    release, changelog, and local developer helpers
+- tools/                    supporting repository tools
+- Brewfile                  macOS system-tool dependencies
+- pyproject.toml            project metadata and runtime dependencies
+- pip_requirements*.txt     pip installation lists
+- source_me.sh              Python environment setup for agent and developer use
`- VERSION                  release version
```

The native code belongs in [moviemanager/](../moviemanager/), not in a second application package.
The root scripts remain thin entry points so the GUI and CLI share the same API and core behavior.

## Application package

```text
moviemanager/
+- api/                 facade plus scan, search, scrape, download, and cache services
+- core/
|  +- file/             classify, collect, walk, and move collection files
|  +- models/           Movie, MovieSet, and MediaFile data classes
|  +- movie/            session list, directory scan, rename, and template behavior
|  `- nfo/              Kodi NFO XML reader and writer
+- scraper/             provider interfaces, registry, and provider implementations
+- ui/
|  +- controllers/      scan, match, rename, and download interaction controllers
|  +- dialogs/          modal workflows, including the movie chooser
|  +- movies/           collection table, panel, and detail presentation
|  `- widgets/          reusable PySide6 controls and views
`- vendor/              repository-vendored support code
```

[moviemanager/api/movie_api.py](../moviemanager/api/movie_api.py) is the shared facade for root
entry points and UI controllers. Keep code that needs Qt in `ui`; keep local media and metadata
rules in `core`; keep provider-specific concerns in `scraper`.

## Tests and developer tools

- [tests/](../tests/) contains focused unit, integration, style, and repository-policy tests. Test
  filenames begin with `test_`.
- [tests/e2e/](../tests/e2e/) contains explicitly named end-to-end CLI, GUI, and live-provider
  checks. These are separated from normal focused tests so their external requirements are clear.
- [devel/](../devel/) contains changelog rotation, release preparation, repository mapping, and
  screenshot helpers. It is not imported by the application package.
- [tools/](../tools/) holds supporting repository tools. Check the tool's own help or source before
  treating it as an application runtime dependency.

## Documentation map

- [INSTALL.md](INSTALL.md) and [USAGE.md](USAGE.md) describe setup and operation.
- [NFO_FILE_FORMAT.md](NFO_FILE_FORMAT.md) documents the on-disk metadata format.
- [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md) and [TASK_API.md](TASK_API.md) document GUI work
  scheduling.
- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) describes runtime boundaries and data flow.
- [REPO_STYLE.md](REPO_STYLE.md), [PYTHON_STYLE.md](PYTHON_STYLE.md), and
  [PYTEST_STYLE.md](PYTEST_STYLE.md) define maintenance conventions.
- [CHANGELOG.md](CHANGELOG.md) is the active change record; archived day blocks use
  `CHANGELOG-YYYY-MMa.md` filenames.

## Generated and local state

- Build products (`build/`, `dist/`, `sdist/`, `*.egg-info/`, and `site/`) are ignored.
- `graphify-out/` is generated repository-map output and is ignored.
- Root `output*/`, `generated/`, `temp/`, and test temporary files are ignored.
- Runtime settings, API cache files, media-side NFO files, and Qt settings are stored outside the
  repository or alongside the managed movie collection; see [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md).

## Where to add work

- Put a new shared movie operation behind [moviemanager/api/movie_api.py](../moviemanager/api/movie_api.py)
  and its focused service or core module.
- Put a new scraper provider in [moviemanager/scraper/](../moviemanager/scraper/) and register it.
- Put a GUI interaction coordinator in [moviemanager/ui/controllers/](../moviemanager/ui/controllers/),
  a modal flow in [moviemanager/ui/dialogs/](../moviemanager/ui/dialogs/), or a reusable visual
  element in [moviemanager/ui/widgets/](../moviemanager/ui/widgets/).
- Add focused coverage under [tests/](../tests/) and reserve [tests/e2e/](../tests/e2e/) for
  cross-process, GUI, or live-provider behavior.
- Add durable documentation under [docs/](.) using the repository's Markdown conventions.
