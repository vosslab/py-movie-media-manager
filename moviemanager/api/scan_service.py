"""API-level scan service wrapping core scan_service and MovieList."""

# local repo modules
import moviemanager.core.movie.movie_list
import moviemanager.core.movie.scan_service


#============================================
class ScanService:
	"""API-level scan operations backed by MovieList.

	Wraps the core scan_service directory scanner and provides
	count/filter operations on the in-memory MovieList.
	"""

	#============================================
	def __init__(
		self,
		movie_list: moviemanager.core.movie.movie_list.MovieList,
	):
		"""Initialize the scan service.

		Args:
			movie_list: Shared MovieList for the current session.
		"""
		self._movie_list = movie_list

	#============================================
	def scan_directory(
		self, root_path: str, progress_callback=None,
		movie_callback=None,
	) -> list:
		"""Scan a directory for movie files and add them to the library.

		Args:
			root_path: Root directory path to scan.
			progress_callback: Optional callable(current, message).
			movie_callback: Optional callable(movie) for incremental delivery.

		Returns:
			List of Movie instances discovered during the scan.
		"""
		movies = moviemanager.core.movie.scan_service.scan_directory(
			root_path, progress_callback=progress_callback,
			movie_callback=movie_callback,
		)
		for movie in movies:
			self._movie_list.add(movie)
		return movies

	#============================================
	def get_movies(self) -> list:
		"""Return all movies in the library.

		Returns:
			List of all Movie instances.
		"""
		result = self._movie_list.get_all()
		return result

	#============================================
	def get_unscraped(self) -> list:
		"""Return movies that have not been scraped.

		Returns:
			List of unscraped Movie instances.
		"""
		result = self._movie_list.get_unscraped()
		return result

	#============================================
	def get_movie_count(self) -> int:
		"""Return the total number of movies in the library.

		Returns:
			Integer count of movies.
		"""
		result = self._movie_list.count()
		return result

	#============================================
	def get_scraped_count(self) -> int:
		"""Return the number of scraped movies.

		Returns:
			Integer count of scraped movies.
		"""
		result = len(self._movie_list.get_scraped())
		return result

	#============================================
	def get_unscraped_count(self) -> int:
		"""Return the number of unscraped movies.

		Returns:
			Integer count of unscraped movies.
		"""
		result = len(self._movie_list.get_unscraped())
		return result
