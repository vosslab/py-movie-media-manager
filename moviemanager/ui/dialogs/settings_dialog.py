"""Application settings dialog."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import moviemanager.core.settings


#============================================
class SettingsDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for editing application settings."""

	def __init__(self, settings, parent=None):
		super().__init__(parent)
		self._settings = settings
		self.setWindowTitle("Settings")
		self.resize(500, 400)
		self._setup_ui()
		self._load_settings()

	#============================================
	def _setup_ui(self):
		"""Build the tabbed settings form and buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# tabs for different settings groups
		tabs = PySide6.QtWidgets.QTabWidget()
		# API Keys tab
		api_widget = PySide6.QtWidgets.QWidget()
		api_layout = PySide6.QtWidgets.QFormLayout(api_widget)
		self._tmdb_key_edit = PySide6.QtWidgets.QLineEdit()
		self._tmdb_key_edit.setEchoMode(
			PySide6.QtWidgets.QLineEdit.EchoMode.Password
		)
		api_layout.addRow("TMDB API Key:", self._tmdb_key_edit)
		self._fanart_key_edit = PySide6.QtWidgets.QLineEdit()
		self._fanart_key_edit.setEchoMode(
			PySide6.QtWidgets.QLineEdit.EchoMode.Password
		)
		api_layout.addRow(
			"Fanart.tv API Key:", self._fanart_key_edit
		)
		tabs.addTab(api_widget, "API Keys")
		# Scraping tab
		scrape_widget = PySide6.QtWidgets.QWidget()
		scrape_layout = PySide6.QtWidgets.QFormLayout(
			scrape_widget
		)
		self._language_edit = PySide6.QtWidgets.QLineEdit()
		self._language_edit.setMaximumWidth(60)
		scrape_layout.addRow("Language:", self._language_edit)
		self._country_edit = PySide6.QtWidgets.QLineEdit()
		self._country_edit.setMaximumWidth(60)
		scrape_layout.addRow("Country:", self._country_edit)
		self._cert_country_edit = PySide6.QtWidgets.QLineEdit()
		self._cert_country_edit.setMaximumWidth(60)
		scrape_layout.addRow(
			"Certification Country:", self._cert_country_edit
		)
		tabs.addTab(scrape_widget, "Scraping")
		# Renamer tab
		rename_widget = PySide6.QtWidgets.QWidget()
		rename_layout = PySide6.QtWidgets.QFormLayout(
			rename_widget
		)
		self._path_template_edit = PySide6.QtWidgets.QLineEdit()
		rename_layout.addRow(
			"Path Template:", self._path_template_edit
		)
		self._file_template_edit = PySide6.QtWidgets.QLineEdit()
		rename_layout.addRow(
			"File Template:", self._file_template_edit
		)
		tabs.addTab(rename_widget, "Renamer")
		# Artwork tab
		artwork_widget = PySide6.QtWidgets.QWidget()
		artwork_layout = PySide6.QtWidgets.QVBoxLayout(
			artwork_widget
		)
		self._poster_check = PySide6.QtWidgets.QCheckBox(
			"Download Poster"
		)
		artwork_layout.addWidget(self._poster_check)
		self._fanart_check = PySide6.QtWidgets.QCheckBox(
			"Download Fanart"
		)
		artwork_layout.addWidget(self._fanart_check)
		self._banner_check = PySide6.QtWidgets.QCheckBox(
			"Download Banner"
		)
		artwork_layout.addWidget(self._banner_check)
		self._clearart_check = PySide6.QtWidgets.QCheckBox(
			"Download Clearart"
		)
		artwork_layout.addWidget(self._clearart_check)
		self._logo_check = PySide6.QtWidgets.QCheckBox(
			"Download Logo"
		)
		artwork_layout.addWidget(self._logo_check)
		self._discart_check = PySide6.QtWidgets.QCheckBox(
			"Download Disc Art"
		)
		artwork_layout.addWidget(self._discart_check)
		artwork_layout.addStretch()
		tabs.addTab(artwork_widget, "Artwork")
		layout.addWidget(tabs)
		# buttons
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		save_btn = PySide6.QtWidgets.QPushButton("Save")
		save_btn.clicked.connect(self._save)
		btn_layout.addWidget(save_btn)
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(cancel_btn)
		layout.addLayout(btn_layout)

	#============================================
	def _load_settings(self):
		"""Populate form from settings."""
		s = self._settings
		self._tmdb_key_edit.setText(s.tmdb_api_key)
		self._fanart_key_edit.setText(s.fanart_api_key)
		self._language_edit.setText(s.scrape_language)
		self._country_edit.setText(s.scrape_country)
		self._cert_country_edit.setText(s.certification_country)
		self._path_template_edit.setText(s.path_template)
		self._file_template_edit.setText(s.file_template)
		self._poster_check.setChecked(s.download_poster)
		self._fanart_check.setChecked(s.download_fanart)
		self._banner_check.setChecked(s.download_banner)
		self._clearart_check.setChecked(s.download_clearart)
		self._logo_check.setChecked(s.download_logo)
		self._discart_check.setChecked(s.download_discart)

	#============================================
	def _save(self):
		"""Save form values to settings and write config."""
		s = self._settings
		s.tmdb_api_key = self._tmdb_key_edit.text()
		s.fanart_api_key = self._fanart_key_edit.text()
		s.scrape_language = self._language_edit.text()
		s.scrape_country = self._country_edit.text()
		s.certification_country = self._cert_country_edit.text()
		s.path_template = self._path_template_edit.text()
		s.file_template = self._file_template_edit.text()
		s.download_poster = self._poster_check.isChecked()
		s.download_fanart = self._fanart_check.isChecked()
		s.download_banner = self._banner_check.isChecked()
		s.download_clearart = self._clearart_check.isChecked()
		s.download_logo = self._logo_check.isChecked()
		s.download_discart = self._discart_check.isChecked()
		# write to disk
		moviemanager.core.settings.save_settings(s)
		self.accept()

	#============================================
	def get_settings(self):
		"""Return the settings object.

		Returns:
			The Settings instance with updated values.
		"""
		return self._settings
