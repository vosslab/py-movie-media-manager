"""Status bar widget for task progress."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore


#============================================
class StatusBar(PySide6.QtWidgets.QStatusBar):
	"""Status bar showing task progress and movie counts."""

	# emitted when the user clicks the Cancel button
	cancel_requested = PySide6.QtCore.Signal()

	def __init__(self, parent=None):
		super().__init__(parent)
		# movie count label
		self._count_label = PySide6.QtWidgets.QLabel("No movies loaded")
		self.addPermanentWidget(self._count_label)
		# cancel button (hidden by default)
		self._cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		self._cancel_btn.setMaximumWidth(80)
		self._cancel_btn.hide()
		self._cancel_btn.clicked.connect(self.cancel_requested.emit)
		self.addWidget(self._cancel_btn)
		# progress bar (hidden by default)
		self._progress = PySide6.QtWidgets.QProgressBar()
		self._progress.setMaximumWidth(200)
		self._progress.hide()
		self.addWidget(self._progress)

	#============================================
	def set_movie_count(self, total: int, scraped: int) -> None:
		"""Update movie count display."""
		text = f"{total} movies ({scraped} scraped)"
		self._count_label.setText(text)

	#============================================
	def set_checked_count(self, checked: int, total: int) -> None:
		"""Update count display to include checked count."""
		text = f"{checked} checked, {total} total"
		self._count_label.setText(text)

	#============================================
	def show_progress(self, current: int, total: int, message: str = "") -> None:
		"""Show progress bar with current/total."""
		self._progress.show()
		self._cancel_btn.show()
		self._progress.setMaximum(total)
		self._progress.setValue(current)
		if message:
			self.showMessage(message)

	#============================================
	def hide_progress(self) -> None:
		"""Hide the progress bar and cancel button."""
		self._progress.hide()
		self._cancel_btn.hide()
		self.clearMessage()
