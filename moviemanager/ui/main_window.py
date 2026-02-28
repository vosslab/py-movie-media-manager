"""Main application window."""

# Standard Library
import importlib.metadata

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.settings
import moviemanager.ui.menu_builder
import moviemanager.ui.movies.movie_panel
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
		# status bar
		self._status = moviemanager.ui.widgets.status_bar.StatusBar()
		self._status.cancel_requested.connect(self._cancel_operation)
		self.setStatusBar(self._status)
		# track the active worker for cancellation
		self._active_worker = None
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
		# load directory if provided, otherwise offer to reopen last folder
		if directory:
			self._scan_directory(directory)
		elif self._settings.last_directory:
			import os
			last_dir = self._settings.last_directory
			if os.path.isdir(last_dir):
				reply = PySide6.QtWidgets.QMessageBox.question(
					self, "Reopen Last Folder",
					f"Reopen last folder?\n{last_dir}",
				)
				yes_btn = PySide6.QtWidgets.QMessageBox.StandardButton.Yes
				if reply == yes_btn:
					self._scan_directory(last_dir)

	#============================================
	def _setup_menus(self):
		"""Create menu bar from YAML configuration."""
		stored = moviemanager.ui.menu_builder.build_menus(self)
		self._undo_rename_action = stored.get("undo_rename_action")
		self._dark_mode_action = stored.get("dark_mode_action")

	#============================================
	def _setup_toolbar(self):
		"""Create toolbar with labeled icons in workflow order."""
		toolbar = self.addToolBar("Main")
		toolbar.setMovable(False)
		# text-under-icon layout with larger icons
		toolbar.setToolButtonStyle(
			PySide6.QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon
		)
		toolbar.setIconSize(PySide6.QtCore.QSize(32, 32))
		# use standard icons from the style (#18)
		style = self.style()
		# open button
		open_btn = PySide6.QtGui.QAction("Open", self)
		open_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon
			)
		)
		open_btn.setToolTip("Open a movie directory (Ctrl+O)")
		open_btn.triggered.connect(self._open_directory)
		toolbar.addAction(open_btn)
		# separator between Open and workflow actions
		toolbar.addSeparator()
		# scrape button
		scrape_btn = PySide6.QtGui.QAction("Scrape", self)
		scrape_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_ArrowDown
			)
		)
		scrape_btn.setToolTip(
			"Scrape metadata from TMDB (Ctrl+Shift+S)"
		)
		scrape_btn.triggered.connect(self._scrape_selected)
		toolbar.addAction(scrape_btn)
		# edit button
		edit_btn = PySide6.QtGui.QAction("Edit", self)
		edit_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView
			)
		)
		edit_btn.setToolTip("Edit movie metadata (Ctrl+E)")
		edit_btn.triggered.connect(self._edit_selected)
		toolbar.addAction(edit_btn)
		# rename button
		rename_btn = PySide6.QtGui.QAction("Rename", self)
		rename_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileIcon
			)
		)
		rename_btn.setToolTip("Rename movie files (F2)")
		rename_btn.triggered.connect(self._rename_selected)
		toolbar.addAction(rename_btn)
		# flexible spacer to push settings/quit to the right
		spacer = PySide6.QtWidgets.QWidget()
		spacer.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Expanding,
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
		)
		toolbar.addWidget(spacer)
		toolbar.addSeparator()
		# settings button
		settings_btn = PySide6.QtGui.QAction("Settings", self)
		settings_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton
			)
		)
		settings_btn.setToolTip("Open settings (Ctrl+,)")
		settings_btn.triggered.connect(self._show_settings)
		toolbar.addAction(settings_btn)
		# quit button
		quit_btn = PySide6.QtGui.QAction("Quit", self)
		quit_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton
			)
		)
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
		"""Scan directory in a background thread (#1)."""
		self._current_directory = directory
		# save last opened directory to settings
		self._settings.last_directory = directory
		moviemanager.core.settings.save_settings(self._settings)
		# clear rename history on directory change
		self._rename_history.clear()
		self._undo_rename_action.setEnabled(False)
		self._status.showMessage(f"Scanning {directory}...")
		self._status.show_progress(0, 0, f"Scanning {directory}...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# run scan in background (#1)
		worker = moviemanager.ui.workers.Worker(
			self._api.scan_directory, directory,
			progress_callback=self._on_scan_progress_callback
		)
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
		# note: this is called from a worker thread but Qt signals
		# are thread-safe for cross-thread emission
		self._status.show_progress(current, 0, message)

	#============================================
	def _on_scan_progress(self, current: int, total: int, message: str) -> None:
		"""Handle scan progress updates on the main thread."""
		self._status.show_progress(current, total, message)

	#============================================
	def _on_scan_done(self, movies) -> None:
		"""Handle scan completion."""
		self.unsetCursor()
		self._status.hide_progress()
		self._movie_panel.set_movies(movies)
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
		"""Scrape metadata for selected movie."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection",
				"Please select a movie first."
			)
			return
		# import and show movie chooser dialog
		import moviemanager.ui.dialogs.movie_chooser
		dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
			movie, self._api, self
		)
		if dialog.exec() == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			# refresh table
			self._movie_panel.set_movies(self._api.get_movies())
			scraped = self._api.get_scraped_count()
			total = self._api.get_movie_count()
			self._status.set_movie_count(total, scraped)
			# transient success message (#24)
			self._status.showMessage("Scrape complete", 3000)

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
		import moviemanager.ui.dialogs.movie_editor
		dialog = moviemanager.ui.dialogs.movie_editor.MovieEditorDialog(
			movie, self
		)
		if dialog.exec() == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			self._movie_panel.set_movies(self._api.get_movies())
			# transient success message (#24)
			self._status.showMessage("Metadata saved", 3000)

	#============================================
	def _rename_selected(self):
		"""Rename selected movie files."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			# show feedback instead of silent return (#3)
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection",
				"Please select a movie first."
			)
			return
		# show preview
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		try:
			pairs = self._api.rename_movie(movie, dry_run=True)
		except Exception as exc:
			self.unsetCursor()
			self._show_error("Rename Error", str(exc))
			return
		self.unsetCursor()
		if not pairs:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Rename", "No files to rename."
			)
			return
		# show rename preview dialog
		import moviemanager.ui.dialogs.rename_preview
		dialog = moviemanager.ui.dialogs.rename_preview.RenamePreviewDialog(
			pairs, self
		)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			try:
				self._api.rename_movie(movie, dry_run=False)
			except Exception as exc:
				self._show_error("Rename Error", str(exc))
				return
			# record rename batch for undo
			self._rename_history.append(pairs)
			self._undo_rename_action.setEnabled(True)
			self._movie_panel.set_movies(self._api.get_movies())
			# transient success message (#24)
			self._status.showMessage("Rename complete", 3000)

	#============================================
	def _undo_last_rename(self) -> None:
		"""Undo the last rename batch by reversing file moves."""
		if not self._rename_history:
			return
		import os
		import shutil
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
		import moviemanager.ui.dialogs.settings_dialog
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
		"""Scrape all unscraped movies using auto-select best match."""
		movies = self._api.get_movies()
		unscraped = [m for m in movies if not m.scraped]
		if not unscraped:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Batch Scrape",
				"All movies are already scraped."
			)
			return
		# show progress dialog
		progress = PySide6.QtWidgets.QProgressDialog(
			"Scraping movies...", "Cancel",
			0, len(unscraped), self
		)
		progress.setWindowModality(
			PySide6.QtCore.Qt.WindowModality.WindowModal
		)
		progress.setMinimumDuration(0)
		scraped_count = 0
		for i, movie in enumerate(unscraped):
			if progress.wasCanceled():
				break
			progress.setValue(i)
			progress.setLabelText(
				f"Scraping: {movie.title} ({i + 1}/{len(unscraped)})"
			)
			# search and auto-select best match
			results = self._api.search_movie(
				movie.title, movie.year
			)
			if results:
				best = results[0]
				self._api.scrape_movie(movie, tmdb_id=best.tmdb_id)
				scraped_count += 1
		progress.setValue(len(unscraped))
		# refresh table
		self._movie_panel.set_movies(self._api.get_movies())
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		self._status.set_movie_count(total, scraped)
		self._status.showMessage(
			f"Batch scrape complete: {scraped_count} movies scraped",
			3000
		)

	#============================================
	def _toggle_dark_mode(self) -> None:
		"""Toggle between dark and system theme."""
		import moviemanager.ui.theme
		if self._settings.theme == "dark":
			self._settings.theme = "system"
		else:
			self._settings.theme = "dark"
		moviemanager.core.settings.save_settings(self._settings)
		app = PySide6.QtWidgets.QApplication.instance()
		moviemanager.ui.theme.apply_theme(app, self._settings.theme)

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
		import os
		if os.path.isdir(path):
			self._scan_directory(path)
		else:
			PySide6.QtWidgets.QMessageBox.warning(
				self, "Invalid Drop",
				"Please drop a directory, not a file."
			)

	#============================================
	def closeEvent(self, event) -> None:
		"""Save window state on close (#20)."""
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
