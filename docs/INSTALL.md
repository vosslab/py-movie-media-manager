# Install

Install py-movie-media-manager so that the `movie-organizer` CLI and PySide6 GUI
are available on your system.

## Requirements

- Python 3.12 or later.
- `pip` for installing Python packages.
- `MediaInfo` (system library, required by `pymediainfo` for codec detection).
- `yt-dlp` (optional, for trailer downloading).

## Install steps

1. Clone the repository:

```bash
git clone <repo-url>
cd py-movie-media-manager
```

2. Install runtime dependencies:

```bash
source source_me.sh
pip install -r pip_requirements.txt
```

3. Install the package in editable mode:

```bash
pip install -e .
```

4. Install dev dependencies (optional, for testing):

```bash
pip install -r pip_requirements-dev.txt
```

## Configuration

API keys and settings are stored in `~/.config/movie_organizer.yaml`.
The file is created automatically on first run. Add your TMDB API key there
if you want TMDB scraping (IMDB works without a key).

## Verify install

```bash
source source_me.sh && python3 movie_organizer.py --help
```

This prints the CLI usage and available subcommands.

## Known gaps

- [ ] Confirm whether `MediaInfo` is required at install time or only at runtime.
- [ ] Document macOS Homebrew install for `mediainfo` and `yt-dlp` if a Brewfile is added.
