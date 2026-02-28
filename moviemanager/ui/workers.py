"""Background worker threads for non-blocking UI operations."""

# Standard Library
import io
import traceback

# PIP3 modules
import requests
import PySide6.QtCore


#============================================
class WorkerSignals(PySide6.QtCore.QObject):
	"""Signals for background workers."""

	# emitted when the task completes successfully with a result
	finished = PySide6.QtCore.Signal(object)
	# emitted when the task fails with an error message
	error = PySide6.QtCore.Signal(str)
	# emitted to report progress (current, total, message)
	progress = PySide6.QtCore.Signal(int, int, str)


#============================================
class Worker(PySide6.QtCore.QRunnable):
	"""Generic background worker that runs a callable off the main thread.

	Args:
		fn: The function to execute in background.
		args: Positional arguments for fn.
		kwargs: Keyword arguments for fn.
	"""

	def __init__(self, fn, *args, **kwargs):
		super().__init__()
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.signals = WorkerSignals()
		self._cancelled = False
		self.setAutoDelete(True)

	#============================================
	def cancel(self) -> None:
		"""Request cancellation of this worker."""
		self._cancelled = True

	#============================================
	@property
	def is_cancelled(self) -> bool:
		"""Return whether cancellation was requested."""
		return self._cancelled

	#============================================
	def run(self) -> None:
		"""Execute the function and emit finished or error."""
		if self._cancelled:
			return
		try:
			result = self.fn(*self.args, **self.kwargs)
			if not self._cancelled:
				self.signals.finished.emit(result)
		except Exception:
			if not self._cancelled:
				# capture full traceback for debugging
				buf = io.StringIO()
				traceback.print_exc(file=buf)
				error_text = buf.getvalue()
				self.signals.error.emit(error_text)


#============================================
class ImageDownloadWorker(PySide6.QtCore.QRunnable):
	"""Worker that downloads an image from a URL and emits the bytes.

	Args:
		url: The image URL to download.
		timeout: HTTP request timeout in seconds.
	"""

	def __init__(self, url: str, timeout: int = 15):
		super().__init__()
		self._url = url
		self._timeout = timeout
		self.signals = WorkerSignals()
		self._cancelled = False
		self.setAutoDelete(True)

	#============================================
	def cancel(self) -> None:
		"""Request cancellation of this worker."""
		self._cancelled = True

	#============================================
	def run(self) -> None:
		"""Download the image and emit raw bytes or error."""
		if self._cancelled:
			return
		try:
			response = requests.get(
				self._url, timeout=self._timeout
			)
			if self._cancelled:
				return
			if response.status_code == 200:
				self.signals.finished.emit(response.content)
			else:
				error_msg = (
					f"HTTP {response.status_code} "
					f"downloading {self._url}"
				)
				self.signals.error.emit(error_msg)
		except Exception:
			if not self._cancelled:
				self.signals.error.emit(traceback.format_exc())
