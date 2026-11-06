# Release history

Development snapshots summarize work in this checkout. They are not published releases.

## v26.11 - 2026-11-06

### Highlights

- Split the movie chooser into focused query, results, preview, and prefetch components while
  preserving the existing matching workflow.
- Moved the existing next-movie search prefetch and cancellation code into the dedicated prefetch
  component, clarifying its responsibility for future maintenance.
- Refreshed the screenshot launcher and macOS prerequisites for a more dependable local setup.

### Notable fixes

- Repaired changelog rotation and removed obsolete maintenance tools from the modernization work.
- Removed unused Pillow and tabulate dependencies, synchronized unidecode metadata, and documented
  MediaInfo and yt-dlp in the macOS Brewfile.

### Validation

- Captured and inspected a native 1200x843 WebP GUI screenshot during launcher validation.

