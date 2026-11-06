# Install

Install py-movie-media-manager so that the `movie-organizer` CLI and PySide6 GUI
are available on your system.

## Requirements

- Python 3.12 or later.
- `pip` for installing Python packages.
- The MediaInfo library for codec detection. Supported `pymediainfo` wheels bundle it;
  source installations need a system copy.
- `yt-dlp` and FFmpeg for trailer downloading and merging video/audio streams.

On macOS, install the system tools from [Brewfile](../Brewfile):

```bash
brew bundle
```

The `media-info` formula installs the `mediainfo` command and depends on `libmediainfo`.
See the [Homebrew formula](https://formulae.brew.sh/formula/media-info) and
[pymediainfo installation notes](https://pymediainfo.readthedocs.io/en/stable/introduction.html#installation).
On other platforms, install the MediaInfo library when needed and install `yt-dlp` and FFmpeg
through your package manager. Scanning and metadata editing do not require the trailer tools.

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
