"""Non-modal dialog showing running and completed background jobs."""

# Standard Library
import time

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets


#============================================
class JobsDialog(PySide6.QtWidgets.QDialog):
	"""Popup listing all background jobs with status and elapsed time.

	Shows a table of running and recently completed jobs. Non-modal
	so it does not block the main window. Refreshes automatically
	when the TaskAPI emits job_list_changed.
	"""

	def __init__(self, task_api, parent=None):
		"""Initialize the jobs dialog.

		Args:
			task_api: TaskAPI instance providing job metadata.
			parent: Parent widget.
		"""
		super().__init__(parent)
		self._task_api = task_api
		self.setWindowTitle("Background Jobs")
		self.resize(480, 300)
		# non-modal so user can interact with main window
		self.setModal(False)
		self._setup_ui()
		# connect to job list updates
		self._task_api.job_list_changed.connect(self._refresh)
		# populate initial state
		self._refresh()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the dialog layout with jobs table and action buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# jobs table with 3 columns: Name, Status, Time
		self._table = PySide6.QtWidgets.QTableWidget()
		self._table.setColumnCount(3)
		self._table.setHorizontalHeaderLabels(
			["Name", "Status", "Time"]
		)
		self._table.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionBehavior.SelectRows
		)
		self._table.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView
			.EditTrigger.NoEditTriggers
		)
		self._table.horizontalHeader().setStretchLastSection(True)
		# stretch the Name column to fill available space
		self._table.horizontalHeader().setSectionResizeMode(
			0,
			PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch,
		)
		layout.addWidget(self._table)
		# button row
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		# clear completed button
		self._clear_btn = PySide6.QtWidgets.QPushButton(
			"Clear Completed"
		)
		self._clear_btn.clicked.connect(self._clear_completed)
		btn_layout.addWidget(self._clear_btn)
		# close button
		close_btn = PySide6.QtWidgets.QPushButton("Close")
		close_btn.clicked.connect(self.close)
		btn_layout.addWidget(close_btn)
		layout.addLayout(btn_layout)

	#============================================
	def _refresh(self) -> None:
		"""Refresh the jobs table from TaskAPI metadata."""
		jobs = self._task_api.all_jobs
		self._table.setRowCount(len(jobs))
		now = time.time()
		for row, job in enumerate(jobs):
			# name column
			name_item = PySide6.QtWidgets.QTableWidgetItem(
				job["name"]
			)
			self._table.setItem(row, 0, name_item)
			# status column
			status = job["status"]
			if status == "running":
				status_text = "Running..."
			elif status == "done":
				status_text = "Done"
			else:
				# truncate error text for table display
				err = job.get("error_text", "")
				short_err = err.split("\n")[-1][:60] if err else ""
				status_text = f"Error: {short_err}"
			status_item = PySide6.QtWidgets.QTableWidgetItem(
				status_text
			)
			self._table.setItem(row, 1, status_item)
			# elapsed time column
			elapsed = now - job["submitted_at"]
			time_text = self._format_elapsed(elapsed)
			time_item = PySide6.QtWidgets.QTableWidgetItem(time_text)
			self._table.setItem(row, 2, time_item)
		self._table.resizeColumnsToContents()
		# re-stretch Name column after resize
		self._table.horizontalHeader().setSectionResizeMode(
			0,
			PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch,
		)

	#============================================
	@staticmethod
	def _format_elapsed(seconds: float) -> str:
		"""Format elapsed seconds as a human-readable string.

		Args:
			seconds: Elapsed time in seconds.

		Returns:
			Formatted string like "3s", "1m 12s", or "5m 0s".
		"""
		total_secs = int(seconds)
		if total_secs < 60:
			text = f"{total_secs}s"
		else:
			mins = total_secs // 60
			secs = total_secs % 60
			text = f"{mins}m {secs}s"
		return text

	#============================================
	def _clear_completed(self) -> None:
		"""Remove all finished jobs from the list."""
		self._task_api.clear_completed()

	#============================================
	def _cancel_selected(self) -> None:
		"""Cancel the selected running job."""
		row = self._table.currentRow()
		jobs = self._task_api.all_jobs
		if row < 0 or row >= len(jobs):
			return
		job = jobs[row]
		if job["status"] == "running":
			self._task_api.cancel(job["task_id"])
