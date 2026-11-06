"""Tests for error delivery from Qt background workers."""

# local repo modules
import moviemanager.ui.workers


#============================================
def raise_runtime_error() -> None:
	"""Raise the runtime error that workers must report to their caller."""
	raise RuntimeError("expected worker failure")


#============================================
def test_worker_reports_runtime_error() -> None:
	"""A callable failure reaches the error signal instead of disappearing."""
	errors: list[str] = []
	worker = moviemanager.ui.workers.Worker(raise_runtime_error)
	worker.signals.error.connect(errors.append)
	worker.run()
	assert len(errors) == 1
	assert "expected worker failure" in errors[0]


#============================================
def test_cancelled_worker_does_not_run() -> None:
	"""Cancellation prevents a queued worker from calling its function."""
	called: list[bool] = []

	def record_call() -> None:
		called.append(True)

	worker = moviemanager.ui.workers.Worker(record_call)
	worker.cancel()
	worker.run()
	assert called == []
