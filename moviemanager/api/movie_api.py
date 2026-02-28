"""Facade providing all movie operations for CLI and GUI."""

# local repo modules
import moviemanager.core.movie.movie_list
import moviemanager.core.movie.scanner
import moviemanager.core.settings


#============================================
class MovieAPI:
	"""Facade providing all movie operations for CLI and GUI.

	Wraps scanning, scraping, and renaming behind a single interface.
	Maintains an in-memory MovieList for the current session.
	"""

	def __init__(self, settings: moviemanager.core.settings.Settings = None):
		"""Initialize the MovieAPI.

		Args:
			settings: Application settings. If None, uses defaults.
		"""
		if settings is None:
			settings = moviemanager.core.settings.Settings()
		self._settings = settings
		self._movie_list = moviemanager.core.movie.movie_list.MovieList()

	#============================================
	def scan_directory(self, root_path: str) -> list:
		"""Scan a directory for movie files and add them to the library.

		Args:
			root_path: Root directory path to scan.

		Returns:
			List of Movie instances discovered during the scan.
		"""
		movies = moviemanager.core.movie.scanner.scan_directory(root_path)
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
	def search_movie(self, title: str, year: str = "") -> list:
		"""Search for movie metadata by title.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			List of SearchResult instances from the scraper.
		"""
		# scraper integration will be wired in M3
		result = []
		return result

	#============================================
	def scrape_movie(self, movie, tmdb_id: int = 0) -> None:
		"""Fetch and apply metadata from TMDB to a movie.

		Args:
			movie: Movie instance to update with scraped metadata.
			tmdb_id: Optional TMDB ID to fetch directly.
		"""
		# scraper integration will be wired in M3
		pass

	#============================================
	def rename_movie(
		self,
		movie,
		path_template: str = "",
		file_template: str = "",
		dry_run: bool = True,
	) -> list:
		"""Generate rename operations for a movie.

		Args:
			movie: Movie instance to rename.
			path_template: Template for directory name.
			file_template: Template for file name.
			dry_run: If True, only return planned renames.

		Returns:
			List of (source, destination) path tuples.
		"""
		# renamer integration will be wired in M3
		result = []
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
