# NFO file format

Documentation for the Kodi NFO XML file format as used by this project.

## Overview

Kodi NFO files are UTF-8 encoded XML documents that store movie metadata.
They begin with the standard XML declaration:

```xml
<?xml version="1.0" encoding="utf-8"?>
```

The root element is `<movie>`. When Kodi finds an NFO file alongside a video,
it loads metadata directly from the file instead of re-scraping from an
online source. This makes NFO files the authoritative local metadata cache.

## File naming

Kodi recognizes two naming conventions for movie NFO files:

- `<VideoFileName>.nfo` -- matches the video file stem. For example,
  `The Matrix (1999).mkv` pairs with `The Matrix (1999).nfo`. This is
  the recommended approach.
- `movie.nfo` -- fallback name that Kodi checks when no per-video NFO
  exists. In multi-movie directories, a single `movie.nfo` is shared by
  all videos, so per-video naming is safer and avoids metadata collisions.

## Movie NFO tag reference

All supported XML tags inside the `<movie>` root element.

| Tag | XML type | Description | Multiple? | Status |
| --- | --- | --- | --- | --- |
| title | text | Primary display title | No | Supported |
| originaltitle | text | Original language title | No | Supported |
| sorttitle | text | Alphabetical sort title | No | Supported |
| year | text | Release year | No | Supported |
| id | text | IMDB identifier (e.g. tt1234567) | No | Supported |
| tmdbid | integer (as text) | TMDB numeric identifier | No | Supported |
| tagline | text | Short promotional tagline | No | Supported |
| plot | text | Full plot summary | No | Supported |
| outline | text | Short plot outline (read as fallback for plot) | No | Supported (read-only) |
| runtime | integer (as text) | Runtime in minutes | No | Supported |
| mpaa | text | Content rating (PG-13, R, etc.) | No | Supported |
| country | text | Country of origin | No | Supported |
| languages | text | Comma-separated language list | No | Supported |
| premiered | text | Release date string | No | Supported |
| rating | float (as text) | Average rating score | No | Supported |
| votes | integer (as text) | Number of votes (may contain commas) | No | Supported |
| top250 | integer (as text) | Position in top-250 list | No | Supported |
| userrating | float (as text) | User-assigned personal rating | No | Supported |
| director | text | Director name(s) | No | Supported |
| credits | text | Writer name(s) | No | Supported |
| studio | text | Production studio | No | Supported |
| watched | boolean (true/false) | Whether movie has been watched | No | Supported |
| playcount | integer (as text) | Play count (>0 means watched) | No | Supported |
| dateadded | text | Date added to library | No | Supported |
| lastplayed | text | Date last watched | No | Supported |
| poster | text | URL to poster image | No | Supported |
| trailer | text | Trailer URL or path | Yes | Supported |
| set | container | Movie set/collection | No | Supported |
| set/name | text | Movie set name | - | Supported |
| genre | text | Genre name | Yes | Supported |
| tag | text | User-defined tag | Yes | Supported |
| actor | container | Cast member | Yes | Supported |
| actor/name | text | Actor name | - | Supported |
| actor/role | text | Character role | - | Supported |
| actor/thumb | text | Actor photo URL | - | Supported |
| actor/tmdbid | integer (as text) | Actor TMDB ID | - | Supported |
| producer | container | Producer | Yes | Supported |
| producer/name | text | Producer name | - | Supported |
| producer/role | text | Producer role | - | Supported |
| producer/thumb | text | Producer photo URL | - | Supported |
| producer/tmdbid | integer (as text) | Producer TMDB ID | - | Supported |
| thumb | text | Poster URL (alias for poster) | No | Supported |
| fanart | container | Fanart wrapper | No | Supported |
| fanart/thumb | text | Fanart image URL | - | Supported |
| parental_guide | container | Advisory severity levels | No | Supported (custom) |
| parental_guide/advisory | text with @category | Severity by category | Yes | Supported (custom) |

Tags not yet supported by this project:

- `uniqueid` -- modern Kodi v17+ style external ID (with `type` attribute)
- `ratings` -- wrapper element for multiple rating sources
- `fileinfo` -- technical file information container
- `source` -- media source descriptor
- `original_filename` -- original file name before rename

