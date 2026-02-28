"""Dark and light theme palettes for the application."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import PySide6.QtCore


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
	elif theme_name == "light":
		palette = app.style().standardPalette()
		app.setPalette(palette)
	else:
		# system default
		palette = app.style().standardPalette()
		app.setPalette(palette)


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
		PySide6.QtCore.Qt.GlobalColor.white
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
