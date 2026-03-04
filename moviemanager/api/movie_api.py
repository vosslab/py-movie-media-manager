"""Facade providing all movie operations for CLI and GUI."""

# Standard Library
import logging

# local repo modules
import moviemanager.api.api_cache
import moviemanager.api.artwork_service
import moviemanager.api.match_confidence
import moviemanager.api.scan_service
import moviemanager.api.scrape_service
import moviemanager.api.search_service
import moviemanager.api.subtitle_service
import moviemanager.api.trailer_service
import moviemanager.core.movie.movie_list
import moviemanager.core.movie.rename_service
import moviemanager.core.movie.template_engine
import moviemanager.core.settings
import moviemanager.scraper.browser_cookies
import moviemanager.scraper.interfaces
import moviemanager.scraper.registry


# module logger
_LOG = logging.getLogger(__name__)


#============================================
class MovieAPI:
	"""Facade providing all movie operations for CLI and GUI.

	Thin composition root that delegates to focused service classes.
	Maintains scraper lifecycle and IMDB transport management.
	"""

	def __init__(
		self,
		settings: moviemanager.core.settings.Settings = None,
	):
		"""Initialize the MovieAPI.

		Args:
			settings: Application settings. If None, uses defaults.
		"""
		if settings is None:
			settings = moviemanager.core.settings.Settings()
		self._settings = settings
		self._movie_list = (
			moviemanager.core.movie.movie_list.MovieList()
		)
		self._cache = moviemanager.api.api_cache.ApiCache()
		self._registry = (
			moviemanager.scraper.registry.build_default_registry()
		)
		# scraper lifecycle (stays in MovieAPI)
		self._scraper = None
		self._imdb_scraper = None
		self._imdb_transport = None
		self._imdb_cookies_loaded_spec = ""
		# create service instances
		self._scan_svc = moviemanager.api.scan_service.ScanService(
			self._movie_list,
		)
		self._search_svc = (
			moviemanager.api.search_service.SearchService(
				self._settings, self._cache,
			)
		)
		self._scrape_svc = (
			moviemanager.api.scrape_service.ScrapeService(
				self._settings, self._cache,
				search_service=self._search_svc,
			)
		)
		# look up download providers from the registry pipeline
		_Cap = moviemanager.scraper.interfaces.ProviderCapability
		_pipeline = self._registry.create_pipeline(self._settings)
		_trailer_prov = _pipeline.get_for_capability(_Cap.TRAILER)
		_subtitle_prov = _pipeline.get_for_capability(_Cap.SUBTITLES)
		self._trailer_svc = (
			moviemanager.api.trailer_service.TrailerService(
				provider=_trailer_prov,
			)
		)
		self._artwork_svc = (
			moviemanager.api.artwork_service.ArtworkService(
				self._settings,
			)
		)
		self._subtitle_svc = (
			moviemanager.api.subtitle_service.SubtitleService(
				self._settings,
				provider=_subtitle_prov,
			)
		)

	#============================================
	# -- scraper and transport lifecycle (stays in MovieAPI) --
	#============================================

	#============================================
	def shutdown(self) -> None:
		"""Clean up resources for a clean exit.

		Logs out from subtitle service first (after task pool is
		drained), then shuts down the IMDB browser transport so
		QWebEnginePage is deleted before its QWebEngineProfile,
		preventing the segfault on application exit.
		"""
		# subtitle logout before transport teardown
		self._subtitle_svc.shutdown()
		if self._imdb_transport is not None:
			self._imdb_transport.shutdown()
			self._imdb_transport = None

	#============================================
	def _ensure_imdb_transport(self) -> None:
		"""Create the IMDB browser transport if not already created.

		The transport uses QWebEnginePage to load IMDB pages, solving
		WAF JavaScript challenges automatically via the Chromium engine.
		Must be called from the Qt main thread.

		Silently skips creation when no Qt application is running
		(e.g. in CLI mode or tests). The IMDB scraper still works
		for search via the CDN suggestion API without the transport.
		"""
		if self._imdb_transport is not None:
			return
		try:
			import moviemanager.ui.imdb_browser_transport
			self._imdb_transport = (
				moviemanager.ui.imdb_browser_transport
				.ImdbBrowserTransport()
			)
		except Exception as err:
			_LOG.warning(
				"Could not create IMDB browser transport "
				"(Qt app may not be running): %s", err,
			)

	#============================================
	def get_imdb_transport(self):
		"""Return the IMDB browser transport, creating if needed.

		Returns:
			ImdbBrowserTransport or None: The transport instance.
		"""
		self._ensure_imdb_transport()
		return self._imdb_transport

	#============================================
	def _ensure_scraper(self) -> None:
		"""Create the scraper, preferring TMDB when API key exists.

		Uses the scraper registry to discover and create providers.
		TMDB is used for search and metadata when a TMDB API key is
		configured, with IMDB as a supplement for parental guide data.
		Falls back to IMDB-only when no TMDB key is available.

		Transport creation is lazy -- the IMDB scraper works without
		a transport for search (uses CDN suggestion API). The transport
		is only needed for metadata and parental guide page loads,
		and is injected when first needed via
		_ensure_imdb_transport_on_scraper().
		"""
		if self._scraper is not None:
			return
		# use registry pipeline to select providers
		pipeline = self._registry.create_pipeline(self._settings)
		if pipeline.primary is not None:
			self._scraper = pipeline.primary
			# check for parental guide supplement provider
			if pipeline.supplements:
				for supp in pipeline.supplements:
					if isinstance(
						supp,
						moviemanager.scraper.interfaces
						.ParentalGuideProvider,
					):
						self._imdb_scraper = supp
						break
			return
		# fallback: IMDB only (no TMDB key) -- create directly
		self._scraper = self._registry.create_provider(
			"imdb", self._settings
		)

	#============================================
	def _ensure_imdb_transport_on_scraper(self) -> None:
		"""Lazily create transport and inject into IMDB scrapers.

		Called just before a transport-requiring operation (metadata
		or parental guide fetch). Creates the transport only once,
		then injects it into any IMDB scrapers that need it.
		"""
		self._ensure_imdb_transport()
		if self._imdb_transport is None:
			return
		# inject transport into scrapers that support it
		if hasattr(self._scraper, "set_transport"):
			self._scraper.set_transport(self._imdb_transport)
		if (self._imdb_scraper is not None
				and hasattr(self._imdb_scraper, "set_transport")):
			self._imdb_scraper.set_transport(
				self._imdb_transport
			)

	#============================================
	def _configured_imdb_browser_cookie_spec(self) -> str:
		"""Return cookie loader spec from structured settings."""
		if self._settings.imdb_browser_cookies_enabled:
			browser = (
				self._settings
				.imdb_browser_cookies_browser.strip().lower()
			)
			if not browser:
				browser = "firefox"
			return browser
		return ""

	#============================================
	def get_configured_imdb_browser_cookies(self) -> list:
		"""Load IMDB browser cookies from current settings.

		Returns:
			list: Cookie dicts, or empty list when disabled/unavailable.
		"""
		spec = self._configured_imdb_browser_cookie_spec()
		if not spec:
			return []
		try:
			cookies = (
				moviemanager.scraper.browser_cookies
				.load_imdb_cookies_from_browser(spec)
			)
			return cookies
		except Exception as error:
			_LOG.warning(
				"Failed to load IMDB browser cookies "
				"from '%s': %s",
				spec, error,
			)
			return []

	#============================================
	def _apply_configured_imdb_browser_cookies(self) -> None:
		"""No-op. Cookies are now managed by the browser transport.

		Kept for backward compatibility. The QWebEnginePage transport
		handles cookies automatically via its persistent profile.
		"""

	#============================================
	def apply_imdb_cookies(self, cookies: list) -> bool:
		"""Apply browser cookies to the active IMDB scraper sessions.

		Applies cookies to both the primary scraper (if IMDB) and
		the IMDB supplement scraper used for parental guide data.

		Args:
			cookies: List of cookie dicts from a browser context.

		Returns:
			bool: True when cookies were applied to at least one scraper.
		"""
		self._ensure_scraper()
		applied = False
		# apply to primary scraper if it supports transport
		if hasattr(self._scraper, "set_transport"):
			applied = True
		# apply to supplement scraper if active and supports transport
		if (self._imdb_scraper is not None
				and hasattr(self._imdb_scraper, "set_transport")):
			applied = True
		return applied

	#============================================
	# -- delegating public methods --
	#============================================

	#============================================
	def scan_directory(
		self, root_path: str, progress_callback=None,
		movie_callback=None,
	) -> list:
		"""Scan a directory for movie files and add them to the library.

		Args:
			root_path: Root directory path to scan.
			progress_callback: Optional callable(current, message).
			movie_callback: Optional callable(movie) for delivery.

		Returns:
			List of Movie instances discovered during the scan.
		"""
		result = self._scan_svc.scan_directory(
			root_path, progress_callback=progress_callback,
			movie_callback=movie_callback,
		)
		return result

	#============================================
	def get_movies(self) -> list:
		"""Return all movies in the library.

		Returns:
			List of all Movie instances.
		"""
		result = self._scan_svc.get_movies()
		return result

	#============================================
	def get_unscraped(self) -> list:
		"""Return movies that have not been scraped.

		Returns:
			List of unscraped Movie instances.
		"""
		result = self._scan_svc.get_unscraped()
		return result

	#============================================
	def get_movie_count(self) -> int:
		"""Return the total number of movies in the library.

		Returns:
			Integer count of movies.
		"""
		result = self._scan_svc.get_movie_count()
		return result

	#============================================
	def get_scraped_count(self) -> int:
		"""Return the number of scraped movies.

		Returns:
			Integer count of scraped movies.
		"""
		result = self._scan_svc.get_scraped_count()
		return result

	#============================================
	def get_unscraped_count(self) -> int:
		"""Return the number of unscraped movies.

		Returns:
			Integer count of unscraped movies.
		"""
		result = self._scan_svc.get_unscraped_count()
		return result

	#============================================
	def search_movie(
		self, title: str, year: str = "",
		query_title: str = "", query_year: str = "",
		query_runtime: int = 0,
	) -> list:
		"""Search for movie metadata by title.

		Computes match confidence for each result and sorts
		by confidence descending so the best match is first.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.
			query_title: Original title for scoring (defaults to title).
			query_year: Original year for scoring (defaults to year).
			query_runtime: Runtime in minutes (0 if unknown).

		Returns:
			List of SearchResult instances sorted by match confidence.
		"""
		self._ensure_scraper()
		result = self._search_svc.search_movie(
			self._scraper, title, year,
			query_title=query_title, query_year=query_year,
			query_runtime=query_runtime,
		)
		return result

	#============================================
	def search_movie_with_fallback(
		self, title: str, year: str = "",
		query_runtime: int = 0,
	) -> tuple:
		"""Search with fallback strategies when initial search fails.

		Tries progressively broader searches:
		1. title + year (exact)
		2. title only (drop year)
		3. simplified title (remove parenthetical text, articles)

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.
			query_runtime: Runtime in minutes (0 if unknown).

		Returns:
			tuple: (results list, strategy description string).
		"""
		self._ensure_scraper()
		result = self._search_svc.search_movie_with_fallback(
			self._scraper, title, year,
			query_runtime=query_runtime,
		)
		return result

	#============================================
	@staticmethod
	def compute_match_confidence(
		query_title: str, query_year: str,
		result_title: str, result_year: str,
	) -> float:
		"""Compute confidence score for a search result match.

		Delegates to the API-agnostic match_confidence module.

		Args:
			query_title: Original movie title from the library.
			query_year: Original movie year from the library.
			result_title: Title from the search result.
			result_year: Year from the search result.

		Returns:
			float: Confidence score from 0.0 to 1.0.
		"""
		score = (
			moviemanager.api.match_confidence
			.compute_match_confidence(
				query_title, query_year,
				result_title, result_year,
			)
		)
		return score

	#============================================
	def scrape_movie(
		self, movie, tmdb_id: int = 0, imdb_id: str = "",
		bypass_cache: bool = False,
	) -> None:
		"""Fetch and apply metadata to a movie from the active scraper.

		Maps MediaMetadata fields onto the Movie object, marks it
		as scraped, and writes a Kodi-format NFO file.

		Args:
			movie: Movie instance to update with scraped metadata.
			tmdb_id: TMDB ID to fetch metadata for.
			imdb_id: IMDB ID to fetch metadata for.
			bypass_cache: Skip cache lookup and force fresh fetch.
		"""
		self._ensure_scraper()
		self._scrape_svc.scrape_movie(
			movie, self._scraper,
			imdb_scraper=self._imdb_scraper,
			ensure_transport_fn=self._ensure_imdb_transport_on_scraper,
			tmdb_id=tmdb_id, imdb_id=imdb_id,
			bypass_cache=bypass_cache,
		)

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
			# build template with media tokens from checkbox settings
			file_template = (
				moviemanager.core.movie.template_engine
				.build_file_template(self._settings)
			)
		result = moviemanager.core.movie.rename_service.rename_movie(
			movie, path_template, file_template, dry_run=dry_run,
			spaces_to_underscores=(
				self._settings.spaces_to_underscores
			),
		)
		return result

	#============================================
	def download_artwork(self, movie) -> list:
		"""Download artwork files for a movie.

		Downloads poster and fanart images to the movie directory
		based on settings and available URLs.

		Args:
			movie: Movie instance with artwork URLs.

		Returns:
			list: Paths of downloaded artwork files.
		"""
		result = self._artwork_svc.download_artwork(movie)
		return result

	#============================================
	def download_trailer(self, movie) -> str:
		"""Download a movie trailer using yt-dlp.

		Args:
			movie: Movie instance with trailer_url set.

		Returns:
			str: Path to downloaded trailer file.

		Raises:
			DownloadError: With category describing the failure reason.
		"""
		result = self._trailer_svc.download_trailer(movie)
		return result

	#============================================
	def download_subtitles(
		self, movie, languages: str = "en",
	) -> list:
		"""Download subtitles for a movie from OpenSubtitles.

		Args:
			movie: Movie instance with imdb_id set.
			languages: Comma-separated language codes.

		Returns:
			list: Paths of downloaded subtitle files.

		Raises:
			DownloadError: With category describing the failure reason.
		"""
		result = self._subtitle_svc.download_subtitles(
			movie, languages
		)
		return result

	#============================================
	def fetch_parental_guides(
		self, movies: list, progress_callback=None,
	) -> dict:
		"""Fetch parental guide data for movies missing it.

		Filters to movies with imdb_id that either have no guide data
		and have not been checked, or were checked over 90 days ago.

		Args:
			movies: List of Movie instances to check.
			progress_callback: Optional callable(current, total, message).

		Returns:
			Dict with fetched, no_data, failed, skipped counts.
		"""
		self._ensure_scraper()
		result = self._scrape_svc.fetch_parental_guides(
			movies, self._scraper,
			imdb_scraper=self._imdb_scraper,
			ensure_transport_fn=(
				self._ensure_imdb_transport_on_scraper
			),
			progress_callback=progress_callback,
		)
		return result

	#============================================
	def has_failed_parental_guides(self) -> bool:
		"""Return True if there are parental guide fetches to retry.

		Returns:
			bool: True when at least one fetch failed.
		"""
		result = self._scrape_svc.has_failed_parental_guides()
		return result

	#============================================
	def clear_failed_parental_guides(self) -> None:
		"""Clear the list of failed parental guide fetches."""
		self._scrape_svc.clear_failed_parental_guides()

	#============================================
	def retry_failed_parental_guides(self) -> dict:
		"""Retry previously failed parental guide fetches.

		Iterates the failed list with a delay between requests to
		allow WAF immunity cookies to propagate. On success, updates
		the movie object and caches the result.

		Returns:
			Dict with retried, succeeded, and still_failed counts.
		"""
		self._ensure_scraper()
		result = self._scrape_svc.retry_failed_parental_guides(
			self._imdb_scraper,
			ensure_transport_fn=(
				self._ensure_imdb_transport_on_scraper
			),
		)
		return result

	#============================================
	# -- backward compatibility: _failed_parental_guides access --
	#============================================

	@property
	def _failed_parental_guides(self) -> list:
		"""Provide backward-compatible access to scrape service failures.

		main_window.py accesses this attribute directly for counting.
		"""
		return self._scrape_svc._failed_parental_guides
