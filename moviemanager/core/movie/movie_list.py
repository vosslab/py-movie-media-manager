"""In-memory collection of Movie objects."""

# local repo modules
import moviemanager.core.models.movie


#============================================
class MovieList:
	"""In-memory collection of Movie objects.

	Provides add, remove, find, and filter operations on a list of
	Movie instances without persistence.
	"""

	def __init__(self):
		"""Initialize an empty movie list."""
		self._movies: list = []

	#============================================
	def add(self, movie: moviemanager.core.models.movie.Movie) -> None:
		"""Add a Movie to the collection.

		Args:
			movie: Movie instance to add.
		"""
		self._movies.append(movie)

	#============================================
	def remove(self, movie: moviemanager.core.models.movie.Movie) -> None:
		"""Remove a Movie from the collection by identity.

		Args:
			movie: Movie instance to remove.
		"""
		self._movies.remove(movie)

	#============================================
	def get_all(self) -> list:
		"""Return a shallow copy of the movie list.

		Returns:
			List of all Movie instances in the collection.
		"""
		result = list(self._movies)
		return result

	#============================================
	def find_by_path(
		self, path: str
	) -> moviemanager.core.models.movie.Movie | None:
		"""Find a movie by its directory path.

		Args:
			path: Directory path to match against movie.path.

		Returns:
			The first Movie with a matching path, or None.
		"""
		for movie in self._movies:
			if movie.path == path:
				return movie
		return None

	#============================================
	def find_by_title(self, title: str) -> list:
		"""Find movies matching a title substring (case-insensitive).

		Args:
			title: Substring to match against movie titles.

		Returns:
			List of Movie instances whose title contains the substring.
		"""
		lower_title = title.lower()
		matches = [
			m for m in self._movies
			if lower_title in m.title.lower()
		]
		return matches

	#============================================
	def get_unscraped(self) -> list:
		"""Return movies that have not been scraped.

		Returns:
			List of Movie instances where scraped is False.
		"""
		result = [m for m in self._movies if not m.scraped]
		return result

	#============================================
	def get_scraped(self) -> list:
		"""Return movies that have been scraped.

		Returns:
			List of Movie instances where scraped is True.
		"""
		result = [m for m in self._movies if m.scraped]
		return result

	#============================================
	def count(self) -> int:
		"""Return the total number of movies in the collection.

		Returns:
			Integer count of movies.
		"""
		result = len(self._movies)
		return result

	#============================================
	def clear(self) -> None:
		"""Remove all movies from the collection."""
		self._movies.clear()
