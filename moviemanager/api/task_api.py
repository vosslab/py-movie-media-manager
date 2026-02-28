"""Simple background task wrapper using ThreadPoolExecutor."""

# Standard Library
import concurrent.futures
import threading


#============================================
class TaskAPI:
	"""Submit and track background tasks.

	Wraps a ThreadPoolExecutor to provide a simple task ID based
	interface for submitting and querying background work.
	"""

	def __init__(self, max_workers: int = 2):
		"""Initialize the task executor.

		Args:
			max_workers: Maximum number of concurrent worker threads.
		"""
		self._executor = concurrent.futures.ThreadPoolExecutor(
			max_workers=max_workers
		)
		self._futures: dict = {}
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
			future = self._executor.submit(fn, *args, **kwargs)
			self._futures[task_id] = future
		return task_id

	#============================================
	def is_running(self, task_id: int) -> bool:
		"""Check whether a task is currently running.

		Args:
			task_id: The task ID to check.

		Returns:
			True if the task is running (not yet done).
		"""
		future = self._futures.get(task_id)
		if future is None:
			return False
		result = future.running()
		return result

	#============================================
	def is_done(self, task_id: int) -> bool:
		"""Check whether a task has completed.

		Args:
			task_id: The task ID to check.

		Returns:
			True if the task has finished (done or cancelled).
		"""
		future = self._futures.get(task_id)
		if future is None:
			return False
		result = future.done()
		return result

	#============================================
	def get_result(self, task_id: int):
		"""Get the result of a completed task.

		Args:
			task_id: The task ID to retrieve results for.

		Returns:
			The return value of the submitted callable.

		Raises:
			KeyError: If the task ID is not found.
			Exception: If the task raised an exception.
		"""
		future = self._futures.get(task_id)
		if future is None:
			raise KeyError(f"Unknown task ID: {task_id}")
		result = future.result(timeout=0)
		return result

	#============================================
	def shutdown(self) -> None:
		"""Shut down the executor without waiting for pending tasks."""
		self._executor.shutdown(wait=False)
