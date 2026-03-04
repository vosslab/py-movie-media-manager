# py-movie-media-manager

A Python movie media manager inspired by [tinyMediaManager](https://www.tinymediamanager.org/).
Scan a local movie collection, match movies to IMDB or TMDB, scrape metadata into
Kodi-compatible NFO files, download artwork and trailers, and rename or organize folders.
Provides both a PySide6 GUI and a CLI.

## Quick start

```bash
git clone <repo-url> && cd py-movie-media-manager
source source_me.sh
pip install -e .

# launch the GUI
./launch_gui.sh

# or use the CLI
python3 movie_organizer.py scan -d /path/to/movies
```

See [docs/INSTALL.md](docs/INSTALL.md) for full setup steps and
[docs/USAGE.md](docs/USAGE.md) for CLI and GUI usage.

## Documentation

- [docs/INSTALL.md](docs/INSTALL.md): setup steps, dependencies, and environment requirements.
- [docs/USAGE.md](docs/USAGE.md): how to run the tool, CLI subcommands, and practical examples.
- [docs/NFO_FILE_FORMAT.md](docs/NFO_FILE_FORMAT.md): Kodi-compatible NFO XML format reference.
- [docs/BACKGROUND_JOBS.md](docs/BACKGROUND_JOBS.md): GUI background job system and priority tiers.
- [docs/TASK_API.md](docs/TASK_API.md): internal task API for background workers.
- [docs/MOVIE_ORGANIZATION_UI_UX_WORKFLOW.md](docs/MOVIE_ORGANIZATION_UI_UX_WORKFLOW.md): UI selection and batch workflow.
- [docs/WAF_CHALLENGES.md](docs/WAF_CHALLENGES.md): IMDB WAF bypass techniques.
- [docs/HOW_TO_PROPERLY_DOWNLOAD_IMDB_PARENTS_GUIDE_DATA.md](docs/HOW_TO_PROPERLY_DOWNLOAD_IMDB_PARENTS_GUIDE_DATA.md): parental guide scraping via GraphQL.
- [docs/CHANGELOG.md](docs/CHANGELOG.md): chronological record of changes.

## Testing

```bash
source source_me.sh && python3 -m pytest tests/
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Maintainer

Neil Voss, https://bsky.app/profile/neilvosslab.bsky.social
