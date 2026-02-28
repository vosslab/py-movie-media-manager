# Changelog

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
