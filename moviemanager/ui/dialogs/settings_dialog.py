"""Application settings dialog."""

# Standard Library
import webbrowser

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import moviemanager.core.settings
import moviemanager.core.utils


#============================================
class SettingsDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for editing application settings."""

	def __init__(self, settings, parent=None):
		super().__init__(parent)
		self._settings = settings
		self.setWindowTitle("Settings")
		self.resize(500, 450)
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
		# scraper provider combobox
		self._provider_combo = PySide6.QtWidgets.QComboBox()
		self._provider_combo.addItem(
			"IMDB (no key required)", "imdb"
		)
		self._provider_combo.addItem(
			"TMDB (key required)", "tmdb"
		)
		api_layout.addRow("Scraper Provider:", self._provider_combo)
		# TMDB API key with Get Key button
		tmdb_row = PySide6.QtWidgets.QHBoxLayout()
		self._tmdb_key_edit = PySide6.QtWidgets.QLineEdit()
		self._tmdb_key_edit.setEchoMode(
			PySide6.QtWidgets.QLineEdit.EchoMode.Password
		)
		tmdb_row.addWidget(self._tmdb_key_edit)
		tmdb_get_btn = PySide6.QtWidgets.QPushButton("Get Key")
		tmdb_get_btn.clicked.connect(
			lambda: webbrowser.open(
				"https://www.themoviedb.org/settings/api"
			)
		)
		tmdb_row.addWidget(tmdb_get_btn)
		api_layout.addRow("TMDB API Key:", tmdb_row)
		# IMDB browser-cookie settings
		self._imdb_cookies_enabled_check = PySide6.QtWidgets.QCheckBox(
			"Enable"
		)
		api_layout.addRow(
			"Use Browser Cookies for IMDB:",
			self._imdb_cookies_enabled_check,
		)
		self._imdb_browser_combo = PySide6.QtWidgets.QComboBox()
		self._imdb_browser_combo.addItem("Firefox", "firefox")
		api_layout.addRow("IMDB Cookie Browser:", self._imdb_browser_combo)
		# Fanart.tv API key with Get Key button
		fanart_row = PySide6.QtWidgets.QHBoxLayout()
		self._fanart_key_edit = PySide6.QtWidgets.QLineEdit()
		self._fanart_key_edit.setEchoMode(
			PySide6.QtWidgets.QLineEdit.EchoMode.Password
		)
		fanart_row.addWidget(self._fanart_key_edit)
		fanart_get_btn = PySide6.QtWidgets.QPushButton("Get Key")
		fanart_get_btn.clicked.connect(
			lambda: webbrowser.open(
				"https://fanart.tv/get-an-api-key/"
			)
		)
		fanart_row.addWidget(fanart_get_btn)
		api_layout.addRow("Fanart.tv API Key:", fanart_row)
		# OpenSubtitles API key with Get Key button
		osub_row = PySide6.QtWidgets.QHBoxLayout()
		self._osub_key_edit = PySide6.QtWidgets.QLineEdit()
		self._osub_key_edit.setEchoMode(
			PySide6.QtWidgets.QLineEdit.EchoMode.Password
		)
		osub_row.addWidget(self._osub_key_edit)
		osub_get_btn = PySide6.QtWidgets.QPushButton("Get Key")
		osub_get_btn.clicked.connect(
			lambda: webbrowser.open(
				"https://www.opensubtitles.com/"
			)
		)
		osub_row.addWidget(osub_get_btn)
		api_layout.addRow("OpenSubtitles API Key:", osub_row)
		# theme combobox
		self._theme_combo = PySide6.QtWidgets.QComboBox()
		self._theme_combo.addItem("System", "system")
		self._theme_combo.addItem("Light", "light")
		self._theme_combo.addItem("Dark", "dark")
		api_layout.addRow("Theme:", self._theme_combo)
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
		# help text for path template variables (#12)
		path_help = PySide6.QtWidgets.QLabel(
			"Variables: {title}, {year}, {rating}, "
			"{certification}, {genre}"
		)
		# use palette-aware styling instead of hardcoded colors (#23)
		path_help_font = path_help.font()
		path_help_font.setPointSizeF(
			path_help_font.pointSizeF() * 0.85
		)
		path_help.setFont(path_help_font)
		path_help.setForegroundRole(
			PySide6.QtGui.QPalette.ColorRole.PlaceholderText
		)
		path_help.setWordWrap(True)
		rename_layout.addRow("", path_help)
		self._file_template_edit = PySide6.QtWidgets.QLineEdit()
		rename_layout.addRow(
			"File Template:", self._file_template_edit
		)
		# help text for file template variables (#12)
		file_help = PySide6.QtWidgets.QLabel(
			"Variables: {title}, {year}, {rating}, "
			"{certification}, {genre}"
		)
		# use palette-aware styling instead of hardcoded colors (#23)
		file_help_font = file_help.font()
		file_help_font.setPointSizeF(
			file_help_font.pointSizeF() * 0.85
		)
		file_help.setFont(file_help_font)
		file_help.setForegroundRole(
			PySide6.QtGui.QPalette.ColorRole.PlaceholderText
		)
		file_help.setWordWrap(True)
		rename_layout.addRow("", file_help)
		# separator combo for media tokens
		self._separator_combo = PySide6.QtWidgets.QComboBox()
		self._separator_combo.addItem("Hyphen (-)", "-")
		self._separator_combo.addItem("Dot (.)", ".")
		self._separator_combo.addItem("Underscore (_)", "_")
		rename_layout.addRow("Token Separator:", self._separator_combo)
		# media token checkboxes
		media_label = PySide6.QtWidgets.QLabel("Append Media Tokens:")
		rename_layout.addRow(media_label)
		self._res_check = PySide6.QtWidgets.QCheckBox(
			"Resolution (1080p, 720p, 4K)"
		)
		rename_layout.addRow("", self._res_check)
		self._vcodec_check = PySide6.QtWidgets.QCheckBox(
			"Video Codec (h264, hevc)"
		)
		rename_layout.addRow("", self._vcodec_check)
		self._acodec_check = PySide6.QtWidgets.QCheckBox(
			"Audio Codec (aac, ac3, dts)"
		)
		rename_layout.addRow("", self._acodec_check)
		self._channels_check = PySide6.QtWidgets.QCheckBox(
			"Audio Channels (5.1, 7.1)"
		)
		rename_layout.addRow("", self._channels_check)
		# shell-safe naming option
		self._spaces_check = PySide6.QtWidgets.QCheckBox(
			"Shell-safe filenames (ASCII, no spaces or special characters)"
		)
		rename_layout.addRow("", self._spaces_check)
		# live preview of folder name
		self._rename_preview = PySide6.QtWidgets.QLabel("")
		preview_font = self._rename_preview.font()
		preview_font.setPointSizeF(preview_font.pointSizeF() * 0.9)
		self._rename_preview.setFont(preview_font)
		self._rename_preview.setForegroundRole(
			PySide6.QtGui.QPalette.ColorRole.PlaceholderText
		)
		self._rename_preview.setWordWrap(True)
		rename_layout.addRow("Preview:", self._rename_preview)
		# connect signals to update preview on changes
		self._path_template_edit.textChanged.connect(
			self._update_rename_preview
		)
		self._file_template_edit.textChanged.connect(
			self._update_rename_preview
		)
		self._spaces_check.stateChanged.connect(
			self._update_rename_preview
		)
		self._separator_combo.currentIndexChanged.connect(
			self._update_rename_preview
		)
		self._res_check.stateChanged.connect(
			self._update_rename_preview
		)
		self._vcodec_check.stateChanged.connect(
			self._update_rename_preview
		)
		self._acodec_check.stateChanged.connect(
			self._update_rename_preview
		)
		self._channels_check.stateChanged.connect(
			self._update_rename_preview
		)
		tabs.addTab(rename_widget, "Renamer")
		# Downloads tab (artwork + trailer + subtitles)
		downloads_widget = PySide6.QtWidgets.QWidget()
		downloads_layout = PySide6.QtWidgets.QVBoxLayout(
			downloads_widget
		)
		# artwork section
		artwork_label = PySide6.QtWidgets.QLabel("Artwork")
		artwork_label_font = artwork_label.font()
		artwork_label_font.setBold(True)
		artwork_label.setFont(artwork_label_font)
		downloads_layout.addWidget(artwork_label)
		self._poster_check = PySide6.QtWidgets.QCheckBox(
			"Download Poster"
		)
		downloads_layout.addWidget(self._poster_check)
		self._fanart_check = PySide6.QtWidgets.QCheckBox(
			"Download Fanart"
		)
		downloads_layout.addWidget(self._fanart_check)
		self._banner_check = PySide6.QtWidgets.QCheckBox(
			"Download Banner"
		)
		downloads_layout.addWidget(self._banner_check)
		self._clearart_check = PySide6.QtWidgets.QCheckBox(
			"Download Clearart"
		)
		downloads_layout.addWidget(self._clearart_check)
		self._logo_check = PySide6.QtWidgets.QCheckBox(
			"Download Logo"
		)
		downloads_layout.addWidget(self._logo_check)
		self._discart_check = PySide6.QtWidgets.QCheckBox(
			"Download Disc Art"
		)
		downloads_layout.addWidget(self._discart_check)
		# trailer/subtitle section
		media_label = PySide6.QtWidgets.QLabel("Media")
		media_label_font = media_label.font()
		media_label_font.setBold(True)
		media_label.setFont(media_label_font)
		downloads_layout.addWidget(media_label)
		self._trailer_check = PySide6.QtWidgets.QCheckBox(
			"Download Trailer"
		)
		downloads_layout.addWidget(self._trailer_check)
		self._subtitles_check = PySide6.QtWidgets.QCheckBox(
			"Download Subtitles"
		)
		downloads_layout.addWidget(self._subtitles_check)
		# subtitle languages field
		sub_lang_layout = PySide6.QtWidgets.QHBoxLayout()
		sub_lang_label = PySide6.QtWidgets.QLabel(
			"Subtitle Languages:"
		)
		sub_lang_layout.addWidget(sub_lang_label)
		self._sub_lang_edit = PySide6.QtWidgets.QLineEdit()
		self._sub_lang_edit.setMaximumWidth(120)
		self._sub_lang_edit.setPlaceholderText("en")
		sub_lang_layout.addWidget(self._sub_lang_edit)
		sub_lang_layout.addStretch()
		downloads_layout.addLayout(sub_lang_layout)
		downloads_layout.addStretch()
		tabs.addTab(downloads_widget, "Downloads")
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
		# provider combo
		provider_index = self._provider_combo.findData(
			s.scraper_provider
		)
		if provider_index >= 0:
			self._provider_combo.setCurrentIndex(provider_index)
		self._tmdb_key_edit.setText(s.tmdb_api_key)
		self._imdb_cookies_enabled_check.setChecked(
			bool(s.imdb_browser_cookies_enabled)
		)
		browser = s.imdb_browser_cookies_browser.strip().lower()
		if not browser:
			browser = "firefox"
		browser_index = self._imdb_browser_combo.findData(browser)
		if browser_index < 0:
			self._imdb_browser_combo.addItem(browser, browser)
			browser_index = self._imdb_browser_combo.findData(browser)
		if browser_index >= 0:
			self._imdb_browser_combo.setCurrentIndex(browser_index)
		self._fanart_key_edit.setText(s.fanart_api_key)
		self._osub_key_edit.setText(s.opensubtitles_api_key)
		# theme combo
		theme_index = self._theme_combo.findData(s.theme)
		if theme_index >= 0:
			self._theme_combo.setCurrentIndex(theme_index)
		self._language_edit.setText(s.scrape_language)
		self._country_edit.setText(s.scrape_country)
		self._cert_country_edit.setText(s.certification_country)
		self._path_template_edit.setText(s.path_template)
		self._file_template_edit.setText(s.file_template)
		self._spaces_check.setChecked(s.spaces_to_underscores)
		# separator combo
		sep_index = self._separator_combo.findData(s.media_separator)
		if sep_index >= 0:
			self._separator_combo.setCurrentIndex(sep_index)
		# media token checkboxes
		self._res_check.setChecked(s.rename_resolution)
		self._vcodec_check.setChecked(s.rename_vcodec)
		self._acodec_check.setChecked(s.rename_acodec)
		self._channels_check.setChecked(s.rename_channels)
		# show initial preview
		self._update_rename_preview()
		self._poster_check.setChecked(s.download_poster)
		self._fanart_check.setChecked(s.download_fanart)
		self._banner_check.setChecked(s.download_banner)
		self._clearart_check.setChecked(s.download_clearart)
		self._logo_check.setChecked(s.download_logo)
		self._discart_check.setChecked(s.download_discart)
		self._trailer_check.setChecked(s.download_trailer)
		self._subtitles_check.setChecked(s.download_subtitles)
		self._sub_lang_edit.setText(s.subtitle_languages)

	#============================================
	def _save(self):
		"""Save form values to settings and write config."""
		s = self._settings
		s.scraper_provider = self._provider_combo.currentData()
		s.tmdb_api_key = self._tmdb_key_edit.text()
		s.imdb_browser_cookies_enabled = (
			self._imdb_cookies_enabled_check.isChecked()
		)
		selected_browser = str(
			self._imdb_browser_combo.currentData() or "firefox"
		).strip().lower()
		if not selected_browser:
			selected_browser = "firefox"
		s.imdb_browser_cookies_browser = selected_browser
		s.fanart_api_key = self._fanart_key_edit.text()
		s.opensubtitles_api_key = self._osub_key_edit.text()
		s.theme = self._theme_combo.currentData()
		s.scrape_language = self._language_edit.text()
		s.scrape_country = self._country_edit.text()
		s.certification_country = self._cert_country_edit.text()
		s.path_template = self._path_template_edit.text()
		s.file_template = self._file_template_edit.text()
		s.spaces_to_underscores = self._spaces_check.isChecked()
		s.media_separator = self._separator_combo.currentData()
		s.rename_resolution = self._res_check.isChecked()
		s.rename_vcodec = self._vcodec_check.isChecked()
		s.rename_acodec = self._acodec_check.isChecked()
		s.rename_channels = self._channels_check.isChecked()
		s.download_poster = self._poster_check.isChecked()
		s.download_fanart = self._fanart_check.isChecked()
		s.download_banner = self._banner_check.isChecked()
		s.download_clearart = self._clearart_check.isChecked()
		s.download_logo = self._logo_check.isChecked()
		s.download_discart = self._discart_check.isChecked()
		s.download_trailer = self._trailer_check.isChecked()
		s.download_subtitles = self._subtitles_check.isChecked()
		s.subtitle_languages = self._sub_lang_edit.text()
		# write to disk
		moviemanager.core.settings.save_settings(s)
		self.accept()

	#============================================
	def _update_rename_preview(self) -> None:
		"""Update the live preview label with example folder and file name."""
		path_tmpl = self._path_template_edit.text()
		file_tmpl = self._file_template_edit.text()
		if not path_tmpl and not file_tmpl:
			self._rename_preview.setText("")
			return

		# example token values for preview
		example_tokens = {
			"{title}": "The Matrix",
			"{year}": "1999",
			"{rating}": "8.7",
			"{certification}": "R",
			"{genre}": "Action",
			"{director}": "Wachowski",
		}
		# media token example values
		media_examples = {
			"{resolution}": "1080p",
			"{vcodec}": "h264",
			"{codec}": "h264",
			"{acodec}": "aac",
			"{audio}": "aac",
			"{channels}": "5.1",
		}

		# build the file portion with appended media tokens
		sep = self._separator_combo.currentData() or "-"
		file_part = file_tmpl
		token_list = []
		if self._res_check.isChecked():
			token_list.append("{resolution}")
		if self._vcodec_check.isChecked():
			token_list.append("{vcodec}")
		if self._acodec_check.isChecked():
			token_list.append("{acodec}")
		if self._channels_check.isChecked():
			token_list.append("{channels}")
		if token_list:
			suffix = sep.join(token_list)
			file_part = file_part + sep + suffix

		# substitute example values into path and file templates
		path_example = path_tmpl
		file_example = file_part
		all_tokens = {}
		all_tokens.update(example_tokens)
		all_tokens.update(media_examples)
		for token, value in all_tokens.items():
			path_example = path_example.replace(token, value)
			file_example = file_example.replace(token, value)

		# apply shell-safe filename cleaning if checked
		if self._spaces_check.isChecked():
			path_example = moviemanager.core.utils.shell_safe_filename(
				path_example
			)
			file_example = moviemanager.core.utils.shell_safe_filename(
				file_example
			)

		preview_text = f"Example: {path_example}/{file_example}.mkv"
		self._rename_preview.setText(preview_text)

	#============================================
	def get_settings(self):
		"""Return the settings object.

		Returns:
			The Settings instance with updated values.
		"""
		return self._settings
