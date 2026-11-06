# Install

Run the PySide6 desktop application and its command-line helper from a source
checkout. This repository is a desktop application, not a published PyPI
package. The verified CLI invocation is `python3 movie_organizer.py` from that
checkout.

## Requirements

- Python 3.12. The project bootstrap commands use that interpreter.
- Git to obtain the source.
- MediaInfo for media probing. `pymediainfo` supplies the Python interface; the
  Homebrew `media-info` formula supplies the `mediainfo` command and library.
- `yt-dlp` only when downloading trailers. The app downloads combined MP4 files;
  FFmpeg and ffprobe are not required.

On macOS, [Brewfile](../Brewfile) installs the supported system tools:

```bash
brew bundle
```

`imagemagick` and `webp` in that Brewfile support the repository's screenshot
maintenance script. They are not needed to scan, match, organize, or use the GUI.
On other platforms, install MediaInfo through the system package manager when it
is not provided by the `pymediainfo` wheel. Install `yt-dlp` only for
trailer downloads.

## Install from source

```bash
git clone https://github.com/vosslab/py-movie-media-manager.git
cd py-movie-media-manager
source ./source_me.sh
python3 -m pip install -r pip_requirements.txt
```

For tests and development checks, add the optional development dependencies:

```bash
source ./source_me.sh
python3 -m pip install -r pip_requirements-dev.txt
```

## Configure metadata services

Open **Settings** in the GUI and save the appropriate credentials. Settings are
stored in `~/.config/movie_organizer.yaml` when saved. IMDB is the default
scraper; add a TMDB API key before selecting TMDB. Optional Fanart.tv artwork
uses its own API key. Subtitle downloads require an OpenSubtitles API key,
username, and password. Trailer downloads use `yt-dlp`; they do not require a
provider API key.

## Verify install

From the source checkout, either command should print usage rather than an
import error:

```bash
source ./source_me.sh && python3 movie_organizer.py --help
source ./source_me.sh && python3 movie_organizer_gui.py --help
```

These commands verify the local CLI and GUI launch arguments. They do not verify
an API key, network access, or a live metadata provider.

## Known gaps

- [ ] Verify package-manager instructions for each non-macOS platform before
  adding platform-specific installation commands.
