# Task API

Developer reference for the background task manager (`moviemanager/ui/task_api.py`).

## Overview

`TaskAPI` wraps Qt's `QThreadPool` with a task-ID-based interface for submitting,
tracking, and cancelling background work. It provides two submission tiers:

- `submit()` -- fire-and-forget callable execution with signal routing
- `submit_job()` -- named job with metadata for UI display in the jobs dialog

## Priority constants

Defined at module level in [moviemanager/ui/task_api.py](../moviemanager/ui/task_api.py):

| Constant | Value | Typical use |
| --- | --- | --- |
| `PRIORITY_CRITICAL` | 100 | Scan, rename preview, rename execute |
| `PRIORITY_HIGH` | 75 | Batch scrape, refresh metadata |
| `PRIORITY_NORMAL` | 50 | Media probe, parental guides |
| `PRIORITY_LOW` | 25 | Downloads (artwork, trailers, subtitles) |
| `PRIORITY_BACKGROUND` | 0 | Prefetch images, thumbnail previews |

Higher values run first when the thread pool queue is congested.

## Public methods

| Method | Returns | Purpose |
| --- | --- | --- |
| `submit_job(name, fn, *args, _priority, **kwargs)` | `int` | Submit a named job with UI tracking |
| `submit(fn, *args, _priority, **kwargs)` | `int` | Submit a callable without metadata |
| `active_count` (property) | `int` | Count of queued or running jobs |
| `all_jobs` (property) | `list` | Job metadata dicts, newest first |
| `clear_completed()` | None | Remove all done/error jobs |
| `is_running(task_id)` | `bool` | True if task has not finished |
| `is_done(task_id)` | `bool` | True if task has a result or error |
| `cancel(task_id)` | None | Request cancellation |
| `get_result(task_id)` | object | Return value of completed callable |
| `get_worker(task_id)` | Worker or None | Access the Worker for extra signal connections |
| `shutdown()` | None | Cancel all tasks and drain the pool |

## Signals

| Signal | Parameters | When emitted |
| --- | --- | --- |
| `task_finished` | `(task_id: int, result: object)` | Callable returned successfully |
| `task_error` | `(task_id: int, error_text: str)` | Callable raised an exception |
| `task_progress` | `(task_id: int, current: int, total: int, message: str)` | Mid-task progress update |
| `job_list_changed` | (none) | Any job status transition |

## Job metadata fields

Each `submit_job()` call creates a metadata dict:

```python
{
    "name": str,              # display name (e.g. "Trailer: The Matrix")
    "status": str,            # "queued", "running", "done", or "error"
    "error_text": str,        # full traceback (empty if no error)
    "error_category": str,    # DownloadError category name (e.g. "no_url")
    "submitted_at": float,    # time.time() at submission
    "started_at": float|None, # time.time() when worker dequeued
    "priority": int,          # scheduling priority value
}
```

The `all_jobs` property adds `"task_id": int` to each dict.

## Error categorization

When a worker raises a `DownloadError` (from `moviemanager/api/download_errors.py`),
the worker prefixes the error signal with `CATEGORY:name\n`. The `_on_error()` handler:

1. Strips the prefix and stores the category in `error_category`
2. Keeps the traceback in `error_text` (without the prefix)
3. Appends a one-line entry to the error log file

## Error log file

**Path:** `/tmp/movie_manager_errors.log`

**Format:** pipe-delimited, one line per error, append-only.

```
YYYY-MM-DD HH:MM:SS | category | job_name | last_traceback_line
```

Example:

```
2026-03-03 14:23:45 | no_url | Trailer: The Matrix | No Url: No trailer URL for this movie
2026-03-03 14:24:12 | timeout | Subtitles: Inception | Timeout: OpenSubtitles API timed out
2026-03-03 14:25:00 | uncategorized | Batch scrape | AttributeError: 'NoneType' has no attribute 'title'
```

Non-download errors use `uncategorized` as the category label. The last traceback line
is truncated to 200 characters.

## Worker system

Workers live in [moviemanager/ui/workers.py](../moviemanager/ui/workers.py).

### Worker class

Generic `QRunnable` that executes a callable and emits signals:

| Signal | Parameters | Purpose |
| --- | --- | --- |
| `finished` | `(result: object)` | Success |
| `error` | `(error_text: str)` | Failure (full traceback) |
| `progress` | `(current: int, total: int, message: str)` | Progress update |
| `partial_result` | `(result: object)` | Streaming/incremental data |
| `started` | (none) | Worker dequeued from pool |

Workers guard all signal emissions against `RuntimeError` in case the receiver
widget was deleted while the worker was still running.

### ImageDownloadWorker

Specialized worker for downloading images with browser-like headers.
Emits `finished` with raw `bytes` on success.

### download_image_bytes()

Standalone helper that downloads image bytes synchronously. Used by callers
that manage their own threading.

## Download error categories

Defined in [moviemanager/api/download_errors.py](../moviemanager/api/download_errors.py).

| Category | Value label | Raised by |
| --- | --- | --- |
| `no_url` | No Url | `download_trailer()` -- movie has no trailer URL |
| `no_api_key` | No Api Key | `download_subtitles()` -- OpenSubtitles key missing |
| `no_imdb_id` | No Imdb Id | `download_subtitles()` -- movie has no IMDB ID |
| `no_results` | No Results | `download_subtitles()` -- search returned empty |
| `network_error` | Network Error | `download_subtitles()` -- connection failure |
| `api_error` | Api Error | `download_subtitles()` -- API request error |
| `download_failed` | Download Failed | `download_trailer()` -- yt-dlp non-zero exit |
| `timeout` | Timeout | Both -- request or subprocess timed out |
| `no_path` | No Path | Both -- movie has no folder path |

## Usage example

```python
import moviemanager.ui.task_api

task_api = moviemanager.ui.task_api.TaskAPI(max_workers=2)

# submit a named job at low priority
tid = task_api.submit_job(
    "Trailer: The Matrix",
    api.download_trailer, movie,
    _priority=moviemanager.ui.task_api.PRIORITY_LOW,
)

# connect to completion
task_api.task_finished.connect(on_done)
task_api.task_error.connect(on_error)
```
