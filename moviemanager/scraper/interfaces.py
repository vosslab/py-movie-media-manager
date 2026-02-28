"""Abstract base classes for scraper providers."""

# Standard Library
import abc

# local repo modules
import moviemanager.scraper.types


#============================================
class MetadataProvider(abc.ABC):
	"""Abstract base for metadata scraper providers."""

	#============================================
	@abc.abstractmethod
	def search(self, title: str, year: str = "") -> list:
		"""Search for movies matching title and optional year.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			list: List of SearchResult objects.
		"""

	#============================================
	@abc.abstractmethod
	def get_metadata(
		self, tmdb_id: int = 0, imdb_id: str = ""
	) -> moviemanager.scraper.types.MediaMetadata:
		"""Fetch full metadata for a specific movie.

		Args:
			tmdb_id: TMDB movie ID.
			imdb_id: IMDB movie ID (tt format).

		Returns:
			MediaMetadata: Complete movie metadata.
		"""


#============================================
class ArtworkProvider(abc.ABC):
	"""Abstract base for artwork providers."""

	#============================================
	@abc.abstractmethod
	def get_artwork(self, tmdb_id: int = 0, imdb_id: str = "") -> dict:
		"""Fetch available artwork URLs for a movie.

		Args:
			tmdb_id: TMDB movie ID.
			imdb_id: IMDB movie ID.

		Returns:
			dict: Mapping of artwork type to list of URL strings.
		"""
