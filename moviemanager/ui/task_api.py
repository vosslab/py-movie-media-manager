"""Qt-integrated background task manager using QThreadPool."""

# Standard Library
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
	"""

	# signals for UI connection
	task_finished = PySide6.QtCore.Signal(int, object)
	task_error = PySide6.QtCore.Signal(int, str)
	task_progress = PySide6.QtCore.Signal(int, int, int, str)

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
		self.task_finished.emit(task_id, result)

	#============================================
	def _on_error(self, task_id: int, error_text: str) -> None:
		"""Handle worker error and forward signal.

		Args:
			task_id: The task ID that failed.
			error_text: The error traceback text.
		"""
		with self._lock:
			self._results[task_id] = None
		self.task_error.emit(task_id, error_text)

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
