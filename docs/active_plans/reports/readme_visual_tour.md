# README visual tour

Captured and inspected native macOS windows on 2026-11-06 at 21:19 UTC.
The [README.md](../../../README.md) now shows four current workflows before setup.

## Capture receipt

| Asset | Dimensions | Bytes | Verified view |
| --- | --- | --- | --- |
| [main_window.webp](../../screenshots/main_window.webp) | 1440x932 | 50702 | Completed ten-movie scan, mixed match states, selected metadata. |
| [match_search.webp](../../screenshots/match_search.webp) | 1100x732 | 38452 | Real IMDb search for Moon, confidence ordering, downloaded poster, batch controls. |
| [rename_preview.webp](../../screenshots/rename_preview.webp) | 1100x732 | 58702 | Twelve dry-run video/NFO moves, current and proposed paths. |
| [metadata_editor.webp](../../screenshots/metadata_editor.webp) | 850x932 | 33294 | Arrival sample metadata, downloaded poster, editable fields, Save/Cancel. |

All four images were captured through easy-screenshot, encoded with `cwebp -q 90`,
and visually inspected. Total: 181150 bytes. Each image is below the 1920-pixel
edge limit. The editor uses a taller frame because its metadata form is vertical.
No obsolete or unreferenced managed assets remain; no reference images were removed.

## Reproduce a view

Run [capture_readme_screenshot.py](../../../devel/capture_readme_screenshot.py)
from the repository root:

```bash
source ./source_me.sh
python3 devel/capture_readme_screenshot.py --view match
```

Wait for `README_DEMO_READY`. In another terminal, capture the matching native
window with easy-screenshot; process under `/tmp`, then copy the encoded WebP:

```bash
screenshot -A Python -t "Match - Moon" -f /tmp/match_search.png
magick /tmp/match_search.png -resize '1920x1920>' /tmp/match_search.png
cwebp -q 90 /tmp/match_search.png -o /tmp/match_search.webp
cp /tmp/match_search.webp docs/screenshots/match_search.webp
rm /tmp/match_search.png
```

When the console command is unavailable, substitute
`/Users/vosslab/nsh/easy-screenshot/run.sh` for `screenshot` on this workstation.
Close the sample app after capture. Choose the other views with:

| View argument | Window title | Asset slug |
| --- | --- | --- |
| `main` | Movie Media Manager - Sample Library | `main_window` |
| `rename` | Rename Preview | `rename_preview` |
| `edit` | Edit - Arrival | `metadata_editor` |

## Isolation and verification

- Capture uses temporary movie files/NFOs, isolated QSettings/YAML, and a temporary
  API cache. Rename pairs are computed with `dry_run=True`; no moves are executed.
- `main` and `rename` work locally. `match` and `edit` need live IMDb/CDN access;
  no search results, confidence values, or downloaded posters were fabricated.
- Application implementation stayed unchanged. The capture helper opens real
  widgets using the normal application API and sample library.
- 568 focused README/link, pyflakes, annotations, and shebang checks passed.
  Capture helper help, native execution of all four views, image dimensions,
  size budgets, embed references, and `git diff --check` were verified.
- No GIF, full regression run, GitHub-rendered page inspection, or large-collection
  benchmark was performed. The sample library demonstrates workflow, not capacity.
