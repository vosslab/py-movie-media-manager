# Documentation refresh report

## Scope

This report records the repository-wide documentation refresh on 2026-11-06.
It distinguishes current user documentation from retained implementation
history, without making unmeasured collection-size or performance claims.

## Created

- [CODE_ARCHITECTURE.md](../../CODE_ARCHITECTURE.md) and
  [FILE_STRUCTURE.md](../../FILE_STRUCTURE.md) describe current architecture and
  repository layout.
- [NEWS.md](../../NEWS.md) and [RELEASE_HISTORY.md](../../RELEASE_HISTORY.md)
  summarize the 26.11 development snapshot without representing it as released.
- [RELATED_PROJECTS.md](../../RELATED_PROJECTS.md) distinguishes direct
  interoperability references from adjacent local-media tools.
- [main_window.webp](../../screenshots/main_window.webp) is a native GUI capture
  with a mixed-state sample collection and selected-movie details. It is static;
  a GIF would add size and maintenance without explaining this table-and-detail
  workflow better.

No remaining-doc reference guide was created. Existing documentation already
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
- [CHANGELOG.md](../../CHANGELOG.md) records the durable screenshot helper and
  the richer static README evidence.

## Other documentation owners

| Owner | Files | Status at audit time |
| --- | --- | --- |
| Landing page | `README.md` | Refreshed with real static evidence; final rubric score 93/100 (up from 39/100). |
| Setup and usage | `docs/INSTALL.md`, `docs/USAGE.md` | Refreshed; verified source-checkout commands and corrected the CLI artwork limitation. |
| Architecture | `docs/CODE_ARCHITECTURE.md`, `docs/FILE_STRUCTURE.md` | Created from current source evidence. |
| Related projects | `docs/RELATED_PROJECTS.md` | Created with official tinyMediaManager, Kodi, and MediaElch references verified. |
| Release docs | `docs/NEWS.md`, `docs/RELEASE_HISTORY.md` | Created for the 26.11 development snapshot; VERSION matches and no HEAD tag was found. |
| Screenshot documentation | `devel/capture_readme_screenshot.py`, `docs/screenshots/main_window.webp`, and README block | Complete: deterministic temporary sample library, isolated QSettings/YAML paths, native 1440x932 WebP, and visual review. |
| Repository instructions | `AGENTS.md` | Concise pointer audit complete; the Debian/system-Python policy was already in the committed repository and was retained. |

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
- The audit changed four current reference pages: background jobs, TaskAPI,
  parental-guide downloading, and the historical Python-port plan. It did not
  add a redundant FAQ, cookbook, troubleshooting guide, roadmap, or YAML guide.

## Known verification gaps

- No clean-machine install or installed-console-script check was run. Source
  checkout commands are documented and verified; package-root console-script
  discovery remains a maintainer follow-up.
- No collection-size or performance benchmark was run. The native GUI capture
  was visually inspected, but it is workflow evidence rather than a scale claim.
- The root AGPL license file and `pyproject.toml` GPL metadata disagree. Resolve
  the intended license in packaging metadata before making a release claim.

## Final documentation checks

```bash
source ./source_me.sh && pytest tests/test_markdown_links.py \
  tests/test_readme_first_paragraph.py tests/test_guidance_doc_format.py \
  tests/test_ascii_compliance.py tests/test_whitespace.py \
  tests/test_function_typing.py tests/test_pyflakes_code_lint.py \
  tests/test_shebangs.py tests/test_source_file_line_limit.py -q
```

This final combined documentation, local-link containment, README, formatting,
ASCII, whitespace, helper typing/lint, shebang, and source-size gate passed:
**1208 passed**. `git diff --check` also passed after the documentation edits.
