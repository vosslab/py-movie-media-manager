"""Qt-integrated background task manager using QThreadPool."""

# Standard Library
import time
import threading

# PIP3 modules
import PySide6.QtCore

# local repo modules
import moviemanager.ui.workers


#============================================
class TaskAPI(PySide6.QtCore.QObject):
	"""Submit and track background tasks using Qt thread pool.

	Wraps QThreadPool with Worker instances to provide a task-ID-based
	interface for submitting and querying background work. Emits Qt
	signals for progress, completion, and errors so the UI can connect
	directly.

	Also provides a Calibre-style job tracking layer via submit_job()
	that stores human-readable job names and statuses for display in
	a status bar indicator and jobs popup.
	"""

	# signals for UI connection
	task_finished = PySide6.QtCore.Signal(int, object)
	task_error = PySide6.QtCore.Signal(int, str)
	task_progress = PySide6.QtCore.Signal(int, int, int, str)
	# emitted when any job starts, finishes, or errors
	job_list_changed = PySide6.QtCore.Signal()

	def __init__(self, max_workers: int = 2, parent=None):
		"""Initialize the task manager.

		Args:
			max_workers: Maximum number of concurrent worker threads.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._pool = PySide6.QtCore.QThreadPool()
		self._pool.setMaxThreadCount(max_workers)
		self._workers: dict = {}
		self._results: dict = {}
		self._lock = threading.Lock()
		self._next_id: int = 0
		# job metadata: task_id -> {name, status, error_text, submitted_at}
		self._jobs: dict = {}

	#============================================
	def submit_job(self, name: str, fn, *args, **kwargs) -> int:
		"""Submit a named job for background execution with UI tracking.

		Like submit(), but stores a human-readable name and status
		so the jobs popup can display progress.

		Args:
			name: Display name for the job (e.g. "Scraping The Matrix").
			fn: Callable to execute.
			*args: Positional arguments for the callable.
			**kwargs: Keyword arguments for the callable.

		Returns:
			Integer task ID for tracking the submitted job.
		"""
		task_id = self.submit(fn, *args, **kwargs)
		# store job metadata under the task_id
		with self._lock:
			self._jobs[task_id] = {
				"name": name,
				"status": "running",
				"error_text": "",
				"submitted_at": time.time(),
			}
		self.job_list_changed.emit()
		return task_id

	#============================================
	@property
	def active_count(self) -> int:
		"""Return the number of currently running jobs."""
		with self._lock:
			count = sum(
				1 for j in self._jobs.values()
				if j["status"] == "running"
			)
		return count

	#============================================
	@property
	def all_jobs(self) -> list:
		"""Return job metadata list sorted newest first."""
		with self._lock:
			jobs = [
				dict(j, task_id=tid)
				for tid, j in self._jobs.items()
			]
		# sort by submitted_at descending (newest first)
		jobs.sort(key=lambda j: j["submitted_at"], reverse=True)
		return jobs

	#============================================
	def clear_completed(self) -> None:
		"""Remove all finished (done/error) jobs from the list."""
		with self._lock:
			done_ids = [
				tid for tid, j in self._jobs.items()
				if j["status"] != "running"
			]
			for tid in done_ids:
				del self._jobs[tid]
		self.job_list_changed.emit()

	#============================================
	def submit(self, fn, *args, **kwargs) -> int:
		"""Submit a callable for background execution.

		Args:
			fn: Callable to execute.
			*args: Positional arguments for the callable.
			**kwargs: Keyword arguments for the callable.

		Returns:
			Integer task ID for tracking the submitted work.
		"""
		with self._lock:
			task_id = self._next_id
			self._next_id += 1
		# create a Worker from the existing workers module
		worker = moviemanager.ui.workers.Worker(fn, *args, **kwargs)
		# connect signals with task_id bound via default arg
		worker.signals.finished.connect(
			lambda result, tid=task_id: self._on_finished(tid, result)
		)
		worker.signals.error.connect(
			lambda err, tid=task_id: self._on_error(tid, err)
		)
		worker.signals.progress.connect(
			lambda cur, tot, msg, tid=task_id: self._on_progress(
				tid, cur, tot, msg
			)
		)
		with self._lock:
			self._workers[task_id] = worker
		self._pool.start(worker)
		return task_id

	#============================================
	def is_running(self, task_id: int) -> bool:
		"""Check whether a task is currently running.

		Args:
			task_id: The task ID to check.

		Returns:
			True if the task is still running (not yet done).
		"""
		with self._lock:
			worker = self._workers.get(task_id)
			if worker is None:
				return False
			# if we have a result or error, it is done
			is_done = task_id in self._results
		return not is_done

	#============================================
	def is_done(self, task_id: int) -> bool:
		"""Check whether a task has completed.

		Args:
			task_id: The task ID to check.

		Returns:
			True if the task has finished (done or cancelled).
		"""
		with self._lock:
			if task_id not in self._workers:
				return False
			is_done = task_id in self._results
		return is_done

	#============================================
	def cancel(self, task_id: int) -> None:
		"""Request cancellation of a running task.

		Args:
			task_id: The task ID to cancel.
		"""
		with self._lock:
			worker = self._workers.get(task_id)
		if worker is not None:
			worker.cancel()

	#============================================
	def get_result(self, task_id: int):
		"""Get the result of a completed task.

		Args:
			task_id: The task ID to retrieve results for.

		Returns:
			The return value of the submitted callable.

		Raises:
			KeyError: If the task ID is not found.
		"""
		with self._lock:
			if task_id not in self._results:
				raise KeyError(f"No result for task ID: {task_id}")
			return self._results[task_id]

	#============================================
	def get_worker(self, task_id: int):
		"""Get the Worker instance for a task.

		Useful for connecting additional signals or checking
		cancellation state.

		Args:
			task_id: The task ID.

		Returns:
			Worker instance or None if not found.
		"""
		with self._lock:
			return self._workers.get(task_id)

	#============================================
	def shutdown(self) -> None:
		"""Cancel all running tasks and clear the pool."""
		with self._lock:
			for worker in self._workers.values():
				worker.cancel()
		self._pool.clear()
		self._pool.waitForDone(1000)

	#============================================
	def _on_finished(self, task_id: int, result) -> None:
		"""Handle worker completion and store result.

		Args:
			task_id: The task ID that completed.
			result: The return value of the callable.
		"""
		with self._lock:
			self._results[task_id] = result
			# update job metadata if this was a named job
			if task_id in self._jobs:
				self._jobs[task_id]["status"] = "done"
		self.task_finished.emit(task_id, result)
		# emit job list change if this was a tracked job
		if task_id in self._jobs:
			self.job_list_changed.emit()

	#============================================
	def _on_error(self, task_id: int, error_text: str) -> None:
		"""Handle worker error and forward signal.

		Args:
			task_id: The task ID that failed.
			error_text: The error traceback text.
		"""
		with self._lock:
			self._results[task_id] = None
			# update job metadata if this was a named job
			if task_id in self._jobs:
				self._jobs[task_id]["status"] = "error"
				self._jobs[task_id]["error_text"] = error_text
		self.task_error.emit(task_id, error_text)
		# emit job list change if this was a tracked job
		if task_id in self._jobs:
			self.job_list_changed.emit()

	#============================================
	def _on_progress(self, task_id: int, current: int, total: int, message: str) -> None:
		"""Handle worker progress and forward signal.

		Args:
			task_id: The task ID reporting progress.
			current: Current progress value.
			total: Total expected value.
			message: Progress description.
		"""
		self.task_progress.emit(task_id, current, total, message)
