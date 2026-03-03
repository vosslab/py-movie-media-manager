"""Non-modal dialog showing running and completed background jobs."""

# Standard Library
import re
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
		self.resize(560, 300)
		# non-modal so user can interact with main window
		self.setModal(False)
		self._setup_ui()
		# connect to job list updates
		self._task_api.job_list_changed.connect(self._refresh)
		# periodic timer keeps elapsed-time column fresh while visible
		self._tick_timer = PySide6.QtCore.QTimer(self)
		self._tick_timer.setInterval(2400)
		self._tick_timer.timeout.connect(self._refresh)
		self._tick_timer.start()
		# populate initial state
		self._refresh()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the dialog layout with jobs table and action buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# jobs table: Name, Priority, Status, Progress, Queued, Active
		self._table = PySide6.QtWidgets.QTableWidget()
		self._table.setColumnCount(6)
		self._table.setHorizontalHeaderLabels(
			["Name", "Priority", "Status", "Progress", "Queued", "Active"]
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
		# error summary button
		self._summary_btn = PySide6.QtWidgets.QPushButton(
			"Error Summary"
		)
		self._summary_btn.clicked.connect(self._show_error_summary)
		btn_layout.addWidget(self._summary_btn)
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
			# priority column
			pri = job.get("priority", 50)
			pri_text = self._format_priority(pri)
			pri_item = PySide6.QtWidgets.QTableWidgetItem(pri_text)
			self._table.setItem(row, 1, pri_item)
			# status column
			status = job["status"]
			if status == "queued":
				status_text = "Queued"
			elif status == "running":
				status_text = "Running..."
			elif status == "done":
				status_text = "Done"
			else:
				# show category label when available, else truncated traceback
				error_cat = job.get("error_category", "")
				if error_cat:
					# title-case the category name (e.g. no_url -> No Url)
					cat_label = error_cat.replace("_", " ").title()
					status_text = f"Error: {cat_label}"
				else:
					err = job.get("error_text", "")
					short_err = err.split("\n")[-1][:120] if err else ""
					status_text = f"Error: {short_err}"
			status_item = PySide6.QtWidgets.QTableWidgetItem(
				status_text
			)
			# add tooltip with full error text for error jobs
			if status == "error" and job.get("error_text"):
				status_item.setToolTip(job["error_text"])
			self._table.setItem(row, 2, status_item)
			# progress column (e.g. "3/42" or "3/42 (2 failed)")
			progress_text = self._format_progress(job.get("progress"))
			progress_item = PySide6.QtWidgets.QTableWidgetItem(
				progress_text
			)
			self._table.setItem(row, 3, progress_item)
			# queued time column (time since submitted)
			queued_elapsed = now - job["submitted_at"]
			queued_text = self._format_elapsed(queued_elapsed)
			queued_item = PySide6.QtWidgets.QTableWidgetItem(
				queued_text
			)
			self._table.setItem(row, 4, queued_item)
			# active time column (time since worker started running)
			started_at = job.get("started_at")
			if started_at:
				active_elapsed = now - started_at
				active_text = self._format_elapsed(active_elapsed)
			else:
				active_text = "--"
			active_item = PySide6.QtWidgets.QTableWidgetItem(
				active_text
			)
			self._table.setItem(row, 5, active_item)
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
	@staticmethod
	def _format_priority(priority: int) -> str:
		"""Format a numeric priority as a human-readable label.

		Args:
			priority: Integer priority value.

		Returns:
			Label such as "Critical", "High", "Normal", "Low", or "Background".
		"""
		if priority >= 100:
			text = "Critical"
		elif priority >= 75:
			text = "High"
		elif priority >= 50:
			text = "Normal"
		elif priority >= 25:
			text = "Low"
		else:
			text = "Background"
		return text

	#============================================
	@staticmethod
	def _format_progress(progress: tuple) -> str:
		"""Format a progress tuple as a short display string.

		Args:
			progress: (current, total, message) tuple or None.

		Returns:
			String like "3/42", "3/42 (2 failed)", or "--".
		"""
		if progress is None:
			return "--"
		current, total, message = progress
		if total <= 0:
			return "--"
		# extract failure count from message if present
		# message format: "... - 1 fetched, 2 failed"
		text = f"{current}/{total}"
		# look for "N failed" in the progress message
		fail_match = re.search(r"(\d+)\s+failed", message)
		if fail_match:
			fail_count = int(fail_match.group(1))
			if fail_count > 0:
				text += f" ({fail_count} failed)"
		return text

	#============================================
	def showEvent(self, event) -> None:
		"""Start the refresh timer when the dialog becomes visible."""
		super().showEvent(event)
		self._tick_timer.start()

	#============================================
	def hideEvent(self, event) -> None:
		"""Stop the refresh timer when the dialog is hidden."""
		self._tick_timer.stop()
		super().hideEvent(event)

	#============================================
	def closeEvent(self, event) -> None:
		"""Stop the refresh timer when the dialog is closed."""
		self._tick_timer.stop()
		super().closeEvent(event)

	#============================================
	def _clear_completed(self) -> None:
		"""Remove all finished jobs from the list."""
		self._task_api.clear_completed()

	#============================================
	def _show_error_summary(self) -> None:
		"""Show a message box with error counts grouped by category."""
		jobs = self._task_api.all_jobs
		# count errors by category
		counts = {}
		for job in jobs:
			if job["status"] != "error":
				continue
			cat = job.get("error_category", "") or "uncategorized"
			cat_label = cat.replace("_", " ").title()
			counts[cat_label] = counts.get(cat_label, 0) + 1
		total = sum(counts.values())
		if total == 0:
			PySide6.QtWidgets.QMessageBox.information(
				self, "Error Summary", "No errors recorded."
			)
			return
		# build summary text sorted by count descending
		lines = [f"Total errors: {total}\n"]
		sorted_cats = sorted(
			counts.items(), key=lambda kv: kv[1], reverse=True,
		)
		for cat_label, count in sorted_cats:
			lines.append(f"  {cat_label}: {count}")
		summary = "\n".join(lines)
		PySide6.QtWidgets.QMessageBox.information(
			self, "Error Summary", summary,
		)

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
