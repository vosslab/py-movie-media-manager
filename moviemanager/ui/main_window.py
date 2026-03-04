"""Main application window."""

# Standard Library
import os
import importlib.metadata

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.settings
import moviemanager.ui.task_api
import moviemanager.ui.controllers.scan_controller
import moviemanager.ui.controllers.match_controller
import moviemanager.ui.controllers.rename_controller
import moviemanager.ui.controllers.download_controller
import moviemanager.ui.dialogs.movie_editor
import moviemanager.ui.dialogs.settings_dialog
import moviemanager.ui.dialogs.jobs_dialog
import moviemanager.ui.menu_builder
import moviemanager.ui.movies.movie_panel
import moviemanager.ui.task_dispatcher
import moviemanager.ui.toolbar_builder
import moviemanager.ui.theme
import moviemanager.ui.widgets.status_bar


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
		self._movie_panel.set_settings(settings)
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
		self._status.jobs_clicked.connect(self._show_jobs_dialog)
		# pause/resume wiring
		self._status.pause_toggled.connect(
			self._on_pause_toggled
		)
		self._task_api.paused_changed.connect(
			self._status.set_paused
		)
		self._task_api.job_list_changed.connect(
			self._update_jobs_count
		)
		self.setStatusBar(self._status)
		# create controllers
		self._scan_ctrl = (
			moviemanager.ui.controllers.scan_controller
			.ScanController(self._api, self._task_api, self)
		)
		self._match_ctrl = (
			moviemanager.ui.controllers.match_controller
			.MatchController(self._api, self._task_api, self)
		)
		self._rename_ctrl = (
			moviemanager.ui.controllers.rename_controller
			.RenameController(self._api, self._task_api, self)
		)
		self._download_ctrl = (
			moviemanager.ui.controllers.download_controller
			.DownloadController(
				self._api, self._task_api,
				self._settings, self,
			)
		)
		# central task dispatcher for all TaskAPI signals
		self._dispatcher = (
			moviemanager.ui.task_dispatcher.TaskDispatcher(
				self._scan_ctrl, self._match_ctrl,
				self._rename_ctrl, self._download_ctrl,
				self._status, parent=self,
			)
		)
		self._task_api.task_finished.connect(
			self._dispatcher.on_task_finished
		)
		self._task_api.task_error.connect(
			self._dispatcher.on_task_error
		)
		self._task_api.task_progress.connect(
			self._dispatcher.on_task_progress
		)
		# wire controller signals
		self._wire_scan_signals()
		self._wire_match_signals()
		self._wire_rename_signals()
		self._wire_download_signals()
		# menu bar
		self._setup_menus()
		# toolbar
		self._setup_toolbar()
		# restore window state (#20)
		self._restore_state()
		# track current directory for re-scan and title
		self._current_directory = ""
		# load directory if provided, otherwise auto-open last folder
		if directory:
			self._scan_directory(directory)
		elif self._settings.last_directory:
			last_dir = self._settings.last_directory
			if os.path.isdir(last_dir):
				self._scan_directory(last_dir)

	#============================================
	def _wire_scan_signals(self) -> None:
		"""Connect ScanController signals to UI update slots."""
		ctrl = self._scan_ctrl
		ctrl.scan_started.connect(self._on_scan_started)
		ctrl.scan_progress.connect(self._on_scan_progress)
		ctrl.scan_completed.connect(self._on_scan_completed)
		ctrl.movies_added.connect(self._on_movies_added)
		ctrl.scan_error.connect(
			lambda err: self._show_error("Scan Error", err)
		)
		ctrl.badges_ready.connect(self._apply_badge_counts)
		ctrl.probe_progress.connect(self._on_probe_progress)
		ctrl.probe_completed.connect(self._on_probe_completed)
		ctrl.probe_error.connect(self._on_probe_error)

	#============================================
	def _wire_match_signals(self) -> None:
		"""Connect MatchController signals to UI update slots."""
		ctrl = self._match_ctrl
		ctrl.scrape_completed.connect(self._on_scrape_completed)
		ctrl.metadata_updated.connect(self._on_metadata_updated)
		ctrl.parental_guides_completed.connect(
			self._on_parental_guides_completed
		)

	#============================================
	def _wire_rename_signals(self) -> None:
		"""Connect RenameController signals to UI update slots."""
		ctrl = self._rename_ctrl
		ctrl.rename_started.connect(self._on_rename_started)
		ctrl.rename_completed.connect(self._on_rename_completed)
		ctrl.rename_error.connect(
			lambda err: self._show_error("Organize Error", err)
		)
		ctrl.undo_completed.connect(self._on_undo_completed)

	#============================================
	def _wire_download_signals(self) -> None:
		"""Connect DownloadController signals to UI update slots."""
		ctrl = self._download_ctrl
		ctrl.download_started.connect(self._on_download_started)
		ctrl.download_completed.connect(self._on_download_completed)

	#============================================
	# -- UI setup --
	#============================================

	#============================================
	def _setup_menus(self):
		"""Create menu bar from YAML configuration."""
		stored = moviemanager.ui.menu_builder.build_menus(self)
		self._undo_rename_action = stored.get("undo_rename_action")
		self._dark_mode_action = stored.get("dark_mode_action")

	#============================================
	def _setup_toolbar(self):
		"""Create toolbar with labeled icons via toolbar_builder."""
		refs = moviemanager.ui.toolbar_builder.build_toolbar(self)
		self._match_btn = refs["match_btn"]
		self._organize_btn = refs["organize_btn"]
		self._download_btn = refs["download_btn"]
		self._dark_toggle = refs["dark_toggle"]

	#============================================
	# -- action delegates to controllers --
	#============================================

	#============================================
	def _open_directory(self):
		"""Open a directory chooser and scan."""
		directory = (
			PySide6.QtWidgets.QFileDialog
			.getExistingDirectory(
				self, "Select Movie Directory"
			)
		)
		if directory:
			self._scan_directory(directory)

	#============================================
	def _scan_directory(self, directory: str):
		"""Start a directory scan via the scan controller.

		Args:
			directory: Path to the directory to scan.
		"""
		self._current_directory = directory
		# save last opened directory to settings
		self._settings.last_directory = directory
		moviemanager.core.settings.save_settings(
			self._settings
		)
		# clear rename history on directory change
		self._rename_ctrl.clear_history()
		self._undo_rename_action.setEnabled(False)
		# clear table and prepare for incremental loading
		self._movie_panel.set_movies([])
		self._movie_panel.set_sorting_enabled(False)
		# delegate to scan controller
		self._scan_ctrl.scan_directory(directory)

	#============================================
	def _scrape_selected(self):
		"""Scrape metadata for selected or checked movies."""
		self._match_ctrl.scrape_selected(
			self._movie_panel, self
		)

	#============================================
	def _rename_selected(self):
		"""Organize selected movie files into folders."""
		self._rename_ctrl.rename_selected(
			self._movie_panel, self
		)

	#============================================
	def _download_content(self):
		"""Download artwork, trailers, and subtitles."""
		self._download_ctrl.download_content(
			self._movie_panel, self
		)

	#============================================
	def _refresh_metadata(self):
		"""Re-fetch metadata from IMDB/TMDB for matched movies."""
		self._match_ctrl.refresh_metadata(
			self._movie_panel, self
		)

	#============================================
	def _fetch_parental_guides(self):
		"""Fetch parental guide data from IMDB."""
		self._match_ctrl.fetch_parental_guides(
			self._movie_panel, self
		)

	#============================================
	def _refresh_file_stats(self) -> None:
		"""Re-probe video files for codec, resolution, and duration."""
		self._scan_ctrl.start_media_probe()

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
		dialog = (
			moviemanager.ui.dialogs.movie_editor
			.MovieEditorDialog(movie, self)
		)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			self._movie_panel.refresh_data()
			self._status.showMessage("Metadata saved", 3000)

	#============================================
	def _show_settings(self):
		"""Show settings dialog."""
		dialog = (
			moviemanager.ui.dialogs.settings_dialog
			.SettingsDialog(self._settings, self)
		)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			self._settings = dialog.get_settings()
			# reinitialize API with new settings
			self._api = moviemanager.api.movie_api.MovieAPI(
				self._settings
			)
			# update controllers with new API/settings
			self._scan_ctrl.set_api(self._api)
			self._match_ctrl.set_api(self._api)
			self._rename_ctrl.set_api(self._api)
			self._download_ctrl.set_api(self._api)
			self._download_ctrl.set_settings(self._settings)
			# update movie panel with new settings for artwork checks
			self._movie_panel.set_settings(self._settings)

	#============================================
	def _show_about(self):
		"""Show about dialog with version, author, and license."""
		try:
			version = importlib.metadata.version(
				"movie-media-manager"
			)
		except importlib.metadata.PackageNotFoundError:
			version = "dev"
		about_text = (
			f"Movie Media Manager v{version}\n\n"
			"A Python tool for organizing movie media.\n"
			"Inspired by tinyMediaManager.\n\n"
			"Author: Neil Voss\n"
			"License: GPL-3.0-or-later\n"
			"https://bsky.app/profile/"
			"neilvosslab.bsky.social"
		)
		PySide6.QtWidgets.QMessageBox.about(
			self, "About Movie Media Manager", about_text
		)

	#============================================
	def _toggle_dark_mode(self) -> None:
		"""Toggle between dark and system theme."""
		if self._settings.theme == "dark":
			self._settings.theme = "system"
		else:
			self._settings.theme = "dark"
		moviemanager.core.settings.save_settings(
			self._settings
		)
		app = PySide6.QtWidgets.QApplication.instance()
		moviemanager.ui.theme.apply_theme(
			app, self._settings.theme
		)

	#============================================
	def _undo_last_rename(self) -> None:
		"""Undo the last rename batch."""
		self._rename_ctrl.undo_last_rename(self)

	#============================================
	def _download_trailer(self) -> None:
		"""Download trailer for selected movie."""
		self._download_ctrl.download_trailer(
			self._movie_panel, self
		)
		self._status.showMessage(
			"Trailer download queued", 3000
		)

	#============================================
	def _download_subtitles(self) -> None:
		"""Download subtitles for selected movie."""
		self._download_ctrl.download_subtitles(
			self._movie_panel, self
		)
		self._status.showMessage(
			"Subtitle download queued", 3000
		)

	#============================================
	def _batch_scrape_unscraped(self) -> None:
		"""Scrape all unscraped movies automatically."""
		self._match_ctrl.batch_scrape_unscraped(self)

	#============================================
	def _cancel_operation(self) -> None:
		"""Cancel the currently running background operation."""
		self._scan_ctrl.cancel()
		self._match_ctrl.cancel()
		self._rename_ctrl.cancel()
		self._download_ctrl.cancel()
		self.unsetCursor()
		self._status.hide_progress()
		self._status.showMessage("Operation cancelled", 3000)

	#============================================
	def _on_pause_toggled(self, paused: bool) -> None:
		"""Handle pause/resume toggle from the status bar.

		Args:
			paused: True to pause, False to resume.
		"""
		if paused:
			self._task_api.pause()
			self._status.showMessage("Job queue paused", 3000)
		else:
			self._task_api.resume()
			pending = self._task_api.pending_count
			msg = "Job queue resumed"
			if pending > 0:
				msg += f" ({pending} pending jobs started)"
			self._status.showMessage(msg, 3000)

	#============================================
	# -- UI update slots (connected to controller signals) --
	#============================================

	#============================================
	def _on_scan_started(self, directory: str) -> None:
		"""Handle scan start: update status and cursor.

		Args:
			directory: Path being scanned.
		"""
		self._status.showMessage(f"Scanning {directory}...")
		self._status.show_progress(
			0, 0, f"Scanning {directory}..."
		)
		self.setCursor(
			PySide6.QtCore.Qt.CursorShape.WaitCursor
		)

	#============================================
	def _on_scan_progress(
		self, current: int, total: int, message: str,
	) -> None:
		"""Handle scan progress updates."""
		self._status.show_progress(current, total, message)

	#============================================
	def _on_movies_added(self, movies: list) -> None:
		"""Handle incremental movie batch from scan controller.

		Args:
			movies: Batch of Movie instances to append.
		"""
		self._movie_panel.append_movies(movies)

	#============================================
	def _on_scan_completed(
		self, total: int, scraped: int,
	) -> None:
		"""Handle scan completion: update UI state.

		Args:
			total: Total number of movies found.
			scraped: Number of scraped movies.
		"""
		# re-enable sorting now that all movies are loaded
		self._movie_panel.set_sorting_enabled(True)
		self.unsetCursor()
		self._status.hide_progress()
		self._status.set_movie_count(total, scraped)
		# update window title with current directory
		self.setWindowTitle(
			f"Movie Media Manager - {self._current_directory}"
		)
		self._status.showMessage(
			f"Scan complete: {total} movies found", 3000
		)

	#============================================
	def _on_probe_progress(
		self, current: int, total: int, message: str,
	) -> None:
		"""Handle probe progress updates."""
		self._status.show_progress(current, total, message)
		# refresh table less frequently
		if current % 25 == 0 or current == total:
			self._movie_panel.refresh_data()

	#============================================
	def _on_probe_completed(self) -> None:
		"""Handle probe completion: refresh table and clear status."""
		self._status.hide_progress()
		self._movie_panel.refresh_data()
		self._status.showMessage("Media probe complete", 3000)

	#============================================
	def _on_probe_error(self, error_text: str) -> None:
		"""Handle probe error."""
		self._status.hide_progress()
		msg = f"Media probe error: {error_text[:80]}"
		self._status.showMessage(msg, 5000)

	#============================================
	def _apply_badge_counts(self, counts: tuple) -> None:
		"""Apply badge counts to toolbar buttons.

		Args:
			counts: Tuple of (unmatched, unorganized, incomplete).
		"""
		unmatched, unorganized, incomplete = counts
		if unmatched > 0:
			self._match_btn.setText(
				f"1. Match ({unmatched})"
			)
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
	def _on_scrape_completed(self, result: dict) -> None:
		"""Handle scrape completion: refresh table and badges."""
		self._status.hide_progress()
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		# show workflow hint
		if result.get("batch"):
			matched = result.get("matched", 0)
			total = result.get("total", 0)
			self._status.showMessage(
				f"Matched {matched}/{total} movies"
				" -- ready to organize (Step 2)",
				8000,
			)
		else:
			self._status.showMessage(
				"Match complete"
				" -- ready to organize (Step 2)",
				5000,
			)
		self._scan_ctrl.update_badges()

	#============================================
	def _on_metadata_updated(self, result: dict) -> None:
		"""Handle metadata refresh completion."""
		self._status.hide_progress()
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		self._scan_ctrl.update_badges()

	#============================================
	def _on_parental_guides_completed(
		self, result: dict,
	) -> None:
		"""Handle parental guide fetch completion."""
		self._status.hide_progress()
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		self._scan_ctrl.update_badges()

	#============================================
	def _on_rename_started(self) -> None:
		"""Handle rename start: update cursor and status."""
		self._status.showMessage("Organizing files...")
		self.setCursor(
			PySide6.QtCore.Qt.CursorShape.WaitCursor
		)

	#============================================
	def _on_rename_completed(self, count: int) -> None:
		"""Handle rename completion.

		Args:
			count: Number of files renamed.
		"""
		self.unsetCursor()
		self._undo_rename_action.setEnabled(True)
		self._movie_panel.refresh_data()
		self._status.showMessage(
			f"Organized {count} file(s)"
			" -- ready to download content (Step 3)",
			8000,
		)
		self._scan_ctrl.update_badges()

	#============================================
	def _on_undo_completed(self, count: int) -> None:
		"""Handle undo rename completion.

		Args:
			count: Number of files restored.
		"""
		if not self._rename_ctrl.has_undo_history:
			self._undo_rename_action.setEnabled(False)
		self._movie_panel.set_movies(
			self._api.get_movies()
		)
		self._status.showMessage(
			f"Undo complete: {count} file(s) restored", 3000
		)

	#============================================
	def _on_download_started(self, count: int) -> None:
		"""Handle download batch start.

		Args:
			count: Number of downloads queued.
		"""
		self._status.showMessage(
			f"Queued {count} downloads -- see Jobs dialog",
			5000,
		)

	#============================================
	def _on_download_completed(self) -> None:
		"""Handle all downloads complete."""
		self._movie_panel.refresh_data()
		self._refresh_status_counts()
		self._scan_ctrl.update_badges()
		self._status.showMessage(
			"All downloads complete", 5000
		)

	#============================================
	def _on_checked_changed(
		self, checked: int, total: int,
	) -> None:
		"""Update status bar when checkbox selection changes.

		Args:
			checked: Number of checked movies.
			total: Total number of visible movies.
		"""
		if checked > 0:
			self._status.set_checked_count(checked, total)
		else:
			self._refresh_status_counts()

	#============================================
	def _refresh_status_counts(self) -> None:
		"""Update status bar movie/scraped counts from API."""
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		self._status.set_movie_count(total, scraped)

	#============================================
	def _update_jobs_count(self) -> None:
		"""Update the status bar jobs button with active count."""
		self._status.update_job_count(
			self._task_api.active_count
		)

	#============================================
	def _show_jobs_dialog(self) -> None:
		"""Show the background jobs popup dialog."""
		if self._jobs_dialog is None:
			self._jobs_dialog = (
				moviemanager.ui.dialogs.jobs_dialog
				.JobsDialog(self._task_api, self)
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
	def _on_context_action(
		self, action: str, movie,
	) -> None:
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
	def _show_error(
		self, title: str, error_text: str,
	) -> None:
		"""Show a user-friendly error dialog with detail text.

		Args:
			title: Dialog window title.
			error_text: Full traceback or error text.
		"""
		self.unsetCursor()
		self._status.hide_progress()
		lines = error_text.strip().splitlines()
		summary = lines[-1] if lines else "Unknown error"
		msg = PySide6.QtWidgets.QMessageBox(self)
		msg.setIcon(
			PySide6.QtWidgets.QMessageBox.Icon.Critical
		)
		msg.setWindowTitle(title)
		msg.setText(summary)
		msg.setDetailedText(error_text)
		msg.exec()

	#============================================
	# -- Qt events --
	#============================================

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
		"""Save window state on close, warn if jobs running."""
		if self._task_api.active_count > 0:
			reply = PySide6.QtWidgets.QMessageBox.question(
				self, "Jobs In Progress",
				f"{self._task_api.active_count}"
				" background job(s) still running."
				"\nQuit anyway?",
				PySide6.QtWidgets.QMessageBox
				.StandardButton.Yes
				| PySide6.QtWidgets.QMessageBox
				.StandardButton.No,
			)
			yes = (
				PySide6.QtWidgets.QMessageBox
				.StandardButton.Yes
			)
			if reply != yes:
				event.ignore()
				return
		settings = PySide6.QtCore.QSettings(
			"MovieMediaManager", "MovieMediaManager"
		)
		settings.setValue("geometry", self.saveGeometry())
		settings.setValue("windowState", self.saveState())
		self._movie_panel.save_table_state(settings)
		# shutdown order: drain task pool, then image pool, then API
		self._task_api.shutdown()
		self._movie_panel.shutdown_detail_panel()
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
		self._movie_panel.restore_table_state(settings)
