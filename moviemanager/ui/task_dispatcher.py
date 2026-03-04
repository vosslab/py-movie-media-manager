"""Central dispatcher that routes TaskAPI signals to controllers."""

# PIP3 modules
import PySide6.QtCore


#============================================
class TaskDispatcher(PySide6.QtCore.QObject):
	"""Routes task_finished/error/progress signals to the correct controller.

	Holds references to all four controllers and the status bar,
	then dispatches incoming TaskAPI signals by matching task_id
	to each controller's active task IDs.

	Args:
		scan_ctrl: ScanController instance.
		match_ctrl: MatchController instance.
		rename_ctrl: RenameController instance.
		download_ctrl: DownloadController instance.
		status_bar: StatusBar widget for progress display.
		parent: Parent QObject.
	"""

	def __init__(
		self, scan_ctrl, match_ctrl, rename_ctrl,
		download_ctrl, status_bar, parent=None,
	):
		super().__init__(parent)
		self._scan_ctrl = scan_ctrl
		self._match_ctrl = match_ctrl
		self._rename_ctrl = rename_ctrl
		self._download_ctrl = download_ctrl
		self._status = status_bar

	#============================================
	def on_task_finished(
		self, task_id: int, result,
	) -> None:
		"""Route task completion to the appropriate handler.

		Args:
			task_id: ID of the completed task.
			result: Result object from the worker.
		"""
		scan_ctrl = self._scan_ctrl
		match_ctrl = self._match_ctrl
		rename_ctrl = self._rename_ctrl
		dl_ctrl = self._download_ctrl
		if task_id == scan_ctrl.scan_task_id:
			scan_ctrl.on_scan_done(result)
		elif task_id == match_ctrl.scrape_task_id:
			match_ctrl.on_batch_scrape_done(result, self.parent())
		elif task_id == match_ctrl.refresh_task_id:
			match_ctrl.on_refresh_metadata_done(
				result, self.parent()
			)
		elif task_id == match_ctrl.pg_task_id:
			match_ctrl.on_fetch_parental_guides_done(
				result, self.parent()
			)
		elif task_id == scan_ctrl.probe_task_id:
			scan_ctrl.on_probe_task_finished(task_id, result)
		elif task_id in dl_ctrl.download_task_ids:
			dl_ctrl.on_download_job_done(task_id, result)
		elif task_id == scan_ctrl.badge_task_id:
			scan_ctrl.on_badge_task_finished(task_id, result)
		elif task_id == rename_ctrl.rename_task_id:
			mode = rename_ctrl.rename_mode
			if mode == "single_preview":
				rename_ctrl.on_rename_preview_done(
					result, self.parent()
				)
			elif mode == "single_exec":
				rename_ctrl.on_rename_exec_done(result)
			elif mode == "batch_preview":
				rename_ctrl.on_batch_rename_preview_done(
					result, self.parent()
				)
			elif mode == "batch_exec":
				rename_ctrl.on_batch_rename_exec_done(
					result, self.parent()
				)

	#============================================
	def on_task_error(
		self, task_id: int, error_text: str,
	) -> None:
		"""Route task errors to the appropriate handler.

		Args:
			task_id: ID of the failed task.
			error_text: Error description or traceback.
		"""
		scan_ctrl = self._scan_ctrl
		match_ctrl = self._match_ctrl
		rename_ctrl = self._rename_ctrl
		if task_id in (
			scan_ctrl.scan_task_id,
			match_ctrl.scrape_task_id,
			match_ctrl.refresh_task_id,
			match_ctrl.pg_task_id,
		):
			scan_ctrl.on_scan_error(error_text)
		elif task_id == scan_ctrl.probe_task_id:
			scan_ctrl.on_probe_task_error(
				task_id, error_text
			)
		elif task_id == rename_ctrl.rename_task_id:
			mode = rename_ctrl.rename_mode
			if mode in ("single_preview", "batch_preview"):
				rename_ctrl.on_rename_preview_error(
					error_text
				)
			else:
				rename_ctrl.on_rename_exec_error(error_text)

	#============================================
	def on_task_progress(
		self, task_id: int, cur: int, tot: int, msg: str,
	) -> None:
		"""Route task progress to the appropriate handler.

		Args:
			task_id: ID of the reporting task.
			cur: Current progress value.
			tot: Total progress value.
			msg: Progress message string.
		"""
		scan_ctrl = self._scan_ctrl
		match_ctrl = self._match_ctrl
		if task_id in (
			scan_ctrl.scan_task_id,
			match_ctrl.scrape_task_id,
			match_ctrl.refresh_task_id,
			match_ctrl.pg_task_id,
		):
			self._status.show_progress(cur, tot, msg)
		elif task_id == scan_ctrl.probe_task_id:
			scan_ctrl.on_probe_task_progress(
				task_id, cur, tot, msg
			)
