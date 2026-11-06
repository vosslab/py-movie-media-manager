# Usage

Movie Media Manager is designed for working through a local collection in
reviewable batches: scan first, narrow the table, confirm matches, preview
renames, then apply changes only to the movies you chose.

## GUI collection workflow

Start with the collection root you want to inspect:

```bash
source ./source_me.sh
python3 movie_organizer_gui.py --directory "/Volumes/Media/Movies"
```

For a returning session, `--open-last` reopens the last saved directory. The
same options work through `./launch_gui.sh`.

1. Scan the root. The table shows discovered movies and their metadata state.
2. Filter or sort the table, then use the check controls such as **Check
   Unmatched**, **Check No Artwork**, or **Check Selected** to keep a persistent
   working set. Use checks or row selection to choose a batch; see the linked
   workflow below for exact precedence.
3. Use **Match Selected** to search, inspect candidate details and artwork, and
   accept or skip each match. Save TMDB credentials in **Settings** before using
   TMDB; IMDB is the default provider.
4. Use **Organize Selected**. Review the rename preview carefully, then confirm
   it to move or rename only the chosen matched movies.
5. Use the status-bar progress and Jobs dialog to follow long scans, matching,
   probing, and downloads. **Pause** holds queued work while running work
   finishes; **Cancel Job** requests cancellation of a selected job.

The Jobs dialog also reports completed and failed work. See
[BACKGROUND_JOBS.md](BACKGROUND_JOBS.md) for statuses and error categories, and
[MOVIE_ORGANIZATION_UI_UX_WORKFLOW.md](MOVIE_ORGANIZATION_UI_UX_WORKFLOW.md) for
the exact checked-versus-selected behavior.

## Command-line workflow

Run the CLI from the source checkout after bootstrapping its environment:

```bash
source ./source_me.sh
python3 movie_organizer.py scan --directory "/Volumes/Media/Movies"
python3 movie_organizer.py info --directory "/Volumes/Media/Movies"
python3 movie_organizer.py list --directory "/Volumes/Media/Movies" --unscraped
```

The scan and list commands print tables; `info` prints collection counts for
scraped movies and configured artwork URLs. These commands inspect the supplied
directory and do not rename files.

## Match and rename deliberately

`scrape` contacts the selected metadata service. Without `--batch`, it presents
candidate matches for confirmation; `--batch` selects the first result only when
the computed confidence is at least 0.7.

```bash
source ./source_me.sh
python3 movie_organizer.py scrape --directory "/Volumes/Media/Movies"
python3 movie_organizer.py scrape --directory "/Volumes/Media/Movies" --batch
python3 movie_organizer.py rename --directory "/Volumes/Media/Movies" \
  --template '{title} ({year})' --dry-run
```

Rename is dry-run by default and prints a source-to-destination preview. Use
`--execute` only after reviewing that preview; it asks for confirmation before
moving files.

```bash
source ./source_me.sh
python3 movie_organizer.py rename --directory "/Volumes/Media/Movies" --execute
```

The CLI `artwork` subcommand downloads configured artwork for scraped movies.
Use the GUI's Download action for trailer or subtitle downloads. Trailers require
`yt-dlp` and FFmpeg but no provider API key; subtitles require the OpenSubtitles
API key, username, and password saved in **Settings**.

## Inputs, outputs, and configuration

- Scan a directory tree containing supported video files, including `.mkv`,
  `.mp4`, `.m4v`, `.avi`, `.mov`, `.m2ts`, and `.webm`.
- Metadata writes Kodi-compatible NFO XML beside movie media; see
  [NFO_FILE_FORMAT.md](NFO_FILE_FORMAT.md). Artwork and optional trailers are
  saved in movie folders.
- The global `--config PATH` option selects a YAML settings file instead of the
  default `~/.config/movie_organizer.yaml`.
- `edit` changes title, year, genre, director, or rating for one discovered movie
  and writes its NFO. Run `python3 movie_organizer.py edit --help` after
  bootstrapping for its field flags.

## Known gaps

- [ ] Add a field-by-field configuration reference once the settings format is
  treated as a stable user-facing contract.
