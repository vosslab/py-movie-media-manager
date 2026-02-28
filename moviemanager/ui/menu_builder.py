"""Build menus and shortcuts from a YAML configuration file."""

# Standard Library
import os

# PIP3 modules
import yaml
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
def build_menus(window, config_path: str = "") -> dict:
	"""Build menus and shortcuts from YAML config on a QMainWindow.

	Args:
		window: QMainWindow instance with action handler methods.
		config_path: Path to menu_config.yaml. If empty, uses the
			default file next to this module.

	Returns:
		dict: Mapping of store_as names to QAction instances.
	"""
	if not config_path:
		config_path = os.path.join(
			os.path.dirname(__file__), "menu_config.yaml"
		)
	with open(config_path, "r") as f:
		config = yaml.safe_load(f)
	action_map = _build_action_map(window)
	stored = {}
	menu_bar = window.menuBar()
	# build menus
	for menu_def in config.get("menus", []):
		menu = menu_bar.addMenu(menu_def["label"])
		for item in menu_def.get("items", []):
			if item.get("separator"):
				menu.addSeparator()
				continue
			action = PySide6.QtGui.QAction(item["label"], window)
			if "shortcut" in item:
				action.setShortcut(item["shortcut"])
			if not item.get("enabled", True):
				action.setEnabled(False)
			if item.get("checkable", False):
				action.setCheckable(True)
			# connect to the window method
			action_name = item.get("action", "")
			handler = action_map.get(action_name)
			if handler:
				action.triggered.connect(handler)
			menu.addAction(action)
			# store reference if requested
			store_name = item.get("store_as", "")
			if store_name:
				stored[store_name] = action
	# build standalone keyboard shortcuts
	for shortcut_def in config.get("shortcuts", []):
		key_seq = shortcut_def["key"]
		action_name = shortcut_def["action"]
		handler = action_map.get(action_name)
		if handler:
			shortcut = PySide6.QtGui.QShortcut(
				PySide6.QtGui.QKeySequence(key_seq), window
			)
			shortcut.activated.connect(handler)
	return stored


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
		"show_settings": window._show_settings,
		"quit": window.close,
		"undo_last_rename": window._undo_last_rename,
		"scrape_selected": window._scrape_selected,
		"edit_selected": window._edit_selected,
		"rename_selected": window._rename_selected,
		"select_all": window._select_all,
		"select_none": window._select_none,
		"select_unscraped": window._select_unscraped,
		"batch_scrape_unscraped": window._batch_scrape_unscraped,
		"toggle_dark_mode": window._toggle_dark_mode,
		"show_about": window._show_about,
		"focus_search": window._focus_search,
		"on_escape": window._on_escape,
		"rescan": window._rescan,
		"download_trailer": window._download_trailer,
		"download_subtitles": window._download_subtitles,
	}
	return action_map
