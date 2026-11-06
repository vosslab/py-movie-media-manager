# Permanent test pruning

Reviewed 2026-11-06 using the checklist in [PYTEST_STYLE.md](../../PYTEST_STYLE.md).
This pass starts after the earlier IMDb reduction from 43 tests to four.

## Scope and results

- Evaluated repository-owned pytest modules and all four non-browser E2E runners.
- Excluded propagated hygiene checks and support, including the unmarked shared
  test-naming checker. Preserved the explicit core/API/scraper Qt dependency boundary.
- Owned inventory: 24 modules/runners and 179 pytest functions became 21 and 106.
- Removed 1,112 lines net, including the mirrored browser fake, the movie-display
  stub, and a separate help-only subprocess runner. No new fixtures or test dependencies.
- Kept pytest-qt because the retained image-decoding test uses a real widget.
- No production code changes belong to this pruning pass. Existing trailer changes
  and concurrent edits were left intact.

## Decisions by area

| Area | Decision and lasting protection |
| --- | --- |
| Browser transport | Delete the module: import/name/path assertions and a fake that mirrored private state did not establish real browser or thread behavior. |
| Display formatting | Delete the module and movie stub: simple string layouts did not justify freezing presentation choices. |
| CLI | Delete the help/no-command runner; retain real scan, info, and dry-run filesystem workflow. |
| Pipeline | Keep metadata application/NFO creation and one complete scan/scrape/rename path; delete repeated scans and a second movie's identical scrape. |
| Renaming/templates | Delete repeated expansion cases from renamer tests; keep dry-run safety, moved files/artwork, sanitization, template tokens, and combined checkbox behavior. |
| Matching | Remove private helper curves and numeric confidence cutoffs; keep correct-movie ranking, bounds, popularity ordering, and runtime comparisons. |
| Cache | Keep persisted data, expiry, key normalization, selective removal/clearing, corrupt-cache recovery, and first-write directories. Delete repeated misses/round trips and speculative serialization of methods. |
| File classification | Keep the category/precedence matrix and filename-level video detection; delete overlapping predicate matrices. |
| Collection/scanning | Keep file inclusion/exclusion, nested/multiple movies, skipped directories, and existing NFO loading; remove repeated empty-directory and artwork checks. |
| Image widget | Keep actual decoding/downscaling of oversized artwork; remove duplicate size-helper checks and exact diagnostic wording. |
| Provider registry | Keep capability/key filtering, configured provider fallback/routing, and discovered capability availability; remove class-name, constructor, and repeated inventory assertions. |
| Provider parsing | Keep the four IMDb parsing contracts, TMDB mappings/identifier lookup, and Fanart results/failure handling. |
| Cookies | Keep SQLite domain filtering/profile selection and missing/unsupported-browser behavior; delete the second unsupported-browser example. |
| NFO/workers | Keep round-trip metadata/XML characters/sets/guides/trailers, worker errors, and cancellation. |
| GUI/live IMDb | Retain the offscreen collection/chooser workflow and explicit live suggestion lookup. |

## Verification and limits

- Before: `source ./source_me.sh && pytest tests/ -q --durations=8`:
  2,538 passed in 13.81 seconds.
- After, same command: 2,398 passed in 4.17 seconds. Timing is a local observation,
  not a performance guarantee. Collected counts include parametrized hygiene checks.
- `source ./source_me.sh && python3 tests/e2e/e2e_cli_integration.py`: passed.
- `source ./source_me.sh && QT_QPA_PLATFORM=offscreen python3 tests/e2e/e2e_gui.py`: passed.
- Checked dangling executable/doc references and `git diff --check`; no issues.
  Historical changelog mentions remain historical records.
- No live-network run or native browser/CAPTCHA interaction was performed. Browser
  timeout/CAPTCHA details, exact display strings, and CLI help/no-command output lose
  dedicated assertions. The GUI runner does not replace those browser assertions.
