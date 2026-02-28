"""Main application window."""

# Standard Library
import importlib.metadata

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.api.movie_api
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
		# status bar
		self._status = moviemanager.ui.widgets.status_bar.StatusBar()
		self.setStatusBar(self._status)
		# menu bar
		self._setup_menus()
		# toolbar
		self._setup_toolbar()
		# restore window state (#20)
		self._restore_state()
		# load directory if provided, otherwise prompt user
		if directory:
			self._scan_directory(directory)
		else:
			# prompt user to open a directory on startup
			PySide6.QtCore.QTimer.singleShot(
				100, self._open_directory
			)

	#============================================
	def _setup_menus(self):
		"""Create menu bar."""
		menu_bar = self.menuBar()
		# File menu
		file_menu = menu_bar.addMenu("&File")
		open_action = PySide6.QtGui.QAction("&Open Directory...", self)
		open_action.setShortcut("Ctrl+O")
		open_action.triggered.connect(self._open_directory)
		file_menu.addAction(open_action)
		file_menu.addSeparator()
		quit_action = PySide6.QtGui.QAction("&Quit", self)
		quit_action.setShortcut("Ctrl+Q")
		quit_action.triggered.connect(self.close)
		file_menu.addAction(quit_action)
		# Movie menu
		movie_menu = menu_bar.addMenu("&Movie")
		scrape_action = PySide6.QtGui.QAction("&Scrape Selected", self)
		# reassign scrape shortcut to avoid Ctrl+S conflict (#9)
		scrape_action.setShortcut("Ctrl+Shift+S")
		scrape_action.triggered.connect(self._scrape_selected)
		movie_menu.addAction(scrape_action)
		edit_action = PySide6.QtGui.QAction("&Edit Selected", self)
		edit_action.setShortcut("Ctrl+E")
		edit_action.triggered.connect(self._edit_selected)
		movie_menu.addAction(edit_action)
		rename_action = PySide6.QtGui.QAction("&Rename Selected", self)
		# add Rename shortcut (#16)
		rename_action.setShortcut("F2")
		rename_action.triggered.connect(self._rename_selected)
		movie_menu.addAction(rename_action)
		# Help menu
		help_menu = menu_bar.addMenu("&Help")
		about_action = PySide6.QtGui.QAction("&About", self)
		about_action.triggered.connect(self._show_about)
		help_menu.addAction(about_action)

	#============================================
	def _setup_toolbar(self):
		"""Create toolbar with icons and tooltips."""
		toolbar = self.addToolBar("Main")
		toolbar.setMovable(False)
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
		# settings button
		settings_btn = PySide6.QtGui.QAction("Settings", self)
		settings_btn.setIcon(
			style.standardIcon(
				PySide6.QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon
			)
		)
		settings_btn.setToolTip("Application settings")
		settings_btn.triggered.connect(self._show_settings)
		toolbar.addAction(settings_btn)

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
		self._status.showMessage(f"Scanning {directory}...")
		self._status.show_progress(0, 0, f"Scanning {directory}...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# run scan in background (#1)
		worker = moviemanager.ui.workers.Worker(
			self._api.scan_directory, directory
		)
		worker.signals.finished.connect(self._on_scan_done)
		worker.signals.error.connect(self._on_scan_error)
		self._pool.start(worker)

	#============================================
	def _on_scan_done(self, movies) -> None:
		"""Handle scan completion."""
		self.unsetCursor()
		self._status.hide_progress()
		self._movie_panel.set_movies(movies)
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		self._status.set_movie_count(total, scraped)
		# transient success message (#24)
		self._status.showMessage(
			f"Scan complete: {total} movies found", 3000
		)

	#============================================
	def _on_scan_error(self, error_text: str) -> None:
		"""Handle scan error (#2)."""
		self.unsetCursor()
		self._status.hide_progress()
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Scan Error",
			f"Failed to scan directory:\n{error_text}"
		)

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
			PySide6.QtWidgets.QMessageBox.critical(
				self, "Rename Error",
				f"Failed to generate rename preview:\n{exc}"
			)
			return
		self.unsetCursor()
		if not pairs:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Rename", "No files to rename."
			)
			return
		# build preview text
		preview_lines = []
		for src, dst in pairs:
			preview_lines.append(f"{src}\n  -> {dst}")
		preview_text = "\n".join(preview_lines)
		reply = PySide6.QtWidgets.QMessageBox.question(
			self, "Rename Preview", preview_text,
			PySide6.QtWidgets.QMessageBox.StandardButton.Ok
			| PySide6.QtWidgets.QMessageBox.StandardButton.Cancel,
		)
		ok_button = PySide6.QtWidgets.QMessageBox.StandardButton.Ok
		if reply == ok_button:
			try:
				self._api.rename_movie(movie, dry_run=False)
			except Exception as exc:
				PySide6.QtWidgets.QMessageBox.critical(
					self, "Rename Error",
					f"Failed to rename files:\n{exc}"
				)
				return
			self._movie_panel.set_movies(self._api.get_movies())
			# transient success message (#24)
			self._status.showMessage("Rename complete", 3000)

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
