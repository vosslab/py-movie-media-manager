# Background jobs

How the background jobs system works from a user perspective.

## Overview

Long-running operations (scanning, scraping, downloading) run in background threads
so the main window stays responsive. A jobs indicator in the status bar shows active
job count and opens the jobs dialog on click.

## Jobs dialog

Click the status bar indicator or use the menu to open the jobs dialog. It shows a
table of all background jobs with live updates.

### Table columns

| Column | Content |
| --- | --- |
| Name | Job description (e.g. "Trailer: The Matrix", "Scanning /Movies") |
| Priority | Scheduling tier: Critical, High, Normal, Low, or Background |
| Status | Current state (see below) |
| Queued | Time since job was submitted |
| Active | Time since worker started executing ("--" while queued) |

### Status values

- **Queued** -- waiting in the thread pool queue
- **Running...** -- actively executing
- **Done** -- completed successfully
- **Error: Category** -- failed with a categorized reason (e.g. "Error: No Url")
- **Error: detail** -- failed with an uncategorized exception (truncated)

Hover over any error row to see the full traceback in a tooltip.

### Buttons

- **Error Summary** -- shows a popup with error counts grouped by category
- **Clear Completed** -- removes all finished (done and error) jobs from the list
- **Close** -- closes the dialog (jobs keep running)

## Job types and priorities

Jobs run in priority order when the queue is congested. Two worker threads
run concurrently by default.

| Priority | Jobs |
| --- | --- |
| Critical | Directory scan, rename preview, rename execute |
| High | Batch scrape, refresh metadata |
| Normal | Media probe, parental guide fetch |
| Low | Artwork, trailer, and subtitle downloads |
| Background | Image prefetch, thumbnail previews |

## Download error categories

When trailer or subtitle downloads fail, the jobs dialog shows a specific reason
instead of a raw traceback.

| Category | Meaning |
| --- | --- |
| No Url | Movie has no trailer URL (needs scraping first) |
| No Api Key | OpenSubtitles API key not configured in settings |
| No Imdb Id | Movie has no IMDB ID (needs scraping first) |
| No Results | Subtitle search returned no matches |
| Network Error | Connection failure during subtitle download |
| Api Error | Subtitle API returned an error response |
| Download Failed | yt-dlp exited with an error (hover for stderr detail) |
| Timeout | Download or API call timed out |
| No Path | Movie has no folder path on disk |

## Error summary

Click "Error Summary" in the jobs dialog to see a breakdown like:

```
Total errors: 54

  No Url: 40
  Download Failed: 10
  Timeout: 4
```

This helps identify patterns -- for example, 40 movies missing trailer URLs
means they need scraping, not a download retry.

## Error log file

All job errors are appended to `/tmp/movie_manager_errors.log` with one line per
error. The log persists across sessions and can be reviewed after batch operations.

Format:

```
2026-03-03 14:23:45 | no_url | Trailer: The Matrix | No Url: No trailer URL for this movie
```

Fields: `timestamp | category | job_name | error_summary`

## Cancellation and shutdown

- Jobs continue running when the jobs dialog is closed
- Closing the main window with active jobs shows a confirmation prompt
- On quit, all running workers receive a cancellation request
