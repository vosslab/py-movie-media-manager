"""Main application window."""

# Standard Library
import os
import shutil
import importlib.metadata

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.settings
import moviemanager.ui.dialogs.download_dialog
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
		self._pool = PySide6.QtCore.QThreadPool()
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
		# status bar
		self._status = moviemanager.ui.widgets.status_bar.StatusBar()
		self._status.cancel_requested.connect(self._cancel_operation)
		self.setStatusBar(self._status)
		# track the active worker for cancellation
		self._active_worker = None
		# track background download worker separately
		self._download_worker = None
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
		self._current_directory = directory
		# save last opened directory to settings
		self._settings.last_directory = directory
		moviemanager.core.settings.save_settings(self._settings)
		# clear rename history on directory change
		self._rename_history.clear()
		self._undo_rename_action.setEnabled(False)
		# clear table and prepare for incremental loading
		self._movie_panel.set_movies([])
		self._status.showMessage(f"Scanning {directory}...")
		self._status.show_progress(0, 0, f"Scanning {directory}...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# run scan in background (#1)
		worker = moviemanager.ui.workers.Worker(
			self._api.scan_directory, directory,
			progress_callback=self._on_scan_progress_callback,
			movie_callback=self._on_movie_found_callback,
		)
		worker.signals.partial_result.connect(self._on_scan_partial)
		worker.signals.finished.connect(self._on_scan_done)
		worker.signals.error.connect(self._on_scan_error)
		worker.signals.progress.connect(self._on_scan_progress)
		self._active_worker = worker
		self._pool.start(worker)

	#============================================
	def _on_scan_progress_callback(self, current: int, message: str) -> None:
		"""Progress callback invoked from scanner thread.

		Emits progress signal to update the UI on the main thread.
		This is called from the worker thread, so we use the signal
		mechanism to forward to the main thread.
		"""
		# emit progress signal to marshal GUI update to the main thread;
		# direct GUI calls from worker threads cause QPainter segfaults
		if self._active_worker:
			self._active_worker.signals.progress.emit(current, 0, message)

	#============================================
	def _on_scan_progress(self, current: int, total: int, message: str) -> None:
		"""Handle scan progress updates on the main thread."""
		self._status.show_progress(current, total, message)

	#============================================
	def _on_movie_found_callback(self, movie) -> None:
		"""Callback invoked from worker thread when a movie is discovered.

		Emits partial_result signal to marshal delivery to the main thread.
		"""
		if self._active_worker:
			self._active_worker.signals.partial_result.emit(movie)

	#============================================
	def _on_scan_partial(self, movie) -> None:
		"""Handle incremental movie delivery on the main thread."""
		self._movie_panel.append_movies([movie])

	#============================================
	def _on_scan_done(self, movies) -> None:
		"""Handle scan completion with final cleanup.

		Movies were already delivered incrementally via partial_result,
		so this only updates status bar counts and window title.
		"""
		self.unsetCursor()
		self._status.hide_progress()
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		self._status.set_movie_count(total, scraped)
		# update window title with current directory
		self.setWindowTitle(
			f"Movie Media Manager - {self._current_directory}"
		)
		# transient success message (#24)
		self._status.showMessage(
			f"Scan complete: {total} movies found", 3000
		)
		# update toolbar badges with workflow counts
		self._update_toolbar_badges()

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
		# count all three categories in a single pass
		unmatched = 0
		unorganized = 0
		incomplete = 0
		for m in movies:
			if not m.scraped:
				unmatched += 1
			elif not m.is_organized:
				unorganized += 1
			if m.is_organized and not (m.has_poster and m.has_trailer):
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
		# check if multiple movies are checked or selected
		checked_movies = self._movie_panel.get_checked_movies()
		# fall back to row selection if fewer than 2 checked
		if len(checked_movies) <= 1:
			selected = self._movie_panel.get_selected_movies()
			if len(selected) > 1:
				checked_movies = selected
		if len(checked_movies) > 1:
			# batch mode: pass movies as a list
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				checked_movies[0], self._api, self,
				movie_list=checked_movies,
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
				movie, self._api, self
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
		# collect checked or selected movies for batch
		checked_movies = self._movie_panel.get_checked_movies()
		if len(checked_movies) <= 1:
			selected = self._movie_panel.get_selected_movies()
			if len(selected) > 1:
				checked_movies = selected
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
		worker = moviemanager.ui.workers.Worker(
			self._api.rename_movie, movie, dry_run=True,
		)
		# store movie ref for the callback
		self._pending_rename_movie = movie
		worker.signals.finished.connect(
			self._on_rename_preview_done
		)
		worker.signals.error.connect(self._on_rename_preview_error)
		self._pool.start(worker)

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
			exec_worker = moviemanager.ui.workers.Worker(
				self._api.rename_movie, movie, dry_run=False,
			)
			# store pairs for undo on completion
			self._pending_rename_pairs = pairs
			exec_worker.signals.finished.connect(
				self._on_rename_exec_done
			)
			exec_worker.signals.error.connect(
				self._on_rename_exec_error
			)
			self._pool.start(exec_worker)

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
		worker = moviemanager.ui.workers.Worker(
			self._compute_batch_rename_pairs, movies,
		)
		worker.signals.finished.connect(
			self._on_batch_rename_preview_done
		)
		worker.signals.error.connect(self._on_rename_preview_error)
		self._pool.start(worker)

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
			exec_worker = moviemanager.ui.workers.Worker(
				self._execute_batch_renames, movies_to_rename,
			)
			exec_worker.signals.finished.connect(
				self._on_batch_rename_exec_done
			)
			exec_worker.signals.error.connect(
				self._on_rename_exec_error
			)
			self._pool.start(exec_worker)

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
		if self._active_worker:
			self._active_worker.cancel()
			self._active_worker = None
		self.unsetCursor()
		self._status.hide_progress()
		self._status.showMessage("Operation cancelled", 3000)

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
		# run scraping in background worker
		worker = moviemanager.ui.workers.Worker(
			self._batch_scrape_loop, unscraped,
		)
		worker.signals.progress.connect(self._on_scan_progress)
		worker.signals.finished.connect(self._on_batch_scrape_done)
		worker.signals.error.connect(self._on_scan_error)
		self._active_worker = worker
		self._pool.start(worker)

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
			# check for cancellation
			if self._active_worker and self._active_worker.is_cancelled:
				break
			# emit progress via worker signals
			if self._active_worker:
				self._active_worker.signals.progress.emit(
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
		result = {
			"scraped_count": scraped_count,
			"skipped_low_confidence": skipped_low_confidence,
			"no_results_list": no_results_list,
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
		self._active_worker = None
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
		"""Download artwork, trailers, and subtitles in the background.

		Replaces modal download dialog with non-blocking background
		worker. User can continue matching and organizing while
		downloads run. Progress shown in status bar.
		"""
		# prevent concurrent downloads
		if hasattr(self, '_download_worker') and self._download_worker:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Download In Progress",
				"A download is already running. Please wait."
			)
			return
		# collect checked or selected movies
		checked_movies = self._movie_panel.get_checked_movies()
		if len(checked_movies) <= 1:
			selected = self._movie_panel.get_selected_movies()
			if len(selected) > 1:
				checked_movies = selected
		# filter to scraped movies only
		scraped_movies = [m for m in checked_movies if m.scraped]
		# fall back to single selected movie
		if not scraped_movies:
			movie = self._movie_panel.get_selected_movie()
			if movie and movie.scraped:
				scraped_movies = [movie]
		if not scraped_movies:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Matched Movies",
				"Match movies to IMDB first (Step 1)."
			)
			return
		# confirm before starting
		count = len(scraped_movies)
		reply = PySide6.QtWidgets.QMessageBox.question(
			self, "Download Content",
			f"Download content for {count} movie(s)?\n\n"
			"Downloads will run in the background.",
			PySide6.QtWidgets.QMessageBox.StandardButton.Ok
			| PySide6.QtWidgets.QMessageBox.StandardButton.Cancel,
		)
		if reply != PySide6.QtWidgets.QMessageBox.StandardButton.Ok:
			return
		# launch background download worker
		self._status.show_progress(
			0, count, "Starting downloads..."
		)
		worker = moviemanager.ui.workers.Worker(
			self._run_background_downloads, scraped_movies,
		)
		worker.signals.progress.connect(self._on_scan_progress)
		worker.signals.finished.connect(
			self._on_background_download_done
		)
		worker.signals.error.connect(
			self._on_background_download_error
		)
		self._download_worker = worker
		self._pool.start(worker)

	#============================================
	def _run_background_downloads(self, movies: list) -> dict:
		"""Execute downloads in a background thread.

		Downloads artwork, trailers, and subtitles for each movie.
		Checks for cancellation between movies.

		Args:
			movies: List of scraped Movie instances.

		Returns:
			dict with art_count, trailer_count, sub_count, errors.
		"""
		import moviemanager.ui.dialogs.download_dialog
		result = moviemanager.ui.dialogs.download_dialog._run_batch_download(
			movies, self._api, self._settings,
			download_artwork=self._settings.download_poster,
			download_trailers=self._settings.download_trailer,
			download_subs=self._settings.download_subtitles,
			worker=self._download_worker,
		)
		return result

	#============================================
	def _on_background_download_done(self, result: dict) -> None:
		"""Handle background download completion.

		Args:
			result: Dict with art_count, trailer_count, sub_count,
				errors list, and cancelled flag.
		"""
		self._download_worker = None
		self._status.hide_progress()
		# build summary text
		parts = []
		if result["art_count"]:
			parts.append(f"{result['art_count']} artwork files")
		if result["trailer_count"]:
			parts.append(f"{result['trailer_count']} trailers")
		if result["sub_count"]:
			parts.append(f"{result['sub_count']} subtitle files")
		if parts:
			summary = "Downloaded: " + ", ".join(parts)
		elif result["cancelled"]:
			summary = "Download cancelled"
		else:
			summary = "All content already present"
		if result["errors"]:
			error_count = len(result["errors"])
			summary += f" ({error_count} errors)"
		self._status.showMessage(summary, 8000)
		# refresh table data
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		self._update_toolbar_badges()

	#============================================
	def _on_background_download_error(self, error_text: str) -> None:
		"""Handle background download error."""
		self._download_worker = None
		self._status.hide_progress()
		self._show_error("Download Error", error_text)

	#============================================
	def _download_trailer(self) -> None:
		"""Download trailer for selected movie."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection", "Please select a movie first."
			)
			return
		if not movie.trailer:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Trailer",
				"No trailer URL available. Scrape the movie first."
			)
			return
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		worker = moviemanager.ui.workers.Worker(
			self._api.download_trailer, movie
		)
		worker.signals.finished.connect(self._on_download_done)
		worker.signals.error.connect(self._on_download_error)
		self._pool.start(worker)

	#============================================
	def _download_subtitles(self) -> None:
		"""Download subtitles for selected movie."""
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
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		languages = self._settings.subtitle_languages
		worker = moviemanager.ui.workers.Worker(
			self._api.download_subtitles, movie, languages
		)
		worker.signals.finished.connect(self._on_download_done)
		worker.signals.error.connect(self._on_download_error)
		self._pool.start(worker)

	#============================================
	def _on_download_done(self, result) -> None:
		"""Handle download completion."""
		self.unsetCursor()
		self._status.showMessage("Download complete", 3000)

	#============================================
	def _on_download_error(self, error_text: str) -> None:
		"""Handle download error."""
		self.unsetCursor()
		self._show_error("Download Error", error_text)

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
		"""Save window state on close, warn if downloads running."""
		# warn if background downloads are still running
		if self._download_worker:
			reply = PySide6.QtWidgets.QMessageBox.question(
				self, "Downloads In Progress",
				"Background downloads are still running.\n"
				"Quit anyway?",
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
