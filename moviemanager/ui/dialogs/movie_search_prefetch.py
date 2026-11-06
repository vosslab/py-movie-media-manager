"""Cancellable search-result prefetch for batch movie matching."""

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.models.movie
import moviemanager.scraper.types
import moviemanager.ui.task_api
import moviemanager.ui.workers


#============================================
class MovieSearchPrefetch:
	"""Cache the next movie's result list and first poster without touching widgets."""

	def __init__(
		self,
		api: moviemanager.api.movie_api.MovieAPI,
		task_api: moviemanager.ui.task_api.TaskAPI,
	) -> None:
		self._api = api
		self._task_api = task_api
		self._results: dict[str, list[moviemanager.scraper.types.SearchResult]] = {}
		self._posters: dict[str, bytes] = {}
		self._search_worker: object | None = None
		self._poster_worker: object | None = None

	#============================================
	def take_results(
		self, movie: moviemanager.core.models.movie.Movie,
	) -> list[moviemanager.scraper.types.SearchResult] | None:
		"""Return and remove the cached results for a movie."""
		return self._results.pop(movie.path, None)

	#============================================
	def take_poster(self, movie: moviemanager.core.models.movie.Movie) -> bytes | None:
		"""Return and remove the cached first-poster bytes for a movie."""
		return self._posters.pop(movie.path, None)

	#============================================
	def start(self, movie: moviemanager.core.models.movie.Movie | None) -> None:
		"""Begin a cancellable search for the next batch movie when present."""
		if movie is None or movie.path in self._results:
			return
		self._cancel_search()
		task_id = self._task_api.submit(
			self._api.search_movie, movie.title, movie.year,
			query_runtime=movie.runtime,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(
			lambda results, path=movie.path: self._on_results(path, results),
		)
		worker.signals.error.connect(lambda _error: self._clear_search_worker())
		self._search_worker = worker

	#============================================
	def _on_results(self, movie_path: str, results: list[moviemanager.scraper.types.SearchResult]) -> None:
		"""Cache results and begin a poster request for their first item."""
		self._results[movie_path] = results
		self._search_worker = None
		if not results or not results[0].poster_url:
			return
		self._cancel_poster()
		task_id = self._task_api.submit(
			moviemanager.ui.workers.download_image_bytes, results[0].poster_url,
			_priority=moviemanager.ui.task_api.PRIORITY_BACKGROUND,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(
			lambda data, path=movie_path: self._on_poster(path, data),
		)
		worker.signals.error.connect(lambda _error: self._clear_poster_worker())
		self._poster_worker = worker

	#============================================
	def _on_poster(self, movie_path: str, data: bytes) -> None:
		"""Cache poster bytes after the background request completes."""
		self._posters[movie_path] = data
		self._poster_worker = None

	#============================================
	def _clear_search_worker(self) -> None:
		"""Forget a failed or cancelled search worker."""
		self._search_worker = None

	#============================================
	def _clear_poster_worker(self) -> None:
		"""Forget a failed or cancelled poster worker."""
		self._poster_worker = None

	#============================================
	def _cancel_search(self) -> None:
		"""Cancel a pending result search."""
		if self._search_worker is not None:
			self._search_worker.cancel()
			self._search_worker = None

	#============================================
	def _cancel_poster(self) -> None:
		"""Cancel a pending poster download."""
		if self._poster_worker is not None:
			self._poster_worker.cancel()
			self._poster_worker = None

	#============================================
	def cancel(self) -> None:
		"""Cancel both task types before their owning dialog is destroyed."""
		self._cancel_search()
		self._cancel_poster()
