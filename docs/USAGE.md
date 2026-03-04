# Usage

py-movie-media-manager provides a PySide6 GUI and a CLI for managing a local movie
collection. The typical workflow is: scan directories, match movies to IMDB or TMDB,
scrape metadata, download artwork, and rename folders.

## GUI

Launch the GUI with the helper script:

```bash
./launch_gui.sh
```

Or directly:

```bash
source source_me.sh && python3 movie_organizer_gui.py
```

Optional flags:

- `-d /path/to/movies` -- open a specific movie directory on startup.
- `--open-last` -- reopen the last used directory.

## CLI

All CLI subcommands require `-d` to specify the movie directory.

```bash
source source_me.sh && python3 movie_organizer.py <command> [options]
```

### Subcommands

| Command | Description |
| --- | --- |
| `scan` | Scan a directory and list discovered movies |
| `info` | Print library statistics (total, scraped, artwork counts) |
| `list` | List movies with optional filters (`-u` for unscraped, `-f` for title filter) |
| `scrape` | Scrape metadata from IMDB/TMDB for unscraped movies |
| `rename` | Rename movie files using a template (dry-run by default) |
| `edit` | Edit metadata fields on a movie and write NFO |
| `artwork` | Download poster and fanart for scraped movies |

### Common examples

Scan a movie directory:

```bash
python3 movie_organizer.py scan -d ~/Movies
```

List unscraped movies:

```bash
python3 movie_organizer.py list -d ~/Movies -u
```

Scrape metadata in batch mode (auto-select high-confidence matches):

```bash
python3 movie_organizer.py scrape -d ~/Movies -b
```

Preview renames without moving files (dry-run is the default):

```bash
python3 movie_organizer.py rename -d ~/Movies -t '{title} ({year})'
```

Execute renames after reviewing the preview:

```bash
python3 movie_organizer.py rename -d ~/Movies -t '{title} ({year})' -x
```

Download artwork and trailers:

```bash
python3 movie_organizer.py artwork -d ~/Movies --trailer
```

## Inputs and outputs

- **Input**: a directory tree containing movie video files (`.mkv`, `.mp4`, `.avi`, etc.),
  one movie per folder.
- **Output**: Kodi-compatible NFO XML files written alongside each video, plus downloaded
  artwork (`poster.jpg`, `fanart.jpg`) and optional trailers saved in each movie folder.
- **Config**: `~/.config/movie_organizer.yaml` stores API keys and settings.

See [docs/NFO_FILE_FORMAT.md](docs/NFO_FILE_FORMAT.md) for the NFO XML schema.

## Known gaps

- [ ] Document subtitle download workflow (`--subtitles` flag on `artwork` subcommand).
- [ ] Document config YAML fields and defaults.
