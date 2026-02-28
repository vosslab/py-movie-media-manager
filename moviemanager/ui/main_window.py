"""Main application window."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui

# local repo modules
import moviemanager.api.movie_api
import moviemanager.ui.movies.movie_panel
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
		# load directory if provided
		if directory:
			self._scan_directory(directory)

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
		scrape_action.setShortcut("Ctrl+S")
		scrape_action.triggered.connect(self._scrape_selected)
		movie_menu.addAction(scrape_action)
		edit_action = PySide6.QtGui.QAction("&Edit Selected", self)
		edit_action.setShortcut("Ctrl+E")
		edit_action.triggered.connect(self._edit_selected)
		movie_menu.addAction(edit_action)
		rename_action = PySide6.QtGui.QAction("&Rename Selected", self)
		rename_action.triggered.connect(self._rename_selected)
		movie_menu.addAction(rename_action)
		# Help menu
		help_menu = menu_bar.addMenu("&Help")
		about_action = PySide6.QtGui.QAction("&About", self)
		about_action.triggered.connect(self._show_about)
		help_menu.addAction(about_action)

	#============================================
	def _setup_toolbar(self):
		"""Create toolbar."""
		toolbar = self.addToolBar("Main")
		toolbar.setMovable(False)
		# open button
		open_btn = PySide6.QtGui.QAction("Open", self)
		open_btn.triggered.connect(self._open_directory)
		toolbar.addAction(open_btn)
		# scrape button
		scrape_btn = PySide6.QtGui.QAction("Scrape", self)
		scrape_btn.triggered.connect(self._scrape_selected)
		toolbar.addAction(scrape_btn)
		# edit button
		edit_btn = PySide6.QtGui.QAction("Edit", self)
		edit_btn.triggered.connect(self._edit_selected)
		toolbar.addAction(edit_btn)
		# rename button
		rename_btn = PySide6.QtGui.QAction("Rename", self)
		rename_btn.triggered.connect(self._rename_selected)
		toolbar.addAction(rename_btn)
		# settings button
		settings_btn = PySide6.QtGui.QAction("Settings", self)
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
		"""Scan directory and populate table."""
		self._status.showMessage(f"Scanning {directory}...")
		movies = self._api.scan_directory(directory)
		self._movie_panel.set_movies(movies)
		scraped = self._api.get_scraped_count()
		total = self._api.get_movie_count()
		self._status.set_movie_count(total, scraped)
		self._status.clearMessage()

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

	#============================================
	def _rename_selected(self):
		"""Rename selected movie files."""
		movie = self._movie_panel.get_selected_movie()
		if not movie:
			return
		# show preview
		pairs = self._api.rename_movie(movie, dry_run=True)
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
			self._api.rename_movie(movie, dry_run=False)
			self._movie_panel.set_movies(self._api.get_movies())

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
		"""Show about dialog."""
		PySide6.QtWidgets.QMessageBox.about(
			self, "About Movie Media Manager",
			"Movie Media Manager\n"
			"A Python tool for organizing movie media.\n\n"
			"Inspired by tinyMediaManager."
		)
