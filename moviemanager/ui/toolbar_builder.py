"""Build the main toolbar for the application window."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
def build_toolbar(window) -> dict:
	"""Build the main toolbar with labeled icons in 3-step workflow order.

	Layout: Open | sep | 1. Match | 2. Organize | 3. Download
	| spacer | Refresh Metadata | Parental Guide | Refresh Stats
	| sep | Settings | Dark Mode | Quit

	Args:
		window: QMainWindow instance with action handler methods.

	Returns:
		dict: Mapping of widget names to QAction instances for
			buttons that need external references (match_btn,
			organize_btn, download_btn, dark_toggle).
	"""
	action_map = _build_action_map(window)
	toolbar = window.addToolBar("Main")
	toolbar.setObjectName("MainToolBar")
	toolbar.setMovable(False)
	toolbar.setToolButtonStyle(
		PySide6.QtCore.Qt.ToolButtonStyle
		.ToolButtonTextUnderIcon
	)
	toolbar.setIconSize(PySide6.QtCore.QSize(32, 32))
	style = window.style()
	stored = {}
	# open button
	open_btn = _make_action(
		window, toolbar, "Open",
		"folder-open",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_DirOpenIcon,
		"Open a movie directory (Ctrl+O)",
	)
	open_btn.triggered.connect(action_map["open_directory"])
	toolbar.addSeparator()
	# step 1: match button
	match_btn = _make_action(
		window, toolbar, "1. Match",
		"edit-find",
		PySide6.QtWidgets.QStyle.StandardPixmap
		.SP_FileDialogContentsView,
		"Match movies to IMDB/TMDB (Ctrl+Shift+S)",
	)
	match_btn.triggered.connect(action_map["scrape_selected"])
	stored["match_btn"] = match_btn
	# step 2: organize button
	organize_btn = _make_action(
		window, toolbar, "2. Organize",
		"folder-new",
		PySide6.QtWidgets.QStyle.StandardPixmap
		.SP_FileDialogNewFolder,
		"Organize movies into folders (F2)",
	)
	organize_btn.triggered.connect(
		action_map["rename_selected"]
	)
	stored["organize_btn"] = organize_btn
	# step 3: download button
	download_btn = _make_action(
		window, toolbar, "3. Download",
		"go-down",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_ArrowDown,
		"Download artwork, trailers, and subtitles",
	)
	download_btn.triggered.connect(
		action_map["download_content"]
	)
	stored["download_btn"] = download_btn
	toolbar.addSeparator()
	# flexible spacer
	spacer = PySide6.QtWidgets.QWidget()
	spacer.setSizePolicy(
		PySide6.QtWidgets.QSizePolicy.Policy.Expanding,
		PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
	)
	toolbar.addWidget(spacer)
	toolbar.addSeparator()
	# refresh metadata button
	refresh_meta_btn = _make_action(
		window, toolbar, "Refresh Metadata",
		"view-refresh",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_BrowserReload,
		"Re-fetch metadata for matched movies"
		" from IMDB/TMDB",
	)
	refresh_meta_btn.triggered.connect(
		action_map["refresh_metadata"]
	)
	# parental guide button
	pg_btn = _make_action(
		window, toolbar, "Parental Guide",
		"security-medium",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_MessageBoxWarning,
		"Fetch parental guide data from IMDB"
		" for matched movies",
	)
	pg_btn.triggered.connect(
		action_map["fetch_parental_guides"]
	)
	# refresh file stats button
	refresh_stats_btn = _make_action(
		window, toolbar, "Refresh Stats",
		"document-properties",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_FileIcon,
		"Re-probe video files for codec,"
		" resolution, and duration",
	)
	refresh_stats_btn.triggered.connect(
		action_map["refresh_file_stats"]
	)
	toolbar.addSeparator()
	# settings button
	settings_btn = _make_action(
		window, toolbar, "Settings",
		"preferences-system",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_ComputerIcon,
		"Open settings (Ctrl+,)",
	)
	settings_btn.triggered.connect(
		action_map["show_settings"]
	)
	# dark mode toggle
	dark_toggle = PySide6.QtGui.QAction(
		"Dark Mode", window
	)
	dark_toggle.setCheckable(True)
	is_dark = (
		hasattr(window, "_settings")
		and window._settings.theme == "dark"
	)
	dark_toggle.setChecked(is_dark)
	dark_icon = PySide6.QtGui.QIcon.fromTheme(
		"weather-clear-night",
		style.standardIcon(
			PySide6.QtWidgets.QStyle
			.StandardPixmap.SP_DesktopIcon
		),
	)
	dark_toggle.setIcon(dark_icon)
	dark_toggle.setToolTip(
		"Toggle dark/light theme"
	)
	dark_toggle.triggered.connect(
		action_map["toggle_dark_mode"]
	)
	toolbar.addAction(dark_toggle)
	stored["dark_toggle"] = dark_toggle
	# quit button
	quit_btn = _make_action(
		window, toolbar, "Quit",
		"application-exit",
		PySide6.QtWidgets.QStyle
		.StandardPixmap.SP_DialogCloseButton,
		"Quit application (Ctrl+Q)",
	)
	quit_btn.triggered.connect(action_map["quit"])
	return stored


#============================================
def _make_action(
	window, toolbar, label: str,
	theme_name: str, fallback_pixmap,
	tooltip: str,
) -> PySide6.QtGui.QAction:
	"""Create a toolbar action with themed icon and fallback.

	Args:
		window: Parent QMainWindow for the action.
		toolbar: QToolBar to add the action to.
		label: Button label text.
		theme_name: Icon theme name string.
		fallback_pixmap: QStyle.StandardPixmap fallback.
		tooltip: Tooltip text for the button.

	Returns:
		QAction: The created and added toolbar action.
	"""
	action = PySide6.QtGui.QAction(label, window)
	icon = PySide6.QtGui.QIcon.fromTheme(
		theme_name,
		window.style().standardIcon(fallback_pixmap),
	)
	action.setIcon(icon)
	action.setToolTip(tooltip)
	toolbar.addAction(action)
	return action


#============================================
def _build_action_map(window) -> dict:
	"""Build mapping from action names to window methods.

	Args:
		window: QMainWindow instance with handler methods.

	Returns:
		dict: Mapping of action name strings to callable methods.
	"""
	action_map = {
		"open_directory": window._open_directory,
		"scrape_selected": window._scrape_selected,
		"rename_selected": window._rename_selected,
		"download_content": window._download_content,
		"refresh_metadata": window._refresh_metadata,
		"fetch_parental_guides": window._fetch_parental_guides,
		"refresh_file_stats": window._refresh_file_stats,
		"show_settings": window._show_settings,
		"toggle_dark_mode": window._toggle_dark_mode,
		"quit": window.close,
	}
	return action_map