## Full sample NFO

A complete example using a fictional movie with all common tags populated.

```xml
<?xml version="1.0" encoding="utf-8"?>
<movie>
	<title>Starfall Legacy</title>
	<originaltitle>Herencia de Estrellas</originaltitle>
	<sorttitle>Starfall Legacy</sorttitle>
	<set>
		<name>Starfall Trilogy</name>
	</set>
	<rating>7.8</rating>
	<userrating>8.5</userrating>
	<year>2024</year>
	<top250>142</top250>
	<votes>48210</votes>
	<outline>A pilot discovers a signal from a dying star.</outline>
	<plot>In the year 2180, veteran pilot Mara Chen intercepts a
		mysterious signal from a collapsing star system. Against orders,
		she diverts her cargo vessel to investigate, discovering an alien
		artifact that holds the key to faster-than-light travel. Pursued
		by corporate enforcers and a rogue military fleet, Mara must
		decide whether to hand over the artifact or risk everything to
		unlock its secrets for all of humanity.</plot>
	<tagline>The stars are calling.</tagline>
	<runtime>127</runtime>
	<thumb>https://image.tmdb.org/t/p/original/starfall_poster.jpg</thumb>
	<fanart>
		<thumb>https://image.tmdb.org/t/p/original/starfall_fanart.jpg</thumb>
	</fanart>
	<mpaa>PG-13</mpaa>
	<parental_guide>
		<advisory category="alcohol">Mild</advisory>
		<advisory category="frightening">Moderate</advisory>
		<advisory category="nudity">None</advisory>
		<advisory category="profanity">Mild</advisory>
		<advisory category="violence">Moderate</advisory>
	</parental_guide>
	<id>tt9876543</id>
	<tmdbid>654321</tmdbid>
	<trailer>https://www.youtube.com/watch?v=abc123</trailer>
	<trailer>plugin://plugin.video.youtube/?action=play_video&amp;videoid=abc123</trailer>
	<country>United States</country>
	<premiered>2024-06-15</premiered>
	<watched>true</watched>
	<playcount>1</playcount>
	<genre>Science Fiction</genre>
	<genre>Adventure</genre>
	<genre>Drama</genre>
	<studio>Nebula Pictures</studio>
	<credits>Elena Rodriguez / James Park</credits>
	<director>Elena Rodriguez</director>
	<tag>space</tag>
	<tag>first contact</tag>
	<actor>
		<name>Li Wei</name>
		<role>Mara Chen</role>
		<thumb>https://image.tmdb.org/t/p/w500/liwei.jpg</thumb>
		<tmdbid>112233</tmdbid>
	</actor>
	<actor>
		<name>David Okonkwo</name>
		<role>Commander Nash</role>
		<thumb>https://image.tmdb.org/t/p/w500/okonkwo.jpg</thumb>
		<tmdbid>445566</tmdbid>
	</actor>
	<producer>
		<name>Sarah Kim</name>
		<role>Executive Producer</role>
		<thumb>https://image.tmdb.org/t/p/w500/kim.jpg</thumb>
		<tmdbid>778899</tmdbid>
	</producer>
	<dateadded>2024-07-01 12:00:00</dateadded>
	<lastplayed>2024-08-15 20:30:00</lastplayed>
	<languages>English, Spanish</languages>
</movie>
```

## Our implementation

The NFO reader and writer live in
[moviemanager/core/nfo/reader.py](moviemanager/core/nfo/reader.py) and
[moviemanager/core/nfo/writer.py](moviemanager/core/nfo/writer.py).
The movie data model is defined in
[moviemanager/core/models/movie.py](moviemanager/core/models/movie.py).

### Reading NFO files

The reader (`read_nfo()`) parses the XML tree and maps each element to the
corresponding field on the `Movie` dataclass. Different tag types use
different conversion strategies:

- **Text tags** -- direct string assignment. Tags like `title`, `year`,
  `director`, `mpaa`, `country` are stored as-is after stripping whitespace.
