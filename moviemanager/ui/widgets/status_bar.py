"""Status bar widget for task progress."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore


#============================================
class StatusBar(PySide6.QtWidgets.QStatusBar):
	"""Status bar showing task progress and movie counts."""

	# emitted when the user clicks the Cancel button
	cancel_requested = PySide6.QtCore.Signal()
	# emitted when the user clicks the Jobs button
	jobs_clicked = PySide6.QtCore.Signal()
	# emitted when the user toggles the Pause button (True = paused)
	pause_toggled = PySide6.QtCore.Signal(bool)

	def __init__(self, parent=None):
		super().__init__(parent)
		# jobs button (permanent widget on the right)
		self._jobs_btn = PySide6.QtWidgets.QPushButton("Jobs: 0")
		self._jobs_btn.setFlat(True)
		self._jobs_btn.setMaximumWidth(90)
		# small font, no border by default
		self._jobs_btn.setStyleSheet(
			"QPushButton { font-size: 11px; padding: 2px 6px; }"
		)
		self._jobs_btn.clicked.connect(self.jobs_clicked.emit)
		self.addPermanentWidget(self._jobs_btn)
		# pause/resume toggle button (permanent widget, next to Jobs)
		self._pause_btn = PySide6.QtWidgets.QPushButton("Pause")
		self._pause_btn.setCheckable(True)
		self._pause_btn.setFlat(True)
		self._pause_btn.setMaximumWidth(80)
		self._pause_btn.setStyleSheet(
			"QPushButton { font-size: 11px; padding: 2px 6px; }"
		)
		self._pause_btn.toggled.connect(self._on_pause_toggled)
		self.addPermanentWidget(self._pause_btn)
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
	def update_job_count(self, active: int) -> None:
		"""Update the Jobs button text and style.

		Args:
			active: Number of currently running jobs.
		"""
		self._jobs_btn.setText(f"Jobs: {active}")
		# bold text when jobs are active
		font = self._jobs_btn.font()
		font.setBold(active > 0)
		self._jobs_btn.setFont(font)

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

	#============================================
	def _on_pause_toggled(self, checked: bool) -> None:
		"""Handle pause button toggle and update button text.

		Args:
			checked: True when the button is toggled on (paused).
		"""
		if checked:
			self._pause_btn.setText("Resume")
		else:
			self._pause_btn.setText("Pause")
		self.pause_toggled.emit(checked)

	#============================================
	def set_paused(self, paused: bool) -> None:
		"""Programmatically set the pause button state.

		Args:
			paused: True to show paused state, False for normal.
		"""
		# block signals to avoid feedback loop
		self._pause_btn.blockSignals(True)
		self._pause_btn.setChecked(paused)
		if paused:
			self._pause_btn.setText("Resume")
		else:
			self._pause_btn.setText("Pause")
		self._pause_btn.blockSignals(False)
