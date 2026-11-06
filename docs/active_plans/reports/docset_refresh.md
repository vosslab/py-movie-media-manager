# Documentation refresh report

## Scope

This report records the repository-wide documentation refresh on 2026-11-06.
It distinguishes current user documentation from retained implementation
history, without making unmeasured collection-size or performance claims.

## Created

- No remaining-doc reference guide was created. Existing documentation already
  covers NFO input/output, background work, and the IMDB WAF behavior with
  implementation-specific detail.

## Updated

- [BACKGROUND_JOBS.md](../../BACKGROUND_JOBS.md) now documents selected-job
  cancellation and queue pause/resume.
- [TASK_API.md](../../TASK_API.md) now documents the corresponding TaskAPI
  queue-control surface.
- [HOW_TO_PROPERLY_DOWNLOAD_IMDB_PARENTS_GUIDE_DATA.md](../../HOW_TO_PROPERLY_DOWNLOAD_IMDB_PARENTS_GUIDE_DATA.md)
  now links to the dedicated parental-guide scraper.
- [PYTHON_PORT_PLAN.md](../../PYTHON_PORT_PLAN.md) is labeled as historical
  planning context rather than a current roadmap.

## Other documentation owners

| Owner | Files | Status at audit time |
| --- | --- | --- |
| Landing page | `README.md` | Refreshed; CLI help, CLI integration, and README link checks passed. Screenshot is pending. |
| Setup and usage | `docs/INSTALL.md`, `docs/USAGE.md` | Refreshed; GUI-primary and safe CLI guidance checked. Fresh installed-console validation is not complete. |
| Architecture | `docs/CODE_ARCHITECTURE.md`, `docs/FILE_STRUCTURE.md` | Created; 44 Markdown guidance checks passed. |
| Related projects | `docs/RELATED_PROJECTS.md` | Created with official tinyMediaManager, Kodi, and MediaElch references verified. |
| Release docs | `docs/NEWS.md`, `docs/RELEASE_HISTORY.md` | Created for the 26.11 unreleased snapshot; VERSION matches and no HEAD tag was found. |
| Screenshot documentation | `docs/screenshots/` and README screenshot block | Awaiting the landing-page managed block |

## Audited decisions

- [NFO_FILE_FORMAT.md](../../NFO_FILE_FORMAT.md) remains the single file-I/O
  reference. A second `FILE_FORMATS.md` or YAML-format document would repeat
  the NFO guide or expose settings fields without a stable user-facing schema.
- `ROADMAP.md` and `TODO.md` were not created: the repository contains no
  bounded, approved future work suitable for a durable roadmap.
- `COOKBOOK.md`, `DEVELOPMENT.md`, `FAQ.md`, and `TROUBLESHOOTING.md` were not
  created: the evidence is already covered by task, API, installation, WAF,
  and background-job references; duplicating it would add maintenance work.
- [AUTHORS.md](../../AUTHORS.md), [MARKDOWN_STYLE.md](../../MARKDOWN_STYLE.md),
  [PYTHON_STYLE.md](../../PYTHON_STYLE.md), and [REPO_STYLE.md](../../REPO_STYLE.md)
  exactly match their canonical starter-repository versions and were not edited.
- No undesirable root documentation files were present. `CLAUDE.md` is a
  repository instruction file, not a public contributor or policy document.

## Known verification gaps

- Run the repository Markdown-link check after all concurrent documentation
  edits settle.
- A screenshot pass remains separate from this audit; retain only a captured
  and inspected image that the landing-page managed block can reference.
