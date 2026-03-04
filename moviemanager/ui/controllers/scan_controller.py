"""Controller for directory scanning and media probe operations."""

# Standard Library
import time

# PIP3 modules
import PySide6.QtCore

# local repo modules
import moviemanager.core.media_probe
import moviemanager.core.settings
import moviemanager.ui.task_api


#============================================
class ScanController(PySide6.QtCore.QObject):
	"""Handles directory scanning, batch movie insertion, and media probing.

	Manages the scan lifecycle from directory selection through incremental
	movie delivery, post-scan finalization, badge computation, and
	background media probing for codec/resolution metadata.

	Signals:
		scan_started: Emitted when a scan begins, with directory path.
		scan_progress: Emitted for progress updates (current, total, message).
		scan_completed: Emitted when scan finishes with (total, scraped) counts.
		movies_added: Emitted when a batch of movies is ready for table insert.
		scan_error: Emitted when a scan fails with error text.
		badges_ready: Emitted with (unmatched, unorganized, incomplete) counts.
		probe_progress: Emitted for probe updates (current, total, message).
		probe_completed: Emitted when media probe finishes.
		probe_error: Emitted when media probe fails with error text.
	"""

	scan_started = PySide6.QtCore.Signal(str)
	scan_progress = PySide6.QtCore.Signal(int, int, str)
	scan_completed = PySide6.QtCore.Signal(int, int)
	movies_added = PySide6.QtCore.Signal(list)
	scan_error = PySide6.QtCore.Signal(str)
	badges_ready = PySide6.QtCore.Signal(tuple)
	probe_progress = PySide6.QtCore.Signal(int, int, str)
	probe_completed = PySide6.QtCore.Signal()
	probe_error = PySide6.QtCore.Signal(str)

	def __init__(self, api, task_api, parent=None):
		"""Initialize the scan controller.

		Args:
			api: MovieAPI facade instance.
			task_api: TaskAPI for background job submission.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._api = api
		self._task_api = task_api
		# task ID tracking
		self._scan_task_id = None
		self._probe_task_id = None
		self._badge_task_id = None
		# batch buffer for incremental scan results
		self._scan_batch_buffer = []
		# throttle progress signals from the scanner thread
		self._scan_progress_last_emit = 0.0
		self._scan_start_time = 0.0
		# batch flush timer
		self._scan_batch_timer = PySide6.QtCore.QTimer(self)
		self._scan_batch_timer.setInterval(200)
		self._scan_batch_timer.timeout.connect(self._flush_scan_batch)

	#============================================
	@property
	def scan_task_id(self) -> int:
		"""Return the current scan task ID."""
		return self._scan_task_id

	#============================================
	@property
	def probe_task_id(self) -> int:
		"""Return the current probe task ID."""
		return self._probe_task_id

	#============================================
	@property
	def badge_task_id(self) -> int:
		"""Return the current badge computation task ID."""
		return self._badge_task_id

	#============================================
	def set_api(self, api) -> None:
		"""Replace the MovieAPI instance (after settings change).

		Args:
			api: New MovieAPI facade instance.
		"""
		self._api = api

	#============================================
	def scan_directory(self, directory: str) -> None:
		"""Scan directory in a background thread.

		Movies are delivered incrementally via the movies_added signal
		so the table fills progressively as directories are scanned.

		Args:
			directory: Path to the directory to scan.
		"""
		self._scan_start_time = time.monotonic()
		self.scan_started.emit(directory)
		# run scan in background via TaskAPI
		self._scan_task_id = self._task_api.submit_job(
			f"Scanning {directory}",
			self._api.scan_directory, directory,
			progress_callback=self._on_scan_progress_callback,
			movie_callback=self._on_movie_found_callback,
			_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
		)
		# connect partial_result for incremental delivery
		scan_worker = self._task_api.get_worker(
			self._scan_task_id
		)
		scan_worker.signals.partial_result.connect(
			self._on_scan_partial
		)

	#============================================
	def _on_scan_progress_callback(
		self, current: int, message: str,
	) -> None:
		"""Progress callback invoked from scanner thread.

		Throttled to at most once per 500ms to avoid flooding the
		event loop when scanning directories with many subdirectories.

		Args:
			current: Current progress count.
			message: Progress description.
		"""
		now = time.monotonic()
		if now - self._scan_progress_last_emit < 0.5:
			return
		self._scan_progress_last_emit = now
		if self._scan_task_id is not None:
			worker = self._task_api.get_worker(
				self._scan_task_id
			)
			if worker:
				worker.signals.progress.emit(current, 0, message)

	#============================================
	def _on_movie_found_callback(self, movie) -> None:
		"""Callback invoked from worker thread when a movie is discovered.

		Emits partial_result signal to marshal delivery to the main thread.

		Args:
			movie: Discovered Movie instance.
		"""
		if self._scan_task_id is not None:
			worker = self._task_api.get_worker(
				self._scan_task_id
			)
			if worker:
				worker.signals.partial_result.emit(movie)

	#============================================
	def _on_scan_partial(self, movie) -> None:
		"""Buffer incremental movie delivery and flush in batches.

		Args:
			movie: Discovered Movie instance.
		"""
		self._scan_batch_buffer.append(movie)
		if not self._scan_batch_timer.isActive():
			self._scan_batch_timer.start()

	#============================================
	def _flush_scan_batch(self) -> None:
		"""Flush buffered movies into the table in small chunks.

		Each chunk inserts up to 50 movies then yields to the event
		loop via QTimer.singleShot(0, ...) so the UI stays responsive.
		"""
		if not self._scan_batch_buffer:
			self._scan_batch_timer.stop()
			return
		# swap out the buffer so new arrivals go into a fresh list
		batch = self._scan_batch_buffer
		self._scan_batch_buffer = []
		chunk_size = 50
		self._insert_chunk(batch, 0, chunk_size)

	#============================================
	def _insert_chunk(
		self, batch: list, offset: int, chunk_size: int,
	) -> None:
		"""Insert one chunk of movies and schedule the next chunk.

		Args:
			batch: Full list of movies from the flush buffer.
			offset: Start index into batch for this chunk.
			chunk_size: Number of movies per chunk.
		"""
		chunk = batch[offset:offset + chunk_size]
		if not chunk:
			return
		self.movies_added.emit(chunk)
		next_offset = offset + chunk_size
		if next_offset < len(batch):
			# yield to event loop, then insert next chunk
			PySide6.QtCore.QTimer.singleShot(
				0,
				lambda: self._insert_chunk(
					batch, next_offset, chunk_size
				),
			)

	#============================================
	def on_scan_done(self, movies) -> None:
		"""Handle scan completion with final cleanup.

		Movies were already delivered incrementally via partial_result,
		so this only flushes remaining buffers and defers finalization.

		Args:
			movies: Complete list of scanned movies (from task result).
		"""
		self._scan_task_id = None
		# flush any remaining buffered movies via chunked insertion
		self._scan_batch_timer.stop()
		if self._scan_batch_buffer:
			final_batch = self._scan_batch_buffer
			self._scan_batch_buffer = []
			chunk_size = 50
			self._insert_chunk(final_batch, 0, chunk_size)
		# defer post-scan cleanup until event loop drains insert chunks
		PySide6.QtCore.QTimer.singleShot(0, self._finalize_scan)

	#============================================
	def _finalize_scan(self) -> None:
		"""Post-scan cleanup after all chunked inserts are done."""
		finalize_start = time.monotonic()
		t0 = time.monotonic()
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		counts_ms = (time.monotonic() - t0) * 1000
		# emit completion signal with counts
		self.scan_completed.emit(total, scraped)
		# update toolbar badges in a background thread
		self._badge_task_id = self._task_api.submit(
			self._compute_badge_counts,
			self._api.get_movies(),
		)
		# launch background media probe for codec/resolution fields
		self.start_media_probe()
		# timing diagnostics
		finalize_ms = (time.monotonic() - finalize_start) * 1000
		total_ms = (time.monotonic() - self._scan_start_time) * 1000
		print(
			f"[scan] finalize {finalize_ms:.0f}ms "
			f"(counts={counts_ms:.0f}, badges=bg), "
			f"total {total_ms:.0f}ms"
		)

	#============================================
	def start_media_probe(self) -> None:
		"""Launch background job to probe video files for codec metadata.

		Uses TaskAPI so the probe appears in the Jobs dialog with
		progress tracking.
		"""
		movies = self._api.get_movies()
		if not movies:
			return
		self._probe_task_id = self._task_api.submit_job(
			"Media probe",
			moviemanager.core.media_probe.probe_movie_list,
			movies,
			progress_callback=self._on_probe_progress_callback,
			_priority=moviemanager.ui.task_api.PRIORITY_NORMAL,
		)

	#============================================
	def _on_probe_progress_callback(
		self, current: int, total: int, message: str,
	) -> None:
		"""Progress callback invoked from probe worker thread.

		Args:
			current: Current progress count.
			total: Total items to probe.
			message: Progress description.
		"""
		worker = self._task_api.get_worker(self._probe_task_id)
		if worker:
			worker.signals.progress.emit(current, total, message)

	#============================================
	def on_probe_task_progress(
		self, task_id: int, current: int, total: int, message: str,
	) -> None:
		"""Handle probe progress updates on the main thread.

		Args:
			task_id: The task ID reporting progress.
			current: Current progress count.
			total: Total items to probe.
			message: Progress description.
		"""
		if task_id != self._probe_task_id:
			return
		self.probe_progress.emit(current, total, message)

	#============================================
	def on_probe_task_finished(
		self, task_id: int, result,
	) -> None:
		"""Handle probe completion: emit signal and clear task ID.

		Args:
			task_id: The completed task ID.
			result: Task result (unused).
		"""
		if task_id != self._probe_task_id:
			return
		self._probe_task_id = None
		self.probe_completed.emit()

	#============================================
	def on_probe_task_error(
		self, task_id: int, error_text: str,
	) -> None:
		"""Handle probe error: emit signal and clear task ID.

		Args:
			task_id: The failed task ID.
			error_text: Error traceback text.
		"""
		if task_id != self._probe_task_id:
			return
		self._probe_task_id = None
		self.probe_error.emit(error_text)

	#============================================
	@staticmethod
	def _compute_badge_counts(movies: list) -> tuple:
		"""Count badge categories in a background thread.

		Pure data work with no Qt calls. Returns counts for
		unmatched, unorganized, and incomplete movies.

		Args:
			movies: List of Movie objects to count.

		Returns:
			Tuple of (unmatched, unorganized, incomplete) counts.
		"""
		settings = moviemanager.core.settings.load_settings()
		unmatched = 0
		unorganized = 0
		incomplete = 0
		t0 = time.monotonic()
		for m in movies:
			if not m.scraped:
				unmatched += 1
			else:
				organized = m.check_organized(settings)
				if not organized:
					unorganized += 1
				# only check poster/trailer for organized movies
				if organized and not (
					m.has_poster and m.has_trailer
				):
					incomplete += 1
		badges_ms = (time.monotonic() - t0) * 1000
		print(f"[scan] badges {badges_ms:.0f}ms (background)")
		result = (unmatched, unorganized, incomplete)
		return result

	#============================================
	def on_badge_task_finished(
		self, task_id: int, result,
	) -> None:
		"""Handle badge computation completion.

		Args:
			task_id: The completed task ID.
			result: Tuple of (unmatched, unorganized, incomplete).
		"""
		if task_id != self._badge_task_id:
			return
		self._badge_task_id = None
		self.badges_ready.emit(result)

	#============================================
	def on_scan_error(self, error_text: str) -> None:
		"""Handle scan error by emitting signal.

		Args:
			error_text: Error traceback text.
		"""
		self._scan_task_id = None
		self.scan_error.emit(error_text)

	#============================================
	def cancel(self) -> None:
		"""Cancel any running scan or probe tasks."""
		for tid in (self._scan_task_id, self._probe_task_id):
			if tid is not None:
				self._task_api.cancel(tid)
		self._scan_task_id = None
		self._probe_task_id = None

	#============================================
	def update_badges(self) -> None:
		"""Recompute toolbar badge counts in the background."""
		movies = self._api.get_movies()
		settings = moviemanager.core.settings.load_settings()
		# count all three categories in a single pass
		unmatched = 0
		unorganized = 0
		incomplete = 0
		for m in movies:
			if not m.scraped:
				unmatched += 1
			else:
				organized = m.check_organized(settings)
				if not organized:
					unorganized += 1
				if organized and not (
					m.has_poster and m.has_trailer
				):
					incomplete += 1
		result = (unmatched, unorganized, incomplete)
		self.badges_ready.emit(result)
