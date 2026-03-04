"""Batch navigation state for the movie chooser dialog."""


#============================================
class BatchNavigator:
	"""Manages batch traversal state for movie matching.

	Tracks the movie list, current index, and per-movie results
	(scraped, failed, pending). Pure Python with no Qt dependency.

	Args:
		movie: The initial movie to start with.
		movie_list: Optional list of movies for batch mode.
	"""

	def __init__(self, movie, movie_list=None):
		self._movie_list = movie_list or [movie]
		self._current_index = 0
		# find the starting movie in the list
		if movie_list:
			for i, m in enumerate(movie_list):
				if m is movie:
					self._current_index = i
					break
		# track batch results: movie path -> True/False/"pending"
		self._batch_results = {}
		self._batch_mode = (
			movie_list is not None and len(movie_list) > 1
		)

	#============================================
	@property
	def batch_mode(self) -> bool:
		"""Whether batch navigation is active."""
		return self._batch_mode

	#============================================
	@property
	def current_movie(self):
		"""The currently active movie."""
		return self._movie_list[self._current_index]

	#============================================
	@property
	def current_index(self) -> int:
		"""Zero-based index of the current movie."""
		return self._current_index

	#============================================
	@property
	def total_count(self) -> int:
		"""Total number of movies in the batch."""
		return len(self._movie_list)

	#============================================
	@property
	def matched_count(self) -> int:
		"""Number of movies successfully matched."""
		count = sum(
			1 for v in self._batch_results.values()
			if v is True
		)
		return count

	#============================================
	@property
	def failed_count(self) -> int:
		"""Number of movies that failed to match."""
		count = sum(
			1 for v in self._batch_results.values()
			if v is False
		)
		return count

	#============================================
	def mark_result(
		self, movie_path: str, result,
	) -> None:
		"""Record a match result for a movie.

		Args:
			movie_path: Path key for the movie.
			result: True for matched, False for failed,
				"pending" for in-progress.
		"""
		self._batch_results[movie_path] = result

	#============================================
	def advance(self) -> bool:
		"""Move to the next movie in the list.

		Returns:
			True if advanced, False if at the end.
		"""
		if self._current_index >= len(self._movie_list) - 1:
			return False
		self._current_index += 1
		return True

	#============================================
	def go_back(self) -> bool:
		"""Move to the previous movie in the list.

		Returns:
			True if moved back, False if at the start.
		"""
		if self._current_index <= 0:
			return False
		self._current_index -= 1
		return True

	#============================================
	def get_next_movie(self):
		"""Get the next movie without advancing the index.

		Returns:
			Next Movie instance, or None if at the end.
		"""
		next_idx = self._current_index + 1
		if next_idx >= len(self._movie_list):
			return None
		return self._movie_list[next_idx]

	#============================================
	def get_results(self) -> dict:
		"""Return the batch scrape results.

		Returns:
			dict: Mapping of movie path -> bool (True if scraped).
		"""
		return self._batch_results
