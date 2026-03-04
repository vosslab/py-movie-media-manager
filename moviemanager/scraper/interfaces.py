"""Abstract base classes for scraper providers."""

# Standard Library
import abc
import enum

# local repo modules
import moviemanager.scraper.types


#============================================
class ProviderCapability(enum.Enum):
	"""Capabilities a scraper provider can advertise."""
	SEARCH = "search"
	METADATA = "metadata"
	ARTWORK = "artwork"
	PARENTAL_GUIDE = "parental_guide"
	SUBTITLES = "subtitles"
	TRAILER = "trailer"


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


#============================================
class ParentalGuideProvider(abc.ABC):
	"""Abstract base for parental guide providers."""

	#============================================
	@abc.abstractmethod
	def get_parental_guide(self, imdb_id: str) -> dict:
		"""Fetch parental guide severity data for a movie.

		Args:
			imdb_id: IMDB movie ID (tt format).

		Returns:
			dict: Category name to severity string mapping.
		"""


#============================================
class TrailerProvider(abc.ABC):
	"""Abstract base for trailer download providers."""

	#============================================
	@abc.abstractmethod
	def download_trailer(self, url: str, output_path: str) -> str:
		"""Download a trailer from a URL to output_path.

		Args:
			url: Trailer URL to download.
			output_path: Destination file path.

		Returns:
			str: Path to the downloaded trailer file.
		"""


#============================================
class SubtitleProvider(abc.ABC):
	"""Abstract base for subtitle download providers."""

	#============================================
	@abc.abstractmethod
	def search_subtitles(
		self, imdb_id: str, languages: list,
	) -> list:
		"""Search for subtitles by IMDB ID.

		Args:
			imdb_id: IMDB identifier string (tt format).
			languages: List of language codes.

		Returns:
			list: List of subtitle result dicts.
		"""

	#============================================
	@abc.abstractmethod
	def download_subtitle(
		self, file_id: int, output_path: str,
	) -> str:
		"""Download a subtitle file by file ID.

		Args:
			file_id: Subtitle file ID from search results.
			output_path: Destination file path.

		Returns:
			str: Path to the downloaded subtitle file.
		"""
