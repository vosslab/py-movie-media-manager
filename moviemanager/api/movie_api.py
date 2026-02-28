"""Facade providing all movie operations for CLI and GUI."""

# Standard Library
import os

# local repo modules
import moviemanager.core.movie.movie_list
import moviemanager.core.movie.renamer
import moviemanager.core.movie.scanner
import moviemanager.core.nfo.writer
import moviemanager.core.settings
import moviemanager.scraper.tmdb_scraper


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
		self._scraper = None

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
	def _ensure_tmdb_scraper(self) -> None:
		"""Create the TmdbScraper if not already initialized.

		Raises:
			ValueError: If no TMDB API key is configured.
		"""
		if self._scraper is not None:
			return
		api_key = self._settings.tmdb_api_key
		if not api_key:
			raise ValueError("TMDB API key is not configured")
		self._scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(
			api_key=api_key,
			language=self._settings.scrape_language,
		)

	#============================================
	def search_movie(self, title: str, year: str = "") -> list:
		"""Search for movie metadata by title.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			List of SearchResult instances from the scraper.
		"""
		self._ensure_tmdb_scraper()
		result = self._scraper.search(title, year)
		return result

	#============================================
	def scrape_movie(self, movie, tmdb_id: int = 0) -> None:
		"""Fetch and apply metadata from TMDB to a movie.

		Maps MediaMetadata fields onto the Movie object, marks it
		as scraped, and writes a Kodi-format NFO file.

		Args:
			movie: Movie instance to update with scraped metadata.
			tmdb_id: TMDB ID to fetch metadata for.
		"""
		self._ensure_tmdb_scraper()
		metadata = self._scraper.get_metadata(tmdb_id=tmdb_id)
		# map MediaMetadata fields to the Movie object
		movie.title = metadata.title or movie.title
		movie.original_title = metadata.original_title or movie.original_title
		movie.year = metadata.year or movie.year
		movie.plot = metadata.plot
		movie.tagline = metadata.tagline
		movie.runtime = metadata.runtime
		movie.rating = metadata.rating
		movie.votes = metadata.votes
		movie.genres = metadata.genres
		movie.director = metadata.director
		movie.writer = metadata.writer
		movie.studio = metadata.studio
		movie.country = metadata.country
		movie.spoken_languages = metadata.spoken_languages
		movie.imdb_id = metadata.imdb_id
		movie.tmdb_id = metadata.tmdb_id
		movie.poster_url = metadata.poster_url
		movie.fanart_url = metadata.fanart_url
		movie.certification = metadata.certification
		movie.release_date = metadata.release_date
		# convert CastMember dataclasses to dicts for NFO writer
		movie.actors = [
			{"name": a.name, "role": a.role, "tmdb_id": a.tmdb_id}
			for a in metadata.actors
		]
		movie.scraped = True
		# build NFO path from first video file basename
		nfo_path = ""
		video_file = movie.video_file
		if video_file:
			base, _ = os.path.splitext(video_file.filename)
			nfo_path = os.path.join(movie.path, base + ".nfo")
		else:
			# fallback: use movie title
			safe_title = movie.title or "movie"
			nfo_path = os.path.join(movie.path, safe_title + ".nfo")
		# write the NFO file
		moviemanager.core.nfo.writer.write_nfo(movie, nfo_path)
		movie.nfo_path = nfo_path

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
		# use settings templates as defaults
		if not path_template:
			path_template = self._settings.path_template
		if not file_template:
			file_template = self._settings.file_template
		result = moviemanager.core.movie.renamer.rename_movie(
			movie, path_template, file_template, dry_run=dry_run,
		)
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
