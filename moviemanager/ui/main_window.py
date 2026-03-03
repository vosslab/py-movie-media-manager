"""Main application window."""

# Standard Library
import os
import time
import shutil
import importlib.metadata

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.media_probe
import moviemanager.core.settings
import moviemanager.ui.task_api
import moviemanager.ui.dialogs.download_dialog
import moviemanager.ui.dialogs.jobs_dialog
import moviemanager.ui.dialogs.movie_chooser
import moviemanager.ui.dialogs.movie_editor
import moviemanager.ui.dialogs.rename_preview
import moviemanager.ui.dialogs.settings_dialog
import moviemanager.ui.menu_builder
import moviemanager.ui.movies.movie_panel
import moviemanager.ui.theme
import moviemanager.ui.widgets.status_bar
import moviemanager.ui.workers


#============================================
class MainWindow(PySide6.QtWidgets.QMainWindow):
	"""Main application window with menu, movie panel, and status bar."""

	def __init__(self, settings, directory: str = "", parent=None):
		super().__init__(parent)
		self._settings = settings
		self._api = moviemanager.api.movie_api.MovieAPI(settings)
		self.setWindowTitle("Movie Media Manager")
		self.resize(1200, 800)
		# accept drag-and-drop of directories (#19)
		self.setAcceptDrops(True)
		# central widget
		self._movie_panel = (
			moviemanager.ui.movies.movie_panel.MoviePanel()
		)
		self.setCentralWidget(self._movie_panel)
		# connect movie panel signals
		self._movie_panel.open_folder_requested.connect(
			self._open_directory
		)
		self._movie_panel.movie_double_clicked.connect(
			self._edit_selected
		)
		self._movie_panel.context_action.connect(
			self._on_context_action
		)
		# connect checked count to status bar
		self._movie_panel.checked_changed.connect(
			self._on_checked_changed
		)
		# shared task API for background job tracking
		self._task_api = moviemanager.ui.task_api.TaskAPI(
			max_workers=2, parent=self
		)
		# jobs dialog (created on demand, reused)
		self._jobs_dialog = None
		# status bar
		self._status = moviemanager.ui.widgets.status_bar.StatusBar()
		self._status.cancel_requested.connect(self._cancel_operation)
		# connect jobs button to show jobs dialog
		self._status.jobs_clicked.connect(self._show_jobs_dialog)
		# update jobs count when job list changes
		self._task_api.job_list_changed.connect(
			self._update_jobs_count
		)
		# central task dispatcher for all TaskAPI signals
		self._task_api.task_finished.connect(self._on_task_finished)
		self._task_api.task_error.connect(self._on_task_error)
		self._task_api.task_progress.connect(self._on_task_progress)
		self.setStatusBar(self._status)
		# track background task IDs by operation type
		self._scan_task_id = None
		self._scrape_task_id = None
		self._refresh_task_id = None
		self._pg_task_id = None
		self._download_task_ids = []
		self._probe_task_id = None
		self._rename_task_id = None
		self._rename_mode = None
		self._badge_task_id = None
		# batch buffer for incremental scan results
		self._scan_batch_buffer = []
		# throttle progress signals from the scanner thread
		self._scan_progress_last_emit = 0.0
		self._scan_batch_timer = PySide6.QtCore.QTimer(self)
		# flush every 200ms so movies appear quickly in the table
		self._scan_batch_timer.setInterval(200)
		self._scan_batch_timer.timeout.connect(self._flush_scan_batch)
		# menu bar
		self._setup_menus()
		# toolbar
		self._setup_toolbar()
		# restore window state (#20)
		self._restore_state()
		# track current directory for re-scan and title
		self._current_directory = ""
		# rename history for undo (stack of rename batches)
		self._rename_history = []
		# load directory if provided, otherwise auto-open last folder
		if directory:
			self._scan_directory(directory)
		elif self._settings.last_directory:
			last_dir = self._settings.last_directory
			if os.path.isdir(last_dir):
				self._scan_directory(last_dir)

	#============================================
	def _setup_menus(self):
		"""Create menu bar from YAML configuration."""
		stored = moviemanager.ui.menu_builder.build_menus(self)
		self._undo_rename_action = stored.get("undo_rename_action")
		self._dark_mode_action = stored.get("dark_mode_action")

	#============================================
	def _setup_toolbar(self):
		"""Create toolbar with labeled icons in 3-step workflow order.

		Layout: Open | sep | 1. Match | 2. Organize | 3. Download | spacer | Settings | Quit
		"""
		toolbar = self.addToolBar("Main")
		toolbar.setObjectName("MainToolBar")
		toolbar.setMovable(False)
		# text-under-icon layout with larger icons
		toolbar.setToolButtonStyle(
			PySide6.QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon
		)
		toolbar.setIconSize(PySide6.QtCore.QSize(32, 32))
		# themed icons with system fallbacks
		# open button
		open_btn = PySide6.QtGui.QAction("Open", self)
		open_icon = PySide6.QtGui.QIcon.fromTheme(
			"folder-open",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon
			),
		)
		open_btn.setIcon(open_icon)
		open_btn.setToolTip("Open a movie directory (Ctrl+O)")
		open_btn.triggered.connect(self._open_directory)
		toolbar.addAction(open_btn)
		# separator between Open and workflow actions
		toolbar.addSeparator()
		# step 1: match button -- magnifying glass icon
		self._match_btn = PySide6.QtGui.QAction("1. Match", self)
		match_icon = PySide6.QtGui.QIcon.fromTheme(
			"edit-find",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView
			),
		)
		self._match_btn.setIcon(match_icon)
		self._match_btn.setToolTip(
			"Match movies to IMDB/TMDB (Ctrl+Shift+S)"
		)
		self._match_btn.triggered.connect(self._scrape_selected)
		toolbar.addAction(self._match_btn)
		# step 2: organize button -- folder icon
		self._organize_btn = PySide6.QtGui.QAction(
			"2. Organize", self
		)
		organize_icon = PySide6.QtGui.QIcon.fromTheme(
			"folder-new",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogNewFolder
			),
		)
		self._organize_btn.setIcon(organize_icon)
		self._organize_btn.setToolTip(
			"Organize movies into folders (F2)"
		)
		self._organize_btn.triggered.connect(self._rename_selected)
		toolbar.addAction(self._organize_btn)
		# step 3: download button -- download arrow icon
		self._download_btn = PySide6.QtGui.QAction(
			"3. Download", self
		)
		download_icon = PySide6.QtGui.QIcon.fromTheme(
			"go-down",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_ArrowDown
			),
		)
		self._download_btn.setIcon(download_icon)
		self._download_btn.setToolTip(
			"Download artwork, trailers, and subtitles"
		)
		self._download_btn.triggered.connect(self._download_content)
		toolbar.addAction(self._download_btn)
		# separator between workflow and utility buttons
		toolbar.addSeparator()
		# flexible spacer to push settings/quit to the right
		spacer = PySide6.QtWidgets.QWidget()
		spacer.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Expanding,
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
		)
		toolbar.addWidget(spacer)
		toolbar.addSeparator()
		# refresh metadata button -- re-fetch IMDB/TMDB data
		refresh_meta_btn = PySide6.QtGui.QAction("Refresh Metadata", self)
		refresh_meta_icon = PySide6.QtGui.QIcon.fromTheme(
			"view-refresh",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_BrowserReload
			),
		)
		refresh_meta_btn.setIcon(refresh_meta_icon)
		refresh_meta_btn.setToolTip(
			"Re-fetch metadata for matched movies from IMDB/TMDB"
		)
		refresh_meta_btn.triggered.connect(self._refresh_metadata)
		toolbar.addAction(refresh_meta_btn)
		# fetch parental guide button -- standalone IMDB parental guide
		pg_btn = PySide6.QtGui.QAction("Parental Guide", self)
		pg_icon = PySide6.QtGui.QIcon.fromTheme(
			"security-medium",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning
			),
		)
		pg_btn.setIcon(pg_icon)
		pg_btn.setToolTip(
			"Fetch parental guide data from IMDB for matched movies"
		)
		pg_btn.triggered.connect(self._fetch_parental_guides)
		toolbar.addAction(pg_btn)
		# refresh file stats button -- re-probe video files
		refresh_stats_btn = PySide6.QtGui.QAction("Refresh Stats", self)
		refresh_stats_icon = PySide6.QtGui.QIcon.fromTheme(
			"document-properties",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileIcon
			),
		)
		refresh_stats_btn.setIcon(refresh_stats_icon)
		refresh_stats_btn.setToolTip(
			"Re-probe video files for codec, resolution, and duration"
		)
		refresh_stats_btn.triggered.connect(self._refresh_file_stats)
		toolbar.addAction(refresh_stats_btn)
		toolbar.addSeparator()
		# settings button -- gear icon
		settings_btn = PySide6.QtGui.QAction("Settings", self)
		settings_icon = PySide6.QtGui.QIcon.fromTheme(
			"preferences-system",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon
			),
		)
		settings_btn.setIcon(settings_icon)
		settings_btn.setToolTip("Open settings (Ctrl+,)")
		settings_btn.triggered.connect(self._show_settings)
		toolbar.addAction(settings_btn)
		# dark mode toggle -- checkable action
		self._dark_toggle = PySide6.QtGui.QAction(
			"Dark Mode", self
		)
		self._dark_toggle.setCheckable(True)
		is_dark = (
			hasattr(self, "_settings")
			and self._settings.theme == "dark"
		)
		self._dark_toggle.setChecked(is_dark)
		dark_icon = PySide6.QtGui.QIcon.fromTheme(
			"weather-clear-night",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon
			),
		)
		self._dark_toggle.setIcon(dark_icon)
		self._dark_toggle.setToolTip("Toggle dark/light theme")
		self._dark_toggle.triggered.connect(self._toggle_dark_mode)
		toolbar.addAction(self._dark_toggle)
		# quit button -- exit door icon
		quit_btn = PySide6.QtGui.QAction("Quit", self)
		quit_icon = PySide6.QtGui.QIcon.fromTheme(
			"application-exit",
			self.style().standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton
			),
		)
		quit_btn.setIcon(quit_icon)
		quit_btn.setToolTip("Quit application (Ctrl+Q)")
		quit_btn.triggered.connect(self.close)
		toolbar.addAction(quit_btn)

	#============================================
	def _open_directory(self):
		"""Open a directory chooser and scan."""
		directory = PySide6.QtWidgets.QFileDialog.getExistingDirectory(
			self, "Select Movie Directory"
		)
		if directory:
			self._scan_directory(directory)

	#============================================
	def _scan_directory(self, directory: str):
		"""Scan directory in a background thread (#1).

		Movies are delivered incrementally via the partial_result signal
		so the table fills progressively as directories are scanned.
		"""
		self._scan_start_time = time.monotonic()
		self._current_directory = directory
		# save last opened directory to settings
		self._settings.last_directory = directory
		moviemanager.core.settings.save_settings(self._settings)
		# clear rename history on directory change
		self._rename_history.clear()
		self._undo_rename_action.setEnabled(False)
		# clear table and prepare for incremental loading
		self._movie_panel.set_movies([])
		# disable sorting during scan to avoid O(N log N) sort on each batch flush
		self._movie_panel.set_sorting_enabled(False)
		self._status.showMessage(f"Scanning {directory}...")
		self._status.show_progress(0, 0, f"Scanning {directory}...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# run scan in background via TaskAPI (#1)
		self._scan_task_id = self._task_api.submit_job(
			f"Scanning {directory}",
			self._api.scan_directory, directory,
			progress_callback=self._on_scan_progress_callback,
			movie_callback=self._on_movie_found_callback,
			_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
		)
		# connect partial_result directly from the worker for incremental delivery
		scan_worker = self._task_api.get_worker(self._scan_task_id)
		scan_worker.signals.partial_result.connect(self._on_scan_partial)

	#============================================
	def _on_scan_progress_callback(self, current: int, message: str) -> None:
		"""Progress callback invoked from scanner thread.

		Emits progress signal to update the UI on the main thread.
		Throttled to at most once per 500ms to avoid flooding the
		event loop when scanning directories with many subdirectories.
		"""
		now = time.monotonic()
		# emit at most every 500ms to avoid flooding the event loop
		if now - self._scan_progress_last_emit < 0.5:
			return
		self._scan_progress_last_emit = now
		if self._scan_task_id is not None:
			worker = self._task_api.get_worker(self._scan_task_id)
			if worker:
				worker.signals.progress.emit(current, 0, message)

	#============================================
	def _on_scan_progress(self, current: int, total: int, message: str) -> None:
		"""Handle scan progress updates on the main thread."""
		self._status.show_progress(current, total, message)

	#============================================
	def _on_movie_found_callback(self, movie) -> None:
		"""Callback invoked from worker thread when a movie is discovered.

		Emits partial_result signal to marshal delivery to the main thread.
		"""
		if self._scan_task_id is not None:
			worker = self._task_api.get_worker(self._scan_task_id)
			if worker:
				worker.signals.partial_result.emit(movie)

	#============================================
	def _on_scan_partial(self, movie) -> None:
		"""Buffer incremental movie delivery and flush in batches."""
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
	def _insert_chunk(self, batch: list, offset: int, chunk_size: int) -> None:
		"""Insert one chunk of movies and schedule the next chunk.

		Args:
			batch: Full list of movies from the flush buffer.
			offset: Start index into batch for this chunk.
			chunk_size: Number of movies per chunk.
		"""
		chunk = batch[offset:offset + chunk_size]
		if not chunk:
			return
		self._movie_panel.append_movies(chunk)
		next_offset = offset + chunk_size
		if next_offset < len(batch):
			# yield to event loop, then insert next chunk
			PySide6.QtCore.QTimer.singleShot(
				0, lambda: self._insert_chunk(batch, next_offset, chunk_size)
			)

	#============================================
	def _on_scan_done(self, movies) -> None:
		"""Handle scan completion with final cleanup.

		Movies were already delivered incrementally via partial_result,
		so this only updates status bar counts and window title.
		"""
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
		# re-enable sorting now that all movies are loaded;
		# Qt triggers a single sort using the existing sort indicator
		t0 = time.monotonic()
		self._movie_panel.set_sorting_enabled(True)
		sort_ms = (time.monotonic() - t0) * 1000
		self.unsetCursor()
		self._status.hide_progress()
		t0 = time.monotonic()
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		counts_ms = (time.monotonic() - t0) * 1000
		self._status.set_movie_count(total, scraped)
		# update window title with current directory
		self.setWindowTitle(
			f"Movie Media Manager - {self._current_directory}"
		)
		# transient success message (#24)
		self._status.showMessage(
			f"Scan complete: {total} movies found", 3000
		)
		# update toolbar badges in a background thread
		self._badge_task_id = self._task_api.submit(
			self._compute_badge_counts,
			self._api.get_movies(),
		)
		# launch background media probe for codec/resolution fields
		self._start_media_probe()
		# per-step and total timing
		finalize_ms = (time.monotonic() - finalize_start) * 1000
		total_ms = (time.monotonic() - self._scan_start_time) * 1000
		print(
			f"[scan] finalize {finalize_ms:.0f}ms "
			f"(sort={sort_ms:.0f}, counts={counts_ms:.0f}, "
			f"badges=bg), "
			f"total {total_ms:.0f}ms"
		)

	#============================================
	def _start_media_probe(self) -> None:
		"""Launch background job to probe video files for codec metadata.

		Uses TaskAPI so the probe appears in the Jobs dialog with
		progress tracking. Movies appear in the table immediately
		after scan; codec/resolution fields populate in the background.
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
		# progress/finished/error routed through _on_task_* dispatchers

	#============================================
	def _on_probe_progress_callback(
		self, current: int, total: int, message: str,
	) -> None:
		"""Progress callback invoked from probe worker thread.

		Emits progress signal via the TaskAPI worker to marshal
		GUI update to the main thread.
		"""
		worker = self._task_api.get_worker(self._probe_task_id)
		if worker:
			worker.signals.progress.emit(current, total, message)

	#============================================
	def _on_probe_task_progress(
		self, task_id: int, current: int, total: int, message: str,
	) -> None:
		"""Handle probe progress updates on the main thread.

		Refreshes the table every 5 files so codec/duration fields
		appear progressively as files are probed.
		"""
		if task_id != self._probe_task_id:
			return
		self._status.show_progress(current, total, message)
		# refresh table less frequently; Qt repaints asynchronously
		if current % 25 == 0 or current == total:
			self._movie_panel.refresh_data()

	#============================================
	def _on_probe_task_finished(self, task_id: int, result) -> None:
		"""Handle probe completion: refresh table and clear status."""
		if task_id != self._probe_task_id:
			return
		self._probe_task_id = None
		self._status.hide_progress()
		# refresh table cells with newly populated codec fields
		self._movie_panel.refresh_data()
		self._status.showMessage("Media probe complete", 3000)

	#============================================
	def _on_probe_task_error(
		self, task_id: int, error_text: str,
	) -> None:
		"""Handle probe error: clear status and show error message."""
		if task_id != self._probe_task_id:
			return
		self._probe_task_id = None
		self._status.hide_progress()
		# show truncated error in status bar
		msg = f"Media probe error: {error_text[:80]}"
		self._status.showMessage(msg, 5000)

	#============================================
	def _on_task_finished(self, task_id: int, result) -> None:
		"""Route task completion to the appropriate handler."""
		if task_id == self._scan_task_id:
			self._scan_task_id = None
			self._on_scan_done(result)
		elif task_id == self._scrape_task_id:
			self._scrape_task_id = None
			self._on_batch_scrape_done(result)
		elif task_id == self._refresh_task_id:
			self._refresh_task_id = None
			self._on_refresh_metadata_done(result)
		elif task_id == self._pg_task_id:
			self._pg_task_id = None
			self._on_fetch_parental_guides_done(result)
		elif task_id == self._probe_task_id:
			self._on_probe_task_finished(task_id, result)
		elif task_id in self._download_task_ids:
			self._on_download_job_done(task_id, result)
		elif task_id == self._badge_task_id:
			self._badge_task_id = None
			self._apply_badge_counts(result)
		elif task_id == self._rename_task_id:
			self._rename_task_id = None
			mode = self._rename_mode
			self._rename_mode = None
			if mode == "single_preview":
				self._on_rename_preview_done(result)
			elif mode == "single_exec":
				self._on_rename_exec_done(result)
			elif mode == "batch_preview":
				self._on_batch_rename_preview_done(result)
			elif mode == "batch_exec":
				self._on_batch_rename_exec_done(result)

	#============================================
	def _on_task_error(self, task_id: int, error_text: str) -> None:
		"""Route task errors to the appropriate handler."""
		if task_id in (self._scan_task_id, self._scrape_task_id,
					self._refresh_task_id, self._pg_task_id):
			self._on_scan_error(error_text)
		elif task_id == self._probe_task_id:
			self._on_probe_task_error(task_id, error_text)
		elif task_id == self._rename_task_id:
			self._rename_task_id = None
			mode = self._rename_mode
			self._rename_mode = None
			if mode in ("single_preview", "batch_preview"):
				self._on_rename_preview_error(error_text)
			else:
				self._on_rename_exec_error(error_text)

	#============================================
	def _on_task_progress(self, task_id: int, cur: int, tot: int, msg: str) -> None:
		"""Route task progress to the appropriate handler."""
		if task_id in (self._scan_task_id, self._scrape_task_id,
					self._refresh_task_id, self._pg_task_id):
			self._on_scan_progress(cur, tot, msg)
		elif task_id == self._probe_task_id:
			self._on_probe_task_progress(task_id, cur, tot, msg)

	#============================================
	def _on_checked_changed(self, checked: int, total: int) -> None:
		"""Update status bar when checkbox selection changes.

		Args:
			checked: Number of checked movies.
			total: Total number of visible movies.
		"""
		if checked > 0:
			self._status.set_checked_count(checked, total)
		else:
			# restore default movie count display using cached counts
			self._refresh_status_counts()

	#============================================
	def _refresh_status_counts(self) -> None:
		"""Update status bar movie/scraped counts from API."""
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		self._status.set_movie_count(total, scraped)

	#============================================
	def _update_toolbar_badges(self) -> None:
		"""Update toolbar button text with workflow counts.

		Shows number of movies needing action at each step:
		Match (unmatched), Organize (matched but unorganized),
		Download (organized but incomplete).
		Single pass over the movie list for all three counts.
		"""
		movies = self._api.get_movies()
		# load settings once to avoid per-movie YAML reads
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
				# only check poster/trailer for organized movies
				if organized and not (m.has_poster and m.has_trailer):
					incomplete += 1
		# update button labels
		if unmatched > 0:
			self._match_btn.setText(f"1. Match ({unmatched})")
		else:
			self._match_btn.setText("1. Match")
		if unorganized > 0:
			self._organize_btn.setText(
				f"2. Organize ({unorganized})"
			)
		else:
			self._organize_btn.setText("2. Organize")
		if incomplete > 0:
			self._download_btn.setText(
				f"3. Download ({incomplete})"
			)
		else:
			self._download_btn.setText("3. Download")

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
		import moviemanager.core.settings
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
				if organized and not (m.has_poster and m.has_trailer):
					incomplete += 1
		badges_ms = (time.monotonic() - t0) * 1000
		print(f"[scan] badges {badges_ms:.0f}ms (background)")
		result = (unmatched, unorganized, incomplete)
		return result

	#============================================
	def _apply_badge_counts(self, counts: tuple) -> None:
		"""Apply badge counts to toolbar buttons on the main thread.

		Args:
			counts: Tuple of (unmatched, unorganized, incomplete).
		"""
		unmatched, unorganized, incomplete = counts
		if unmatched > 0:
			self._match_btn.setText(f"1. Match ({unmatched})")
		else:
			self._match_btn.setText("1. Match")
		if unorganized > 0:
			self._organize_btn.setText(
				f"2. Organize ({unorganized})"
			)
		else:
			self._organize_btn.setText("2. Organize")
		if incomplete > 0:
			self._download_btn.setText(
				f"3. Download ({incomplete})"
			)
		else:
			self._download_btn.setText("3. Download")

	#============================================
	def _on_scan_error(self, error_text: str) -> None:
		"""Handle scan error with user-friendly message (#2)."""
		self.unsetCursor()
		self._status.hide_progress()
		self._show_error("Scan Error", error_text)

	#============================================
	def _show_error(self, title: str, error_text: str) -> None:
		"""Show a user-friendly error dialog with detail text.

		Extracts the last line (actual error) for the summary and
		puts the full traceback in the detail section.

		Args:
			title: Dialog window title.
			error_text: Full traceback or error text.
		"""
		# extract the last non-empty line as the summary
		lines = error_text.strip().splitlines()
		summary = lines[-1] if lines else "Unknown error"
		msg = PySide6.QtWidgets.QMessageBox(self)
		msg.setIcon(PySide6.QtWidgets.QMessageBox.Icon.Critical)
		msg.setWindowTitle(title)
		msg.setText(summary)
		msg.setDetailedText(error_text)
		msg.exec()

	#============================================
	def _scrape_selected(self):
		"""Scrape metadata for selected or checked movies.

		If multiple movies are checked, opens the chooser dialog in
		batch mode with Previous/Skip/Next navigation. Otherwise
		opens it for the single selected movie.
		"""
		# unified resolution: checked > selected > single
		checked_movies = self._movie_panel.get_chosen_movies()
		if len(checked_movies) > 1:
			# batch mode: pass movies as a list
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				checked_movies[0], self._api, self,
				movie_list=checked_movies,
				task_api=self._task_api,
			)
		else:
			# single movie mode
			movie = self._movie_panel.get_selected_movie()
			if not movie:
				PySide6.QtWidgets.QMessageBox.information(
					self, "No Selection",
					"Please select a movie first."
				)
				return
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movie, self._api, self,
				task_api=self._task_api,
			)
		if dialog.exec() == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			# refresh table data in-place (preserves selection)
			self._movie_panel.refresh_data()
			self._refresh_status_counts()
			# show summary with workflow hint
			if len(checked_movies) > 1:
				batch_results = dialog.get_batch_results()
				count = sum(1 for v in batch_results.values() if v)
				self._status.showMessage(
					f"Matched {count}/{len(checked_movies)} movies"
					" -- ready to organize (Step 2)",
					8000,
				)
			else:
				self._status.showMessage(
					"Match complete -- ready to organize (Step 2)",
					5000,
				)
			self._update_toolbar_badges()

	#============================================
	def _edit_selected(self):
		"""Edit metadata for selected movie."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection",
				"Please select a movie first."
			)
			return
		dialog = moviemanager.ui.dialogs.movie_editor.MovieEditorDialog(
			movie, self
		)
		if dialog.exec() == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			# refresh table data in-place (preserves selection)
			self._movie_panel.refresh_data()
			# transient success message (#24)
			self._status.showMessage("Metadata saved", 3000)

	#============================================
	def _rename_selected(self):
		"""Organize selected movie files into proper folder structure.

		Supports batch mode when multiple movies are checked. Collects
		rename pairs for all checked movies and shows a combined
		preview dialog. Falls back to single-movie mode.
		"""
		# unified resolution: checked > selected > single
		checked_movies = self._movie_panel.get_chosen_movies()
		# batch mode: multiple movies
		if len(checked_movies) > 1:
			self._rename_batch(checked_movies)
			return
		# single mode: one selected movie
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection",
				"Please select a movie first."
			)
			return
		# compute rename preview in background thread
		self._status.showMessage("Computing rename preview...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# store movie ref for the callback
		self._pending_rename_movie = movie
		self._rename_mode = "single_preview"
		self._rename_task_id = self._task_api.submit_job(
			"Rename preview", self._api.rename_movie, movie,
			dry_run=True,
			_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
		)

	#============================================
	def _on_rename_preview_done(self, pairs: list) -> None:
		"""Show rename preview dialog after background dry-run.

		Args:
			pairs: List of (source, dest) path tuples from dry-run.
		"""
		self.unsetCursor()
		self._status.clearMessage()
		movie = self._pending_rename_movie
		self._pending_rename_movie = None
		if not pairs:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Organize", "No files to organize."
			)
			return
		# show rename preview dialog
		dialog = moviemanager.ui.dialogs.rename_preview.RenamePreviewDialog(
			pairs, self
		)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			# execute rename in background
			self._status.showMessage("Organizing files...")
			self.setCursor(
				PySide6.QtCore.Qt.CursorShape.WaitCursor
			)
			# store pairs for undo on completion
			self._pending_rename_pairs = pairs
			self._rename_mode = "single_exec"
			self._rename_task_id = self._task_api.submit_job(
				"Renaming movie", self._api.rename_movie, movie,
				dry_run=False,
				_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
			)

	#============================================
	def _on_rename_preview_error(self, error_text: str) -> None:
		"""Handle error from rename dry-run computation."""
		self.unsetCursor()
		self._status.clearMessage()
		self._pending_rename_movie = None
		self._show_error("Organize Error", error_text)

	#============================================
	def _on_rename_exec_done(self, result) -> None:
		"""Handle rename execution completion."""
		self.unsetCursor()
		# record rename batch for undo
		pairs = self._pending_rename_pairs
		self._pending_rename_pairs = None
		self._rename_history.append(pairs)
		self._undo_rename_action.setEnabled(True)
		# refresh table (paths changed)
		self._movie_panel.refresh_data()
		# workflow hint: suggest download as next step
		self._status.showMessage(
			"Organize complete -- ready to download content"
			" (Step 3)",
			8000,
		)
		self._update_toolbar_badges()

	#============================================
	def _on_rename_exec_error(self, error_text: str) -> None:
		"""Handle error from rename execution."""
		self.unsetCursor()
		self._pending_rename_pairs = None
		self._show_error("Organize Error", error_text)

	#============================================
	def _rename_batch(self, movies: list) -> None:
		"""Organize multiple movies in batch with a combined preview.

		Computes rename pairs for all scraped movies in a background
		thread, then shows a combined preview dialog.

		Args:
			movies: List of Movie instances to organize.
		"""
		self._status.showMessage("Computing batch rename preview...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# store movies for callback
		self._pending_batch_movies = movies
		# compute all dry-run previews in background
		self._rename_mode = "batch_preview"
		self._rename_task_id = self._task_api.submit_job(
			"Batch rename preview",
			self._compute_batch_rename_pairs, movies,
			_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
		)

	#============================================
	def _compute_batch_rename_pairs(self, movies: list) -> dict:
		"""Compute rename pairs for batch of movies (background thread).

		Args:
			movies: List of Movie instances to organize.

		Returns:
			Dict with all_pairs, movies_to_rename, and skipped count.
		"""
		all_pairs = []
		movies_to_rename = []
		skipped = 0
		for movie in movies:
			if not movie.scraped:
				skipped += 1
				continue
			pairs = self._api.rename_movie(movie, dry_run=True)
			if pairs:
				all_pairs.extend(pairs)
				movies_to_rename.append(movie)
		result = {
			"all_pairs": all_pairs,
			"movies_to_rename": movies_to_rename,
			"skipped": skipped,
		}
		return result

	#============================================
	def _on_batch_rename_preview_done(self, result: dict) -> None:
		"""Show combined preview dialog after batch dry-run.

		Args:
			result: Dict with all_pairs, movies_to_rename, skipped.
		"""
		self.unsetCursor()
		self._status.clearMessage()
		all_pairs = result["all_pairs"]
		movies_to_rename = result["movies_to_rename"]
		skipped = result["skipped"]
		if not all_pairs:
			msg = "No matched movies to organize."
			if skipped:
				msg += f" ({skipped} unmatched movies skipped)"
			PySide6.QtWidgets.QMessageBox.information(
				self, "Organize", msg
			)
			return
		# show combined preview dialog
		title = (
			f"Organize {len(movies_to_rename)} movies"
			f" ({len(all_pairs)} files)"
		)
		dialog = moviemanager.ui.dialogs.rename_preview.RenamePreviewDialog(
			all_pairs, self
		)
		dialog.setWindowTitle(title)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			# execute all renames in background
			self._status.showMessage("Organizing files...")
			self.setCursor(
				PySide6.QtCore.Qt.CursorShape.WaitCursor
			)
			self._pending_rename_pairs = all_pairs
			self._rename_mode = "batch_exec"
			self._rename_task_id = self._task_api.submit_job(
				"Batch renaming",
				self._execute_batch_renames, movies_to_rename,
				_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
			)

	#============================================
	def _execute_batch_renames(self, movies: list) -> list:
		"""Execute batch renames in background thread.

		Args:
			movies: List of Movie instances to rename.

		Returns:
			List of error strings (empty if all succeeded).
		"""
		errors = []
		for movie in movies:
			try:
				self._api.rename_movie(movie, dry_run=False)
			except Exception as exc:
				errors.append(f"{movie.title}: {exc}")
		return errors

	#============================================
	def _on_batch_rename_exec_done(self, errors: list) -> None:
		"""Handle batch rename execution completion.

		Args:
			errors: List of error strings from failed renames.
		"""
		self.unsetCursor()
		# record combined batch for undo
		pairs = self._pending_rename_pairs
		self._pending_rename_pairs = None
		self._rename_history.append(pairs)
		self._undo_rename_action.setEnabled(True)
		# refresh table (paths changed)
		self._movie_panel.refresh_data()
		if errors:
			error_text = "\n".join(errors)
			self._show_error("Organize Errors", error_text)
		else:
			count = len(pairs)
			self._status.showMessage(
				f"Organized {count} file(s)"
				" -- ready to download content (Step 3)",
				8000,
			)
		self._update_toolbar_badges()

	#============================================
	def _undo_last_rename(self) -> None:
		"""Undo the last rename batch by reversing file moves."""
		if not self._rename_history:
			return
		pairs = self._rename_history.pop()
		errors = []
		# reverse each rename: move new -> original
		for src, dst in pairs:
			if os.path.exists(dst):
				shutil.move(dst, src)
			else:
				errors.append(f"File not found: {dst}")
		if not self._rename_history:
			self._undo_rename_action.setEnabled(False)
		# refresh table
		self._movie_panel.set_movies(self._api.get_movies())
		if errors:
			error_text = "\n".join(errors)
			self._show_error("Undo Rename", error_text)
		else:
			count = len(pairs)
			self._status.showMessage(
				f"Undo complete: {count} file(s) restored", 3000
			)

	#============================================
	def _show_settings(self):
		"""Show settings dialog."""
		dialog = moviemanager.ui.dialogs.settings_dialog.SettingsDialog(
			self._settings, self
		)
		if dialog.exec() == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			self._settings = dialog.get_settings()
			# reinitialize API with new settings
			self._api = moviemanager.api.movie_api.MovieAPI(
				self._settings
			)

	#============================================
	def _cancel_operation(self) -> None:
		"""Cancel the currently running background operation."""
		# cancel scan, scrape, refresh, rename via TaskAPI
		for tid in (self._scan_task_id, self._scrape_task_id,
					self._refresh_task_id, self._pg_task_id,
					self._rename_task_id):
			if tid is not None:
				self._task_api.cancel(tid)
		self._scan_task_id = None
		self._scrape_task_id = None
		self._refresh_task_id = None
		self._pg_task_id = None
		self._rename_task_id = None
		self._rename_mode = None
		# cancel any pending download jobs
		for tid in self._download_task_ids:
			self._task_api.cancel(tid)
		self._download_task_ids = []
		self.unsetCursor()
		self._status.hide_progress()
		self._status.showMessage("Operation cancelled", 3000)

	#============================================
	def _update_jobs_count(self) -> None:
		"""Update the status bar jobs button with active job count."""
		self._status.update_job_count(self._task_api.active_count)

	#============================================
	def _show_jobs_dialog(self) -> None:
		"""Show the background jobs popup dialog."""
		if self._jobs_dialog is None:
			self._jobs_dialog = (
				moviemanager.ui.dialogs.jobs_dialog.JobsDialog(
					self._task_api, self
				)
			)
		self._jobs_dialog.show()
		self._jobs_dialog.raise_()

	#============================================
	def _focus_search(self) -> None:
		"""Focus the search/filter field (Ctrl+F)."""
		self._movie_panel.focus_search()

	#============================================
	def _on_escape(self) -> None:
		"""Clear filter text or deselect (Escape)."""
		self._movie_panel.clear_filter()

	#============================================
	def _rescan(self) -> None:
		"""Re-scan the current directory (Ctrl+R)."""
		if self._current_directory:
			self._scan_directory(self._current_directory)

	#============================================
	def _on_context_action(self, action: str, movie) -> None:
		"""Handle context menu actions from the movie panel."""
		if action == "scrape":
			self._scrape_selected()
		elif action == "edit":
			self._edit_selected()
		elif action == "rename":
			self._rename_selected()
		elif action == "download":
			self._download_content()

	#============================================
	def _select_all(self) -> None:
		"""Check all movies in the table."""
		self._movie_panel.check_all()

	#============================================
	def _select_none(self) -> None:
		"""Uncheck all movies in the table."""
		self._movie_panel.uncheck_all()

	#============================================
	def _select_unscraped(self) -> None:
		"""Check only unscraped movies."""
		self._movie_panel.check_unscraped()

	#============================================
	def _batch_scrape_unscraped(self) -> None:
		"""Scrape all unscraped movies using auto-select best match.

		Uses confidence scoring to only auto-select high-confidence
		matches (>= 0.7). Runs in a background thread with status bar
		progress so the UI stays responsive.
		"""
		movies = self._api.get_movies()
		unscraped = [m for m in movies if not m.scraped]
		if not unscraped:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Batch Scrape",
				"All movies are already scraped."
			)
			return
		# show progress in status bar
		self._status.show_progress(
			0, len(unscraped), "Starting batch scrape..."
		)
		# run scraping in background via TaskAPI
		self._scrape_task_id = self._task_api.submit_job(
			"Batch scrape", self._batch_scrape_loop, unscraped,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)

	#============================================
	def _batch_scrape_loop(self, unscraped: list) -> dict:
		"""Execute batch scrape loop in a background thread.

		Searches and auto-matches each unscraped movie using
		confidence scoring. Called by Worker in QThreadPool.

		Args:
			unscraped: List of unscraped Movie instances.

		Returns:
			Dict with scraped_count, skipped_low_confidence,
			and no_results_list.
		"""
		confidence_threshold = 0.7
		scraped_count = 0
		skipped_low_confidence = []
		no_results_list = []
		for i, movie in enumerate(unscraped):
			# check for cancellation via TaskAPI worker
			scrape_worker = self._task_api.get_worker(self._scrape_task_id)
			if scrape_worker and scrape_worker.is_cancelled:
				break
			# emit progress via worker signals
			if scrape_worker:
				scrape_worker.signals.progress.emit(
					i, len(unscraped),
					f"Scraping: {movie.title}"
					f" ({i + 1}/{len(unscraped)})",
				)
			# search and auto-select best match
			results = self._api.search_movie(
				movie.title, movie.year
			)
			if not results:
				no_results_list.append(movie.title)
				continue
			best = results[0]
			# use pre-computed match confidence from search
			confidence = best.match_confidence
			if confidence < confidence_threshold:
				skipped_low_confidence.append(
					f"{movie.title} -> {best.title}"
					f" ({confidence:.1f})"
				)
				continue
			# use tmdb_id or imdb_id depending on provider
			if best.tmdb_id:
				self._api.scrape_movie(
					movie, tmdb_id=best.tmdb_id
				)
			elif best.imdb_id:
				self._api.scrape_movie(
					movie, imdb_id=best.imdb_id
				)
			scraped_count += 1
		# check how many parental guide fetches failed during scrape
		pg_fail_count = len(self._api._failed_parental_guides)
		result = {
			"scraped_count": scraped_count,
			"skipped_low_confidence": skipped_low_confidence,
			"no_results_list": no_results_list,
			"parental_guide_failures": pg_fail_count,
		}
		return result

	#============================================
	def _on_batch_scrape_done(self, result: dict) -> None:
		"""Handle batch scrape completion.

		Refreshes the movie table and shows a summary dialog.

		Args:
			result: Dict with scraped_count, skipped_low_confidence,
				and no_results_list.
		"""
		self._status.hide_progress()
		# refresh table data in-place (preserves selection)
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		# build summary
		scraped_count = result["scraped_count"]
		skipped_low_confidence = result["skipped_low_confidence"]
		no_results_list = result["no_results_list"]
		summary_parts = [f"Scraped: {scraped_count}"]
		if skipped_low_confidence:
			summary_parts.append(
				f"Skipped (low confidence):"
				f" {len(skipped_low_confidence)}"
			)
		if no_results_list:
			summary_parts.append(
				f"No results: {len(no_results_list)}"
			)
		# report parental guide failures
		pg_failures = result.get("parental_guide_failures", 0)
		if pg_failures:
			summary_parts.append(
				f"Parental guide timeouts: {pg_failures}"
				" (will retry)"
			)
		summary_text = "\n".join(summary_parts)
		# add detail about skipped movies
		if skipped_low_confidence:
			summary_text += "\n\nLow confidence matches:\n"
			summary_text += "\n".join(
				skipped_low_confidence[:20]
			)
		PySide6.QtWidgets.QMessageBox.information(
			self, "Batch Scrape Complete", summary_text
		)
		self._update_toolbar_badges()
		# submit deferred retry job for failed parental guides
		if self._api.has_failed_parental_guides():
			self._task_api.submit_job(
				"Retry parental guides",
				self._api.retry_failed_parental_guides,
				_priority=moviemanager.ui.task_api.PRIORITY_LOW,
			)

	#============================================
	def _refresh_metadata(self) -> None:
		"""Re-fetch metadata from IMDB/TMDB for matched movies.

		Uses get_chosen_movies() to resolve checked/selected movies,
		filtering to scraped movies. Falls back to all scraped movies
		if nothing is chosen. Launches a background worker to re-scrape
		each with cache bypass.
		"""
		# unified resolution: checked > selected > empty
		chosen = self._movie_panel.get_chosen_movies()
		scraped = [m for m in chosen if m.scraped]
		if not scraped:
			# nothing chosen; fall back to all scraped movies
			all_movies = self._api.get_movies()
			scraped = [m for m in all_movies if m.scraped]
		if not scraped:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Refresh Metadata",
				"No matched movies to refresh."
			)
			return
		# confirm with the user
		reply = PySide6.QtWidgets.QMessageBox.question(
			self, "Refresh Metadata",
			f"Re-fetch metadata for {len(scraped)} matched"
			f" movie{'s' if len(scraped) != 1 else ''}?",
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			| PySide6.QtWidgets.QMessageBox.StandardButton.No,
		)
		if reply != PySide6.QtWidgets.QMessageBox.StandardButton.Yes:
			return
		# show progress in status bar
		self._status.show_progress(
			0, len(scraped), "Starting metadata refresh..."
		)
		# run refresh in background via TaskAPI
		self._refresh_task_id = self._task_api.submit_job(
			"Refresh metadata", self._refresh_metadata_loop, scraped,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)

	#============================================
	def _refresh_metadata_loop(self, movies: list) -> dict:
		"""Execute metadata refresh loop in a background thread.

		Re-scrapes each movie with cache bypass to get fresh
		metadata from the remote provider.

		Args:
			movies: List of scraped Movie instances to refresh.

		Returns:
			Dict with refreshed_count.
		"""
		refreshed_count = 0
		for i, movie in enumerate(movies):
			# check for cancellation via TaskAPI worker
			refresh_worker = self._task_api.get_worker(self._refresh_task_id)
			if refresh_worker and refresh_worker.is_cancelled:
				break
			# emit progress via worker signals
			if refresh_worker:
				refresh_worker.signals.progress.emit(
					i, len(movies),
					f"Refreshing: {movie.title}"
					f" ({i + 1}/{len(movies)})",
				)
			# re-scrape with cache bypass
			self._api.scrape_movie(
				movie,
				tmdb_id=movie.tmdb_id,
				imdb_id=movie.imdb_id,
				bypass_cache=True,
			)
			refreshed_count += 1
		result = {"refreshed_count": refreshed_count}
		return result

	#============================================
	def _on_refresh_metadata_done(self, result: dict) -> None:
		"""Handle metadata refresh completion.

		Refreshes the movie table and shows a summary dialog.

		Args:
			result: Dict with refreshed_count.
		"""
		self._status.hide_progress()
		# refresh table data in-place (preserves selection)
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		count = result["refreshed_count"]
		PySide6.QtWidgets.QMessageBox.information(
			self, "Refresh Metadata Complete",
			f"Refreshed metadata for {count}"
			f" movie{'s' if count != 1 else ''}."
		)
		self._update_toolbar_badges()

	#============================================
	def _fetch_parental_guides(self) -> None:
		"""Fetch parental guide data from IMDB for matched movies.

		Uses get_chosen_movies() to resolve checked/selected movies,
		filtering to scraped movies with imdb_id. Falls back to all
		scraped movies with imdb_id only when nothing is chosen.
		Submits a background job.
		"""
		# unified resolution: checked > selected > empty
		chosen = self._movie_panel.get_chosen_movies()
		if chosen:
			# user explicitly chose movies; only use those
			candidates = [
				m for m in chosen
				if m.scraped and m.imdb_id
			]
		else:
			# nothing chosen; fall back to all scraped movies
			all_movies = self._api.get_movies()
			candidates = [
				m for m in all_movies
				if m.scraped and m.imdb_id
			]
		if not candidates:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Fetch Parental Guide",
				"No matched movies with IMDB IDs found."
			)
			return
		# confirm with the user
		reply = PySide6.QtWidgets.QMessageBox.question(
			self, "Fetch Parental Guide",
			f"Fetch parental guide data for {len(candidates)}"
			f" movie{'s' if len(candidates) != 1 else ''}?\n"
			f"Movies already checked within 90 days will be skipped.",
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			| PySide6.QtWidgets.QMessageBox.StandardButton.No,
		)
		if reply != PySide6.QtWidgets.QMessageBox.StandardButton.Yes:
			return
		# show progress in status bar
		self._status.show_progress(
			0, len(candidates),
			"Starting parental guide fetch...",
		)
		# run in background via TaskAPI
		self._pg_task_id = self._task_api.submit_job(
			"Fetch parental guides",
			self._fetch_parental_guides_loop, candidates,
			_priority=moviemanager.ui.task_api.PRIORITY_NORMAL,
		)

	#============================================
	def _fetch_parental_guides_loop(self, movies: list) -> dict:
		"""Execute parental guide fetch loop in a background thread.

		Args:
			movies: List of Movie instances with imdb_id set.

		Returns:
			Dict with fetched, no_data, failed, skipped counts.
		"""
		# use worker progress callback
		def progress_callback(cur: int, tot: int, msg: str) -> None:
			worker = self._task_api.get_worker(self._pg_task_id)
			if worker:
				worker.signals.progress.emit(cur, tot, msg)
		result = self._api.fetch_parental_guides(
			movies, progress_callback=progress_callback,
		)
		return result

	#============================================
	def _on_fetch_parental_guides_done(self, result: dict) -> None:
		"""Handle parental guide fetch completion.

		Refreshes the movie table and shows a summary dialog.

		Args:
			result: Dict with fetched, no_data, failed, skipped counts.
		"""
		self._status.hide_progress()
		# refresh table data in-place
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		# build summary message
		fetched = result.get("fetched", 0)
		no_data = result.get("no_data", 0)
		failed = result.get("failed", 0)
		skipped = result.get("skipped", 0)
		lines = []
		if fetched:
			lines.append(f"Fetched: {fetched}")
		if no_data:
			lines.append(f"No data on IMDB: {no_data}")
		if failed:
			lines.append(f"Failed: {failed}")
		if skipped:
			lines.append(f"Skipped: {skipped}")
		summary = "\n".join(lines) if lines else "No movies processed."
		PySide6.QtWidgets.QMessageBox.information(
			self, "Parental Guide Fetch Complete", summary
		)
		self._update_toolbar_badges()

	#============================================
	def _refresh_file_stats(self) -> None:
		"""Re-probe video files for codec, resolution, and duration.

		Delegates to the existing media probe infrastructure which
		handles background probing, progress, and table refresh.
		"""
		self._start_media_probe()

	#============================================
	def _toggle_dark_mode(self) -> None:
		"""Toggle between dark and system theme."""
		if self._settings.theme == "dark":
			self._settings.theme = "system"
		else:
			self._settings.theme = "dark"
		moviemanager.core.settings.save_settings(self._settings)
		app = PySide6.QtWidgets.QApplication.instance()
		moviemanager.ui.theme.apply_theme(app, self._settings.theme)

	#============================================
	def _download_content(self) -> None:
		"""Download artwork, trailers, and subtitles via TaskAPI.

		Submits individual download jobs per content type per movie
		so each appears in the Jobs dialog. User can continue working
		while downloads run in the background.
		"""
		# prevent concurrent batch downloads
		if self._download_task_ids:
			still_running = any(
				self._task_api.is_running(tid)
				for tid in self._download_task_ids
			)
			if still_running:
				PySide6.QtWidgets.QMessageBox.information(
					self, "Download In Progress",
					"A download batch is already running. "
					"Check the Jobs dialog for progress."
				)
				return
		# unified resolution: checked > selected > single
		chosen = self._movie_panel.get_chosen_movies()
		# filter to scraped movies only
		scraped_movies = [m for m in chosen if m.scraped]
		if not scraped_movies:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Matched Movies",
				"Match movies to IMDB first (Step 1)."
			)
			return
		# build list of individual download tasks
		tasks = self._build_download_tasks(scraped_movies)
		if not tasks:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Nothing to Download",
				"All content is already present."
			)
			return
		# confirm before starting
		movie_count = len(scraped_movies)
		task_count = len(tasks)
		reply = PySide6.QtWidgets.QMessageBox.question(
			self, "Download Content",
			f"Queue {task_count} download(s) for "
			f"{movie_count} movie(s)?\n\n"
			"Downloads will run in the background.\n"
			"Check the Jobs dialog for progress.",
			PySide6.QtWidgets.QMessageBox.StandardButton.Ok
			| PySide6.QtWidgets.QMessageBox.StandardButton.Cancel,
		)
		if reply != PySide6.QtWidgets.QMessageBox.StandardButton.Ok:
			return
		# submit each task via TaskAPI
		self._download_task_ids = []
		for name, fn, args in tasks:
			task_id = self._task_api.submit_job(
				name, fn, *args,
				_priority=moviemanager.ui.task_api.PRIORITY_LOW,
			)
			self._download_task_ids.append(task_id)
		self._status.showMessage(
			f"Queued {task_count} downloads -- see Jobs dialog",
			5000,
		)

	#============================================
	def _build_download_tasks(self, movies: list) -> list:
		"""Build a list of individual download task tuples.

		Checks settings and per-movie state to determine which
		downloads are needed.

		Args:
			movies: List of scraped Movie instances.

		Returns:
			List of (name, fn, args_tuple) tuples ready for submit_job.
		"""
		tasks = []
		languages = self._settings.subtitle_languages
		for movie in movies:
			title = movie.title or "Unknown"
			# artwork (poster + fanart handled inside download_artwork)
			if self._settings.download_poster and not movie.has_poster:
				tasks.append((
					f"Artwork: {title}",
					self._api.download_artwork,
					(movie,),
				))
			# trailer (no trailer_url filter; DownloadError(no_url) reported)
			if (self._settings.download_trailer
					and not movie.has_trailer):
				tasks.append((
					f"Trailer: {title}",
					self._api.download_trailer,
					(movie,),
				))
			# subtitles (no imdb_id filter; DownloadError(no_imdb_id) reported)
			if (self._settings.download_subtitles
					and not movie.has_subtitle):
				tasks.append((
					f"Subtitles: {title}",
					self._api.download_subtitles,
					(movie, languages),
				))
		return tasks

	#============================================
	def _on_download_job_done(self, task_id: int, result) -> None:
		"""Handle individual download job completion.

		When all tracked batch download jobs are done, refresh the
		movie panel and status counts.

		Args:
			task_id: The completed task ID.
			result: The return value of the download callable.
		"""
		if not self._download_task_ids:
			return
		if task_id not in self._download_task_ids:
			return
		# check if every job in the batch has finished
		all_done = all(
			self._task_api.is_done(tid)
			for tid in self._download_task_ids
		)
		if all_done:
			self._download_task_ids = []
			self._movie_panel.refresh_data()
			self._refresh_status_counts()
			self._update_toolbar_badges()
			self._status.showMessage("All downloads complete", 5000)

	#============================================
	def _download_trailer(self) -> None:
		"""Download trailer for selected movie via TaskAPI."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection", "Please select a movie first."
			)
			return
		if not movie.trailer_url:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Trailer",
				"No trailer URL available. Scrape the movie first."
			)
			return
		title = movie.title or "Unknown"
		self._task_api.submit_job(
			f"Trailer: {title}",
			self._api.download_trailer, movie,
			_priority=moviemanager.ui.task_api.PRIORITY_LOW,
		)
		self._status.showMessage("Trailer download queued", 3000)

	#============================================
	def _download_subtitles(self) -> None:
		"""Download subtitles for selected movie via TaskAPI."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection", "Please select a movie first."
			)
			return
		if not movie.imdb_id:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No IMDB ID",
				"Movie needs an IMDB ID. Scrape the movie first."
			)
			return
		title = movie.title or "Unknown"
		languages = self._settings.subtitle_languages
		self._task_api.submit_job(
			f"Subtitles: {title}",
			self._api.download_subtitles, movie, languages,
			_priority=moviemanager.ui.task_api.PRIORITY_LOW,
		)
		self._status.showMessage("Subtitle download queued", 3000)

	#============================================
	def _show_about(self):
		"""Show about dialog with version, author, and license (#15)."""
		# read version from importlib metadata
		try:
			version = importlib.metadata.version("movie-media-manager")
		except importlib.metadata.PackageNotFoundError:
			version = "dev"
		about_text = (
			f"Movie Media Manager v{version}\n\n"
			"A Python tool for organizing movie media.\n"
			"Inspired by tinyMediaManager.\n\n"
			"Author: Neil Voss\n"
			"License: GPL-3.0-or-later\n"
			"https://bsky.app/profile/neilvosslab.bsky.social"
		)
		PySide6.QtWidgets.QMessageBox.about(
			self, "About Movie Media Manager", about_text
		)

	#============================================
	def dragEnterEvent(self, event) -> None:
		"""Accept directory drag events (#19)."""
		if event.mimeData().hasUrls():
			event.acceptProposedAction()

	#============================================
	def dropEvent(self, event) -> None:
		"""Handle directory drop events (#19)."""
		urls = event.mimeData().urls()
		if not urls:
			return
		# use first dropped URL as directory path
		path = urls[0].toLocalFile()
		if os.path.isdir(path):
			self._scan_directory(path)
		else:
			PySide6.QtWidgets.QMessageBox.warning(
				self, "Invalid Drop",
				"Please drop a directory, not a file."
			)

	#============================================
	def closeEvent(self, event) -> None:
		"""Save window state on close, warn if jobs or downloads running."""
		# warn if background scrape jobs are still running
		if self._task_api.active_count > 0:
			reply = PySide6.QtWidgets.QMessageBox.question(
				self, "Jobs In Progress",
				f"{self._task_api.active_count} background job(s) "
				"still running.\nQuit anyway?",
				PySide6.QtWidgets.QMessageBox.StandardButton.Yes
				| PySide6.QtWidgets.QMessageBox.StandardButton.No,
			)
			if reply != PySide6.QtWidgets.QMessageBox.StandardButton.Yes:
				event.ignore()
				return
		settings = PySide6.QtCore.QSettings(
			"MovieMediaManager", "MovieMediaManager"
		)
		settings.setValue("geometry", self.saveGeometry())
		settings.setValue("windowState", self.saveState())
		# save table column widths and sort state
		self._movie_panel.save_table_state(settings)
		# shut down background job manager
		self._task_api.shutdown()
		# clean up IMDB browser transport (page before profile) to avoid segfault
		self._api.shutdown()
		super().closeEvent(event)

	#============================================
	def _restore_state(self) -> None:
		"""Restore window geometry and state (#20)."""
		settings = PySide6.QtCore.QSettings(
			"MovieMediaManager", "MovieMediaManager"
		)
		geometry = settings.value("geometry")
		if geometry:
			self.restoreGeometry(geometry)
		state = settings.value("windowState")
		if state:
			self.restoreState(state)
		# restore table column widths and sort state
		self._movie_panel.restore_table_state(settings)
