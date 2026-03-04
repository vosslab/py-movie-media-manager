"""Controller for movie file rename and organization operations."""

# Standard Library
import os
import shutil

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.dialogs.rename_preview
import moviemanager.ui.task_api


#============================================
class RenameController(PySide6.QtCore.QObject):
	"""Handles rename preview, batch rename, and undo operations.

	Manages the organize workflow including single and batch rename
	previews, execution, and undo history.

	Signals:
		rename_started: Emitted when a rename operation begins.
		rename_completed: Emitted when rename finishes with pair count.
		rename_error: Emitted when a rename fails with error text.
		undo_completed: Emitted when undo finishes with pair count.
	"""

	rename_started = PySide6.QtCore.Signal()
	rename_completed = PySide6.QtCore.Signal(int)
	rename_error = PySide6.QtCore.Signal(str)
	undo_completed = PySide6.QtCore.Signal(int)

	def __init__(self, api, task_api, parent=None):
		"""Initialize the rename controller.

		Args:
			api: MovieAPI facade instance.
			task_api: TaskAPI for background job submission.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._api = api
		self._task_api = task_api
		# task ID tracking
		self._rename_task_id = None
		self._rename_mode = None
		# pending state for callback
		self._pending_rename_movie = None
		self._pending_rename_pairs = None
		self._pending_batch_movies = None
		# rename history for undo (stack of rename batches)
		self._rename_history = []

	#============================================
	@property
	def rename_task_id(self) -> int:
		"""Return the current rename task ID."""
		return self._rename_task_id

	#============================================
	@property
	def rename_mode(self) -> str:
		"""Return the current rename mode string."""
		return self._rename_mode

	#============================================
	@property
	def has_undo_history(self) -> bool:
		"""Return whether there are renames to undo."""
		return bool(self._rename_history)

	#============================================
	def set_api(self, api) -> None:
		"""Replace the MovieAPI instance (after settings change).

		Args:
			api: New MovieAPI facade instance.
		"""
		self._api = api

	#============================================
	def clear_history(self) -> None:
		"""Clear rename undo history."""
		self._rename_history.clear()

	#============================================
	def rename_selected(
		self, movie_panel, main_window,
	) -> None:
		"""Organize selected movie files into proper folder structure.

		Supports batch mode when multiple movies are checked. Falls
		back to single-movie mode.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for dialogs and cursor.
		"""
		# unified resolution: checked > selected > single
		checked_movies = movie_panel.get_chosen_movies()
		# batch mode: multiple movies
		if len(checked_movies) > 1:
			self._rename_batch(checked_movies, main_window)
			return
		# single mode: one selected movie
		movie = movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "No Selection",
				"Please select a movie first."
			)
			return
		# compute rename preview in background thread
		self.rename_started.emit()
		self._pending_rename_movie = movie
		self._rename_mode = "single_preview"
		self._rename_task_id = self._task_api.submit_job(
			"Rename preview", self._api.rename_movie, movie,
			dry_run=True,
			_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
		)

	#============================================
	def on_rename_preview_done(
		self, pairs: list, main_window,
	) -> None:
		"""Show rename preview dialog after background dry-run.

		Args:
			pairs: List of (source, dest) path tuples from dry-run.
			main_window: Parent window for the dialog.
		"""
		self._rename_task_id = None
		movie = self._pending_rename_movie
		self._pending_rename_movie = None
		if not pairs:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "Organize",
				"No files to organize."
			)
			return
		# show rename preview dialog
		dialog = (
			moviemanager.ui.dialogs.rename_preview
			.RenamePreviewDialog(pairs, main_window)
		)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			# execute rename in background
			self.rename_started.emit()
			self._pending_rename_pairs = pairs
			self._rename_mode = "single_exec"
			self._rename_task_id = self._task_api.submit_job(
				"Renaming movie",
				self._api.rename_movie, movie,
				dry_run=False,
				_priority=(
					moviemanager.ui.task_api.PRIORITY_CRITICAL
				),
			)

	#============================================
	def on_rename_preview_error(self, error_text: str) -> None:
		"""Handle error from rename dry-run computation.

		Args:
			error_text: Error traceback text.
		"""
		self._rename_task_id = None
		self._rename_mode = None
		self._pending_rename_movie = None
		self.rename_error.emit(error_text)

	#============================================
	def on_rename_exec_done(self, result) -> None:
		"""Handle rename execution completion.

		Args:
			result: Task result (unused).
		"""
		self._rename_task_id = None
		self._rename_mode = None
		# record rename batch for undo
		pairs = self._pending_rename_pairs
		self._pending_rename_pairs = None
		self._rename_history.append(pairs)
		self.rename_completed.emit(len(pairs))

	#============================================
	def on_rename_exec_error(self, error_text: str) -> None:
		"""Handle error from rename execution.

		Args:
			error_text: Error traceback text.
		"""
		self._rename_task_id = None
		self._rename_mode = None
		self._pending_rename_pairs = None
		self.rename_error.emit(error_text)

	#============================================
	def _rename_batch(
		self, movies: list, main_window,
	) -> None:
		"""Organize multiple movies in batch with a combined preview.

		Args:
			movies: List of Movie instances to organize.
			main_window: Parent window for status/cursor.
		"""
		self.rename_started.emit()
		self._pending_batch_movies = movies
		self._rename_mode = "batch_preview"
		self._rename_task_id = self._task_api.submit_job(
			"Batch rename preview",
			self._compute_batch_rename_pairs, movies,
			_priority=moviemanager.ui.task_api.PRIORITY_CRITICAL,
		)

	#============================================
	def _compute_batch_rename_pairs(
		self, movies: list,
	) -> dict:
		"""Compute rename pairs for batch of movies (background thread).

		Args:
			movies: List of Movie instances to organize.

		Returns:
			Dict with all_pairs, movies_to_rename, and skipped count.
		"""
		all_pairs = []
		movies_to_rename = []
		skipped = 0
		for movie in movies:
			if not movie.scraped:
				skipped += 1
				continue
			pairs = self._api.rename_movie(movie, dry_run=True)
			if pairs:
				all_pairs.extend(pairs)
				movies_to_rename.append(movie)
		result = {
			"all_pairs": all_pairs,
			"movies_to_rename": movies_to_rename,
			"skipped": skipped,
		}
		return result

	#============================================
	def on_batch_rename_preview_done(
		self, result: dict, main_window,
	) -> None:
		"""Show combined preview dialog after batch dry-run.

		Args:
			result: Dict with all_pairs, movies_to_rename, skipped.
			main_window: Parent window for dialogs.
		"""
		self._rename_task_id = None
		all_pairs = result["all_pairs"]
		movies_to_rename = result["movies_to_rename"]
		skipped = result["skipped"]
		if not all_pairs:
			msg = "No matched movies to organize."
			if skipped:
				msg += f" ({skipped} unmatched movies skipped)"
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "Organize", msg
			)
			return
		# show combined preview dialog
		title = (
			f"Organize {len(movies_to_rename)} movies"
			f" ({len(all_pairs)} files)"
		)
		dialog = (
			moviemanager.ui.dialogs.rename_preview
			.RenamePreviewDialog(all_pairs, main_window)
		)
		dialog.setWindowTitle(title)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			# execute all renames in background
			self.rename_started.emit()
			self._pending_rename_pairs = all_pairs
			self._rename_mode = "batch_exec"
			self._rename_task_id = self._task_api.submit_job(
				"Batch renaming",
				self._execute_batch_renames, movies_to_rename,
				_priority=(
					moviemanager.ui.task_api.PRIORITY_CRITICAL
				),
			)

	#============================================
	def _execute_batch_renames(self, movies: list) -> list:
		"""Execute batch renames in background thread.

		Args:
			movies: List of Movie instances to rename.

		Returns:
			List of error strings (empty if all succeeded).
		"""
		errors = []
		for movie in movies:
			try:
				self._api.rename_movie(movie, dry_run=False)
			except Exception as exc:
				errors.append(f"{movie.title}: {exc}")
		return errors

	#============================================
	def on_batch_rename_exec_done(
		self, errors: list, main_window,
	) -> None:
		"""Handle batch rename execution completion.

		Args:
			errors: List of error strings from failed renames.
			main_window: Parent window for dialogs.
		"""
		self._rename_task_id = None
		self._rename_mode = None
		# record combined batch for undo
		pairs = self._pending_rename_pairs
		self._pending_rename_pairs = None
		self._rename_history.append(pairs)
		if errors:
			error_text = "\n".join(errors)
			self.rename_error.emit(error_text)
		else:
			self.rename_completed.emit(len(pairs))

	#============================================
	def undo_last_rename(self, main_window) -> None:
		"""Undo the last rename batch by reversing file moves.

		Args:
			main_window: Parent window for error dialogs.
		"""
		if not self._rename_history:
			return
		pairs = self._rename_history.pop()
		errors = []
		# reverse each rename: move new -> original
		for src, dst in pairs:
			if os.path.exists(dst):
				shutil.move(dst, src)
			else:
				errors.append(f"File not found: {dst}")
		if errors:
			error_text = "\n".join(errors)
			self.rename_error.emit(error_text)
		else:
			self.undo_completed.emit(len(pairs))

	#============================================
	def cancel(self) -> None:
		"""Cancel any running rename tasks."""
		if self._rename_task_id is not None:
			self._task_api.cancel(self._rename_task_id)
		self._rename_task_id = None
		self._rename_mode = None
