"""Controller for movie scraping and metadata matching operations."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.dialogs.movie_chooser
import moviemanager.ui.task_api


#============================================
class MatchController(PySide6.QtCore.QObject):
	"""Handles single/batch scrape, metadata refresh, and parental guides.

	Manages the match lifecycle including interactive movie chooser dialog,
	batch auto-scrape with confidence scoring, metadata refresh with cache
	bypass, and parental guide fetching from IMDB.

	Signals:
		scrape_started: Emitted when a scrape operation begins.
		scrape_completed: Emitted when scrape finishes with result dict.
		metadata_updated: Emitted when metadata refresh completes.
		parental_guides_completed: Emitted when parental guide fetch completes.
		error: Emitted when an operation fails with error text.
	"""

	scrape_started = PySide6.QtCore.Signal()
	scrape_completed = PySide6.QtCore.Signal(dict)
	metadata_updated = PySide6.QtCore.Signal(dict)
	parental_guides_completed = PySide6.QtCore.Signal(dict)
	error = PySide6.QtCore.Signal(str)

	def __init__(self, api, task_api, parent=None):
		"""Initialize the match controller.

		Args:
			api: MovieAPI facade instance.
			task_api: TaskAPI for background job submission.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._api = api
		self._task_api = task_api
		# task ID tracking
		self._scrape_task_id = None
		self._refresh_task_id = None
		self._pg_task_id = None

	#============================================
	@property
	def scrape_task_id(self) -> int:
		"""Return the current scrape task ID."""
		return self._scrape_task_id

	#============================================
	@property
	def refresh_task_id(self) -> int:
		"""Return the current refresh task ID."""
		return self._refresh_task_id

	#============================================
	@property
	def pg_task_id(self) -> int:
		"""Return the current parental guide task ID."""
		return self._pg_task_id

	#============================================
	def set_api(self, api) -> None:
		"""Replace the MovieAPI instance (after settings change).

		Args:
			api: New MovieAPI facade instance.
		"""
		self._api = api

	#============================================
	def scrape_selected(
		self, movie_panel, main_window,
	) -> None:
		"""Scrape metadata for selected or checked movies.

		If multiple movies are checked, opens the chooser dialog in
		batch mode. Otherwise opens it for the single selected movie.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for the dialog.
		"""
		# unified resolution: checked > selected > single
		checked_movies = movie_panel.get_chosen_movies()
		if len(checked_movies) > 1:
			# batch mode: pass movies as a list
			dialog = (
				moviemanager.ui.dialogs.movie_chooser
				.MovieChooserDialog(
					checked_movies[0], self._api, main_window,
					movie_list=checked_movies,
					task_api=self._task_api,
				)
			)
		else:
			# single movie mode
			movie = movie_panel.get_selected_movie()
			if not movie:
				PySide6.QtWidgets.QMessageBox.information(
					main_window, "No Selection",
					"Please select a movie first."
				)
				return
			dialog = (
				moviemanager.ui.dialogs.movie_chooser
				.MovieChooserDialog(
					movie, self._api, main_window,
					task_api=self._task_api,
				)
			)
		accepted = PySide6.QtWidgets.QDialog.DialogCode.Accepted
		if dialog.exec() == accepted:
			# build result dict for the signal
			if len(checked_movies) > 1:
				batch_results = dialog.get_batch_results()
				count = sum(
					1 for v in batch_results.values() if v
				)
				result = {
					"batch": True,
					"matched": count,
					"total": len(checked_movies),
				}
			else:
				result = {"batch": False}
			self.scrape_completed.emit(result)

	#============================================
	def batch_scrape_unscraped(self, main_window) -> None:
		"""Scrape all unscraped movies using auto-select best match.

		Uses confidence scoring to only auto-select high-confidence
		matches (>= 0.7). Runs in a background thread.

		Args:
			main_window: Parent window for dialogs.
		"""
		movies = self._api.get_movies()
		unscraped = [m for m in movies if not m.scraped]
		if not unscraped:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "Batch Scrape",
				"All movies are already scraped."
			)
			return
		self.scrape_started.emit()
		# run scraping in background via TaskAPI
		self._scrape_task_id = self._task_api.submit_job(
			"Batch scrape", self._batch_scrape_loop, unscraped,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)

	#============================================
	def _batch_scrape_loop(self, unscraped: list) -> dict:
		"""Execute batch scrape loop in a background thread.

		Searches and auto-matches each unscraped movie using
		confidence scoring. Called by Worker in QThreadPool.

		Args:
			unscraped: List of unscraped Movie instances.

		Returns:
			Dict with scraped_count, skipped_low_confidence,
			no_results_list, and parental_guide_failures.
		"""
		confidence_threshold = 0.7
		scraped_count = 0
		skipped_low_confidence = []
		no_results_list = []
		for i, movie in enumerate(unscraped):
			# check for cancellation via TaskAPI worker
			scrape_worker = self._task_api.get_worker(
				self._scrape_task_id
			)
			if scrape_worker and scrape_worker.is_cancelled:
				break
			# emit progress via worker signals
			if scrape_worker:
				scrape_worker.signals.progress.emit(
					i, len(unscraped),
					f"Scraping: {movie.title}"
					f" ({i + 1}/{len(unscraped)})",
				)
			# search and auto-select best match
			results = self._api.search_movie(
				movie.title, movie.year
			)
			if not results:
				no_results_list.append(movie.title)
				continue
			best = results[0]
			# use pre-computed match confidence from search
			confidence = best.match_confidence
			if confidence < confidence_threshold:
				skipped_low_confidence.append(
					f"{movie.title} -> {best.title}"
					f" ({confidence:.1f})"
				)
				continue
			# use tmdb_id or imdb_id depending on provider
			if best.tmdb_id:
				self._api.scrape_movie(
					movie, tmdb_id=best.tmdb_id
				)
			elif best.imdb_id:
				self._api.scrape_movie(
					movie, imdb_id=best.imdb_id
				)
			scraped_count += 1
		# check how many parental guide fetches failed
		pg_fail_count = len(
			self._api._failed_parental_guides
		)
		result = {
			"scraped_count": scraped_count,
			"skipped_low_confidence": skipped_low_confidence,
			"no_results_list": no_results_list,
			"parental_guide_failures": pg_fail_count,
		}
		return result

	#============================================
	def on_batch_scrape_done(
		self, result: dict, main_window,
	) -> None:
		"""Handle batch scrape completion.

		Shows summary dialog and queues parental guide retry if needed.

		Args:
			result: Dict with scraped_count, skipped_low_confidence,
				no_results_list, and parental_guide_failures.
			main_window: Parent window for dialogs.
		"""
		self._scrape_task_id = None
		# build summary
		scraped_count = result["scraped_count"]
		skipped_low_confidence = result["skipped_low_confidence"]
		no_results_list = result["no_results_list"]
		summary_parts = [f"Scraped: {scraped_count}"]
		if skipped_low_confidence:
			summary_parts.append(
				f"Skipped (low confidence):"
				f" {len(skipped_low_confidence)}"
			)
		if no_results_list:
			summary_parts.append(
				f"No results: {len(no_results_list)}"
			)
		# report parental guide failures
		pg_failures = result.get("parental_guide_failures", 0)
		if pg_failures:
			summary_parts.append(
				f"Parental guide timeouts: {pg_failures}"
				" (will retry)"
			)
		summary_text = "\n".join(summary_parts)
		# add detail about skipped movies
		if skipped_low_confidence:
			summary_text += "\n\nLow confidence matches:\n"
			summary_text += "\n".join(
				skipped_low_confidence[:20]
			)
		PySide6.QtWidgets.QMessageBox.information(
			main_window, "Batch Scrape Complete", summary_text
		)
		# submit deferred retry for failed parental guides
		if self._api.has_failed_parental_guides():
			self._task_api.submit_job(
				"Retry parental guides",
				self._api.retry_failed_parental_guides,
				_priority=moviemanager.ui.task_api.PRIORITY_LOW,
			)
		self.scrape_completed.emit(result)

	#============================================
	def refresh_metadata(
		self, movie_panel, main_window,
	) -> None:
		"""Re-fetch metadata from IMDB/TMDB for matched movies.

		Uses get_chosen_movies() to resolve checked/selected movies,
		filtering to scraped movies. Falls back to all scraped movies.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for dialogs.
		"""
		# unified resolution: checked > selected > empty
		chosen = movie_panel.get_chosen_movies()
		scraped = [m for m in chosen if m.scraped]
		if not scraped:
			# nothing chosen; fall back to all scraped movies
			all_movies = self._api.get_movies()
			scraped = [m for m in all_movies if m.scraped]
		if not scraped:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "Refresh Metadata",
				"No matched movies to refresh."
			)
			return
		# confirm with the user
		reply = PySide6.QtWidgets.QMessageBox.question(
			main_window, "Refresh Metadata",
			f"Re-fetch metadata for {len(scraped)} matched"
			f" movie{'s' if len(scraped) != 1 else ''}?",
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			| PySide6.QtWidgets.QMessageBox.StandardButton.No,
		)
		yes = PySide6.QtWidgets.QMessageBox.StandardButton.Yes
		if reply != yes:
			return
		# run refresh in background via TaskAPI
		self._refresh_task_id = self._task_api.submit_job(
			"Refresh metadata",
			self._refresh_metadata_loop, scraped,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)

	#============================================
	def _refresh_metadata_loop(self, movies: list) -> dict:
		"""Execute metadata refresh loop in a background thread.

		Re-scrapes each movie with cache bypass to get fresh
		metadata from the remote provider.

		Args:
			movies: List of scraped Movie instances to refresh.

		Returns:
			Dict with refreshed_count.
		"""
		refreshed_count = 0
		for i, movie in enumerate(movies):
			# check for cancellation via TaskAPI worker
			refresh_worker = self._task_api.get_worker(
				self._refresh_task_id
			)
			if refresh_worker and refresh_worker.is_cancelled:
				break
			# emit progress via worker signals
			if refresh_worker:
				refresh_worker.signals.progress.emit(
					i, len(movies),
					f"Refreshing: {movie.title}"
					f" ({i + 1}/{len(movies)})",
				)
			# re-scrape with cache bypass
			self._api.scrape_movie(
				movie,
				tmdb_id=movie.tmdb_id,
				imdb_id=movie.imdb_id,
				bypass_cache=True,
			)
			refreshed_count += 1
		result = {"refreshed_count": refreshed_count}
		return result

	#============================================
	def on_refresh_metadata_done(
		self, result: dict, main_window,
	) -> None:
		"""Handle metadata refresh completion.

		Args:
			result: Dict with refreshed_count.
			main_window: Parent window for dialogs.
		"""
		self._refresh_task_id = None
		count = result["refreshed_count"]
		PySide6.QtWidgets.QMessageBox.information(
			main_window, "Refresh Metadata Complete",
			f"Refreshed metadata for {count}"
			f" movie{'s' if count != 1 else ''}."
		)
		self.metadata_updated.emit(result)

	#============================================
	def fetch_parental_guides(
		self, movie_panel, main_window,
	) -> None:
		"""Fetch parental guide data from IMDB for matched movies.

		Uses get_chosen_movies() to resolve checked/selected movies.
		Falls back to all scraped movies with imdb_id.

		Args:
			movie_panel: MoviePanel widget for getting selection.
			main_window: Parent window for dialogs.
		"""
		# unified resolution: checked > selected > empty
		chosen = movie_panel.get_chosen_movies()
		if chosen:
			candidates = [
				m for m in chosen
				if m.scraped and m.imdb_id
			]
		else:
			all_movies = self._api.get_movies()
			candidates = [
				m for m in all_movies
				if m.scraped and m.imdb_id
			]
		if not candidates:
			PySide6.QtWidgets.QMessageBox.information(
				main_window, "Fetch Parental Guide",
				"No matched movies with IMDB IDs found."
			)
			return
		# confirm with the user
		reply = PySide6.QtWidgets.QMessageBox.question(
			main_window, "Fetch Parental Guide",
			f"Fetch parental guide data for {len(candidates)}"
			f" movie{'s' if len(candidates) != 1 else ''}?\n"
			f"Movies already checked within 90 days"
			f" will be skipped.",
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			| PySide6.QtWidgets.QMessageBox.StandardButton.No,
		)
		yes = PySide6.QtWidgets.QMessageBox.StandardButton.Yes
		if reply != yes:
			return
		# run in background via TaskAPI
		self._pg_task_id = self._task_api.submit_job(
			"Fetch parental guides",
			self._fetch_parental_guides_loop, candidates,
			_priority=moviemanager.ui.task_api.PRIORITY_NORMAL,
		)

	#============================================
	def _fetch_parental_guides_loop(
		self, movies: list,
	) -> dict:
		"""Execute parental guide fetch in a background thread.

		Args:
			movies: List of Movie instances with imdb_id set.

		Returns:
			Dict with fetched, no_data, failed, skipped counts.
		"""
		def progress_callback(
			cur: int, tot: int, msg: str,
		) -> None:
			worker = self._task_api.get_worker(
				self._pg_task_id
			)
			if worker:
				worker.signals.progress.emit(cur, tot, msg)
		result = self._api.fetch_parental_guides(
			movies, progress_callback=progress_callback,
		)
		return result

	#============================================
	def on_fetch_parental_guides_done(
		self, result: dict, main_window,
	) -> None:
		"""Handle parental guide fetch completion.

		Args:
			result: Dict with fetched, no_data, failed, skipped.
			main_window: Parent window for dialogs.
		"""
		self._pg_task_id = None
		# build summary message
		fetched = result.get("fetched", 0)
		no_data = result.get("no_data", 0)
		failed = result.get("failed", 0)
		skipped = result.get("skipped", 0)
		lines = []
		if fetched:
			lines.append(f"Fetched: {fetched}")
		if no_data:
			lines.append(f"No data on IMDB: {no_data}")
		if failed:
			lines.append(f"Failed: {failed}")
		if skipped:
			lines.append(f"Skipped: {skipped}")
		summary = (
			"\n".join(lines)
			if lines else "No movies processed."
		)
		PySide6.QtWidgets.QMessageBox.information(
			main_window,
			"Parental Guide Fetch Complete",
			summary,
		)
		self.parental_guides_completed.emit(result)

	#============================================
	def cancel(self) -> None:
		"""Cancel any running match tasks."""
		for tid in (
			self._scrape_task_id,
			self._refresh_task_id,
			self._pg_task_id,
		):
			if tid is not None:
				self._task_api.cancel(tid)
		self._scrape_task_id = None
		self._refresh_task_id = None
		self._pg_task_id = None
