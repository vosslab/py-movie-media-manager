"""Search/filter text input widget."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore


#============================================
class SearchField(PySide6.QtWidgets.QLineEdit):
	"""Text input for filtering movie list."""

	# signal emitted when filter text changes (debounced)
	filter_changed = PySide6.QtCore.Signal(str)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setPlaceholderText("Filter movies...")
		self.setClearButtonEnabled(True)
		# debounce timer
		self._timer = PySide6.QtCore.QTimer(self)
		self._timer.setSingleShot(True)
		self._timer.setInterval(300)
		self._timer.timeout.connect(self._emit_filter)
		self.textChanged.connect(self._on_text_changed)

	#============================================
	def _on_text_changed(self, text: str) -> None:
		"""Restart debounce timer on text change."""
		self._timer.start()

	#============================================
	def _emit_filter(self) -> None:
		"""Emit the filter_changed signal with current text."""
		self.filter_changed.emit(self.text())