- **Integer tags** -- `int()` conversion. Applies to `tmdbid`, `runtime`,
  `top250`, and `playcount`. The `votes` tag additionally strips commas
  before conversion (e.g. `"48,210"` becomes `48210`).
- **Float tags** -- `float()` conversion. Applies to `rating` and
  `userrating`.
- **Boolean tags** -- `watched` is parsed with
  `text.lower() in ("true", "1")`. The `playcount` tag also sets `watched`
  to `True` when the count is greater than zero.
- **Container tags** -- child elements are parsed into structured data:
  - `set` -- reads `<name>` child or falls back to direct text content.
    Produces a `MovieSet` instance.
  - `actor` and `producer` -- each parsed into a dict with keys `name`,
    `role`, `thumb`, and `tmdb_id`.
  - `fanart` -- reads the first `<thumb>` child for the fanart URL.
  - `parental_guide` -- reads `<advisory>` children, extracting the
    `category` attribute and text content into a dict keyed by category.
- **outline** -- used as a fallback for `plot` only when `plot` has not
  already been populated by a preceding `<plot>` element.
- **Unknown elements** -- any XML element not in the `KNOWN_TAGS` set is
  preserved in the `unknown_elements` list on the `Movie` instance.

### Writing NFO files

The writer (`write_nfo()`) serializes the `Movie` dataclass back to XML:

- Creates `<movie>` as the root element.
- Writes each non-empty field as the appropriate XML tag.
- Both `<outline>` and `<plot>` are written with the same `plot` content,
  preserving compatibility with readers that prefer one over the other.
- Uses `<thumb>` (not `<poster>`) for the poster URL on output.
- Wraps fanart URLs inside `<fanart><thumb>...</thumb></fanart>`.
- Emits one `<genre>`, `<tag>`, `<trailer>`, `<actor>`, and `<producer>`
  element per list entry.
- Writes `<watched>` as `"true"` or `"false"` and derives `<playcount>`
  from the watched state (`"1"` if watched, `"0"` otherwise).
- Appends deep copies of unknown elements at the end for round-trip
  preservation.
- Uses `lxml.etree.indent()` with tab indentation.
- Writes with `xml_declaration=True` and `encoding="utf-8"`.

## Combination NFO

Kodi supports partial NFO files that contain only a subset of tags. When
a partial NFO is present, Kodi uses it as an override layer: only the
tags present in the file replace the scraped or default values. Tags
omitted from the partial NFO are left at their scraped defaults.

This means you can create a minimal NFO with just an IMDB ID to tell
Kodi which movie to scrape, while letting the scraper fill in the rest:

```xml
<?xml version="1.0" encoding="utf-8"?>
<movie>
	<id>tt1234567</id>
</movie>
```

## Round-trip preservation

When reading an NFO file, any XML elements not recognized by the reader
(those not in `KNOWN_TAGS`) are collected into the `unknown_elements` list
on the `Movie` dataclass. When writing back to disk, the writer appends
deep copies of these elements at the end of the output XML. This ensures
that tags added by other tools or future Kodi versions survive a
read-then-write cycle without data loss.

## Differences from modern Kodi v17+

This project uses an older NFO tag style that predates Kodi v17 (Krypton).
Key differences from the modern format:

- **External IDs** -- we use `<id>` for IMDB and `<tmdbid>` for TMDB.
  Modern Kodi uses `<uniqueid type="imdb" default="true">` and
  `<uniqueid type="tmdb">` inside a wrapper. Both old and new formats
  are still recognized by Kodi, but the `uniqueid` style is preferred
  going forward.
- **Ratings** -- we use a flat `<rating>` element with a single numeric
  value. Modern Kodi uses a `<ratings>` wrapper containing one or more
  `<rating>` children, each with `<value>` and `<votes>` sub-elements
  and a `name` attribute for the source (e.g. `imdb`, `tmdb`).
- **Parental guide** -- the `<parental_guide>` element with `<advisory>`
  children is a custom extension specific to this project. It is not
  part of the standard Kodi NFO schema. Kodi ignores unknown elements,
  so this tag coexists safely with standard metadata.
