"""Controller for artwork, trailer, and subtitle download operations."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.task_api


#============================================
class DownloadController(PySide6.QtCore.QObject):
	"""Handles artwork, trailer, and subtitle downloads.

	Manages the download lifecycle including batch task creation,
	per-movie content checks, and completion tracking.

	Signals:
		download_started: Emitted when download batch begins with count.
		download_completed: Emitted when all downloads in batch finish.
		download_failed: Emitted when a download fails with error text.
	"""

	download_started = PySide6.QtCore.Signal(int)
	download_completed = PySide6.QtCore.Signal()
	download_failed = PySide6.QtCore.Signal(str)

	def __init__(self, api, task_api, settings, parent=None):
		"""Initialize the download controller.

		Args:
			api: MovieAPI facade instance.
			task_api: TaskAPI for background job submission.
			settings: Application settings object.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._api = api
		self._task_api = task_api
		self._settings = settings
		# tracked download task IDs for the current batch
		self._download_task_ids = []

	#============================================
	@property
	def download_task_ids(self) -> list:
		"""Return the list of active download task IDs."""
		return list(self._download_task_ids)

	#============================================
	def set_api(self, api) -> None:
		"""Replace the MovieAPI instance (after settings change).

		Args:
			api: New MovieAPI facade instance.
		"""
		self._api = api

	#============================================
	def set_settings(self, settings) -> None:
		"""Replace the settings instance.

		Args:
			settings: New application settings object.
		"""
		self._settings = settings

	#============================================
	def download_content(
		self, movie_panel, main_window,
	) -> None:
		"""Download artwork, trailers, and subtitles via TaskAPI.

		Submits individual download jobs per content type per movie
		so each appears in the Jobs dialog.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for dialogs.
		"""
		# prevent concurrent batch downloads
		if self._download_task_ids:
			still_running = any(
				self._task_api.is_running(tid)
				for tid in self._download_task_ids
			)
			if still_running:
				PySide6.QtWidgets.QMessageBox.information(
					main_window, "Download In Progress",
					"A download batch is already running. "
					"Check the Jobs dialog for progress."
				)
				return
		# unified resolution: checked > selected > single
		chosen = movie_panel.get_chosen_movies()
		# filter to scraped movies only
		scraped_movies = [m for m in chosen if m.scraped]
		if not scraped_movies:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "No Matched Movies",
				"Match movies to IMDB first (Step 1)."
			)
			return
		# check subtitle credentials before queuing batch
		if self._settings.download_subtitles:
			if not self.check_subtitle_credentials(
				main_window
			):
				return
		# build list of individual download tasks
		tasks = self._build_download_tasks(scraped_movies)
		if not tasks:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "Nothing to Download",
				"All content is already present."
			)
			return
		# confirm before starting
		movie_count = len(scraped_movies)
		task_count = len(tasks)
		reply = PySide6.QtWidgets.QMessageBox.question(
			main_window, "Download Content",
			f"Queue {task_count} download(s) for "
			f"{movie_count} movie(s)?\n\n"
			"Downloads will run in the background.\n"
			"Check the Jobs dialog for progress.",
			PySide6.QtWidgets.QMessageBox.StandardButton.Ok
			| PySide6.QtWidgets.QMessageBox.StandardButton
			.Cancel,
		)
		ok = PySide6.QtWidgets.QMessageBox.StandardButton.Ok
		if reply != ok:
			return
		# submit each task via TaskAPI
		self._download_task_ids = []
		for name, fn, args in tasks:
			task_id = self._task_api.submit_job(
				name, fn, *args,
				_priority=(
					moviemanager.ui.task_api.PRIORITY_LOW
				),
			)
			self._download_task_ids.append(task_id)
		self.download_started.emit(task_count)

	#============================================
	def _build_download_tasks(
		self, movies: list,
	) -> list:
		"""Build a list of individual download task tuples.

		Checks settings and per-movie state to determine which
		downloads are needed.

		Args:
			movies: List of scraped Movie instances.

		Returns:
			List of (name, fn, args_tuple) tuples for submit_job.
		"""
		tasks = []
		languages = self._settings.subtitle_languages
		for movie in movies:
			title = movie.title or "Unknown"
			# artwork (poster + fanart)
			if (self._settings.download_poster
					and not movie.has_poster):
				tasks.append((
					f"Artwork: {title}",
					self._api.download_artwork,
					(movie,),
				))
			# trailer
			if (self._settings.download_trailer
					and not movie.has_trailer):
				tasks.append((
					f"Trailer: {title}",
					self._api.download_trailer,
					(movie,),
				))
			# subtitles
			if (self._settings.download_subtitles
					and not movie.has_subtitle):
				tasks.append((
					f"Subtitles: {title}",
					self._api.download_subtitles,
					(movie, languages),
				))
		return tasks

	#============================================
	def on_download_job_done(
		self, task_id: int, result,
	) -> None:
		"""Handle individual download job completion.

		When all tracked batch download jobs are done, emits
		download_completed signal.

		Args:
			task_id: The completed task ID.
			result: The return value of the download callable.
		"""
		if not self._download_task_ids:
			return
		if task_id not in self._download_task_ids:
			return
		# check if every job in the batch has finished
		all_done = all(
			self._task_api.is_done(tid)
			for tid in self._download_task_ids
		)
		if all_done:
			self._download_task_ids = []
			self.download_completed.emit()

	#============================================
	def download_trailer(
		self, movie_panel, main_window,
	) -> None:
		"""Download trailer for selected movie via TaskAPI.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for dialogs.
		"""
		movie = movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "No Selection",
				"Please select a movie first."
			)
			return
		if not movie.trailer_url:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "No Trailer",
				"No trailer URL available."
				" Scrape the movie first."
			)
			return
		title = movie.title or "Unknown"
		self._task_api.submit_job(
			f"Trailer: {title}",
			self._api.download_trailer, movie,
			_priority=moviemanager.ui.task_api.PRIORITY_LOW,
		)

	#============================================
	def check_subtitle_credentials(
		self, main_window,
	) -> bool:
		"""Check OpenSubtitles API key and login credentials.

		Shows a warning dialog and offers to open Settings if anything
		is missing. Returns True if all credentials are configured.

		Args:
			main_window: Parent window for dialogs.

		Returns:
			True if all credentials are configured.
		"""
		missing = []
		if not self._settings.opensubtitles_api_key:
			missing.append("API key")
		if not self._settings.opensubtitles_username:
			missing.append("username")
		if not self._settings.opensubtitles_password:
			missing.append("password")
		if not missing:
			return True
		label = ", ".join(missing)
		result = PySide6.QtWidgets.QMessageBox.warning(
			main_window,
			"OpenSubtitles Credentials Missing",
			f"Subtitle downloads require"
			f" OpenSubtitles {label}.\n\n"
			"Open Settings to configure them?",
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			| PySide6.QtWidgets.QMessageBox.StandardButton.No,
		)
		yes = PySide6.QtWidgets.QMessageBox.StandardButton.Yes
		return result == yes

	#============================================
	def download_subtitles(
		self, movie_panel, main_window,
	) -> None:
		"""Download subtitles for selected movie via TaskAPI.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for dialogs.
		"""
		movie = movie_panel.get_selected_movie()
		if not movie:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "No Selection",
				"Please select a movie first."
			)
			return
		if not movie.imdb_id:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "No IMDB ID",
				"Movie needs an IMDB ID."
				" Scrape the movie first."
			)
			return
		# check credentials before queuing
		if not self.check_subtitle_credentials(main_window):
			return
		title = movie.title or "Unknown"
		languages = self._settings.subtitle_languages
		self._task_api.submit_job(
			f"Subtitles: {title}",
			self._api.download_subtitles, movie, languages,
			_priority=moviemanager.ui.task_api.PRIORITY_LOW,
		)

	#============================================
	def cancel(self) -> None:
		"""Cancel any pending download jobs."""
		for tid in self._download_task_ids:
			self._task_api.cancel(tid)
		self._download_task_ids = []
