# Modernization ledger

## Baseline

- Offscreen pytest baseline: 2,426 passed, 85 failed, one warning.
- The user removed the Podman disk-budget test; it stays removed.

## Workstreams

- Core: annotations, public API cleanup, and scraper/core standards.
- UI: chooser split, worker error handling, and Qt ownership.
- Tests: test-lane cleanup and regression coverage.
- Docs and tools: changelog rotation, links, and maintenance scripts.

## Evidence

- Changelog bullets: 586 before normalization, 588 after the two modernization entries.
- Day headings: seven before normalization, five after duplicate dates merged.
- Documentation, link, line-limit, and pyflakes checks: 397 passed.
- The chooser now separates navigation/scraping, active search/presentation, and background
  prefetch ownership. Its pre-split 899-line dialog warning was not used as a stopping point.
- Final fast lane: `source ./source_me.sh && pytest tests/` passed 2,535 tests.
- Final explicit E2E: GUI, CLI, and CLI integration runners passed. The GUI render at 900x550
  showed readable prematch metadata and actions without clipping or overlap.
- Final source checks: `git diff --check` and the staged diff check passed.

## Follow-up

- The vendored pytest policy still describes the removed Podman check as mandatory. The user
  explicitly removed that check; update the shared template separately if the policy changes.
