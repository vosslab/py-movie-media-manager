"""Dark and light theme palettes for the application."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import PySide6.QtCore


# minimal QSS for dark theme polish
_DARK_STYLESHEET = """
/* table header styling */
QHeaderView::section {
	background-color: #3a3a3a;
	color: #ffffff;
	padding: 4px 6px;
	border: 1px solid #2a2a2a;
	font-weight: bold;
}

/* toolbar styling */
QToolBar {
	background-color: #353535;
	border-bottom: 1px solid #2a2a2a;
	spacing: 4px;
	padding: 2px;
}
QToolButton {
	color: #ffffff;
	padding: 4px;
	border-radius: 4px;
}
QToolButton:hover {
	background-color: #4a4a4a;
}
QToolButton:pressed {
	background-color: #555555;
}

/* scrollbar styling */
QScrollBar:vertical {
	background: #2a2a2a;
	width: 12px;
	border: none;
}
QScrollBar::handle:vertical {
	background: #555555;
	min-height: 20px;
	border-radius: 4px;
	margin: 2px;
}
QScrollBar::handle:vertical:hover {
	background: #666666;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
	height: 0px;
}
QScrollBar:horizontal {
	background: #2a2a2a;
	height: 12px;
	border: none;
}
QScrollBar::handle:horizontal {
	background: #555555;
	min-width: 20px;
	border-radius: 4px;
	margin: 2px;
}
QScrollBar::handle:horizontal:hover {
	background: #666666;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
	width: 0px;
}

/* button styling */
QPushButton {
	background-color: #3a3a3a;
	color: #ffffff;
	border: 1px solid #555555;
	border-radius: 4px;
	padding: 4px 12px;
}
QPushButton:hover {
	background-color: #4a4a4a;
	border-color: #666666;
}
QPushButton:pressed {
	background-color: #555555;
}
QPushButton:disabled {
	color: #777777;
	background-color: #333333;
}

/* tab bar styling */
QTabBar::tab {
	background-color: #353535;
	color: #cccccc;
	padding: 6px 12px;
	border: 1px solid #2a2a2a;
	border-bottom: none;
}
QTabBar::tab:selected {
	background-color: #3a3a3a;
	color: #ffffff;
	border-bottom: 2px solid #2a82da;
}
QTabBar::tab:hover {
	background-color: #404040;
}

/* status bar */
QStatusBar {
	background-color: #2d2d2d;
	border-top: 1px solid #3a3a3a;
}

/* progress bar */
QProgressBar {
	background-color: #2a2a2a;
	border: 1px solid #3a3a3a;
	border-radius: 3px;
	text-align: center;
	color: #ffffff;
}
QProgressBar::chunk {
	background-color: #2a82da;
	border-radius: 2px;
}

/* group box */
QGroupBox {
	border: 1px solid #3a3a3a;
	border-radius: 4px;
	margin-top: 8px;
	padding-top: 8px;
}
QGroupBox::title {
	color: #cccccc;
	subcontrol-origin: margin;
	padding: 0 4px;
}

/* checkbox */
QCheckBox {
	spacing: 6px;
}
QCheckBox::indicator {
	width: 14px;
	height: 14px;
	border: 1px solid #555555;
	border-radius: 2px;
	background-color: #2a2a2a;
}
QCheckBox::indicator:checked {
	background-color: #2a82da;
	border-color: #2a82da;
}
"""


#============================================
def apply_theme(app, theme_name: str) -> None:
	"""Apply a color theme to the application.

	Args:
		app: QApplication instance.
		theme_name: One of "system", "dark", or "light".
	"""
	if theme_name == "dark":
		palette = _build_dark_palette()
		app.setPalette(palette)
		app.setStyleSheet(_DARK_STYLESHEET)
	elif theme_name == "light":
		palette = app.style().standardPalette()
		app.setPalette(palette)
		app.setStyleSheet("")
	else:
		# system default
		palette = app.style().standardPalette()
		app.setPalette(palette)
		app.setStyleSheet("")


#============================================
def _build_dark_palette() -> PySide6.QtGui.QPalette:
	"""Build a dark color palette.

	Returns:
		QPalette configured with dark theme colors.
	"""
	palette = PySide6.QtGui.QPalette()
	# window and base colors
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.Window,
		PySide6.QtGui.QColor(53, 53, 53)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.WindowText,
		PySide6.QtCore.Qt.GlobalColor.white
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.Base,
		PySide6.QtGui.QColor(25, 25, 25)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.AlternateBase,
		PySide6.QtGui.QColor(53, 53, 53)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.ToolTipBase,
		PySide6.QtGui.QColor(53, 53, 53)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.ToolTipText,
		PySide6.QtCore.Qt.GlobalColor.white
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.Text,
		PySide6.QtCore.Qt.GlobalColor.white
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.Button,
		PySide6.QtGui.QColor(53, 53, 53)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.ButtonText,
		PySide6.QtCore.Qt.GlobalColor.white
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.BrightText,
		PySide6.QtCore.Qt.GlobalColor.red
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.Link,
		PySide6.QtGui.QColor(42, 130, 218)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.Highlight,
		PySide6.QtGui.QColor(42, 130, 218)
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.HighlightedText,
		PySide6.QtCore.Qt.GlobalColor.black
	)
	palette.setColor(
		PySide6.QtGui.QPalette.ColorRole.PlaceholderText,
		PySide6.QtGui.QColor(127, 127, 127)
	)
	return palette
