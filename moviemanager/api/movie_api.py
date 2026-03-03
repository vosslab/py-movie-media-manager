"""Facade providing all movie operations for CLI and GUI."""

# Standard Library
import os
import re
import time
import random
import subprocess
import logging

# PIP3 modules
import requests

# local repo modules
import moviemanager.api.api_cache
import moviemanager.api.match_confidence
import moviemanager.core.movie.movie_list
import moviemanager.core.movie.renamer
import moviemanager.core.movie.scanner
import moviemanager.core.nfo.writer
import moviemanager.core.settings
import moviemanager.scraper.browser_cookies
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.tmdb_scraper


# module logger
_LOG = logging.getLogger(__name__)
_TMDB_POSTER_PREFETCH_LIMIT = 3


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
		self._cache = moviemanager.api.api_cache.ApiCache()
		self._scraper = None
		self._imdb_scraper = None
		self._imdb_cookies_loaded_spec = ""
		self._tmdb_lookup_scraper = None
		self._tmdb_lookup_spec = ""
		self._tmdb_poster_cache = {}

	#============================================
	def scan_directory(self, root_path: str, progress_callback=None) -> list:
		"""Scan a directory for movie files and add them to the library.

		Args:
			root_path: Root directory path to scan.
			progress_callback: Optional callable(current, message) for progress.

		Returns:
			List of Movie instances discovered during the scan.
		"""
		movies = moviemanager.core.movie.scanner.scan_directory(
			root_path, progress_callback=progress_callback
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
	def _ensure_scraper(self) -> None:
		"""Create the scraper, preferring TMDB when API key exists.

		Uses TMDB for search and metadata when a TMDB API key is
		configured, with IMDB as a supplement for parental guide data.
		Falls back to IMDB-only when no TMDB key is available.
		"""
		if self._scraper is not None:
			self._apply_configured_imdb_browser_cookies()
			return
		# auto-detect: use TMDB when API key exists
		api_key = self._settings.tmdb_api_key
		if api_key:
			self._scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(
				api_key=api_key,
				language=self._settings.scrape_language,
			)
			# IMDB supplement for parental guide data
			self._imdb_scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
			self._apply_configured_imdb_browser_cookies()
			return
		# fallback: IMDB only (no TMDB key)
		self._scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		self._apply_configured_imdb_browser_cookies()

	#============================================
	def _configured_imdb_browser_cookie_spec(self) -> str:
		"""Return cookie loader spec from structured settings."""
		if self._settings.imdb_browser_cookies_enabled:
			browser = (
				self._settings.imdb_browser_cookies_browser.strip().lower()
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
			return moviemanager.scraper.browser_cookies.load_imdb_cookies_from_browser(
				spec
			)
		except Exception as error:
			_LOG.warning(
				"Failed to load IMDB browser cookies from '%s': %s",
				spec, error,
			)
			return []

	#============================================
	def _apply_configured_imdb_browser_cookies(self) -> None:
		"""Load and apply browser cookies to IMDB scrapers, if configured."""
		spec = self._configured_imdb_browser_cookie_spec()
		if not spec:
			return
		if spec == self._imdb_cookies_loaded_spec:
			return
		cookies = self.get_configured_imdb_browser_cookies()
		if not cookies:
			_LOG.warning(
				"No IMDB cookies found from browser spec: %s", spec
			)
			return
		# apply to primary scraper if it is an IMDB scraper
		if isinstance(
			self._scraper, moviemanager.scraper.imdb_scraper.ImdbScraper
		):
			self._scraper.set_cookies(cookies)
		# also apply to IMDB supplement scraper if active
		if (self._imdb_scraper is not None
				and isinstance(self._imdb_scraper,
					moviemanager.scraper.imdb_scraper.ImdbScraper)):
			self._imdb_scraper.set_cookies(cookies)
		self._imdb_cookies_loaded_spec = spec

	#============================================
	def _get_tmdb_lookup_scraper(self):
		"""Return a TMDB scraper for poster lookup, or None if disabled."""
		api_key = self._settings.tmdb_api_key.strip()
		if not api_key:
			return None
		spec = f"{api_key}|{self._settings.scrape_language}"
		if (
			self._tmdb_lookup_scraper is not None
			and self._tmdb_lookup_spec == spec
		):
			return self._tmdb_lookup_scraper
		self._tmdb_lookup_scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(
			api_key=api_key,
			language=self._settings.scrape_language,
		)
		self._tmdb_lookup_spec = spec
		self._tmdb_poster_cache = {}
		return self._tmdb_lookup_scraper

	#============================================
	def _lookup_tmdb_poster_for_imdb_id(self, imdb_id: str) -> tuple:
		"""Resolve TMDB id/poster URL for an IMDB id with persistent caching."""
		if not imdb_id:
			return (0, "")
		# check in-memory cache first, then persistent cache
		if imdb_id in self._tmdb_poster_cache:
			return self._tmdb_poster_cache[imdb_id]
		cached = self._cache.get_poster_lookup(imdb_id)
		if cached is not None:
			self._tmdb_poster_cache[imdb_id] = cached
			return cached
		lookup_scraper = self._get_tmdb_lookup_scraper()
		if lookup_scraper is None:
			self._tmdb_poster_cache[imdb_id] = (0, "")
			return (0, "")
		try:
			tmdb_id, poster_url = lookup_scraper.find_by_imdb_id(imdb_id)
		except Exception as error:
			_LOG.warning(
				"TMDB poster lookup failed for %s: %s",
				imdb_id, error,
			)
			tmdb_id = 0
			poster_url = ""
		result = (tmdb_id, poster_url)
		self._tmdb_poster_cache[imdb_id] = result
		# persist to disk cache
		self._cache.put_poster_lookup(imdb_id, tmdb_id, poster_url)
		return result

	#============================================
	def _prefer_tmdb_poster(self, result) -> None:
		"""Mutate a SearchResult in-place to prefer TMDB poster URL."""
		if not result or not result.imdb_id:
			return
		tmdb_id, poster_url = self._lookup_tmdb_poster_for_imdb_id(
			result.imdb_id
		)
		if tmdb_id and not result.tmdb_id:
			result.tmdb_id = tmdb_id
		if poster_url:
			result.poster_url = poster_url

	#============================================
	def search_movie(
		self, title: str, year: str = "",
		query_title: str = "", query_year: str = "",
	) -> list:
		"""Search for movie metadata by title.

		Computes match confidence for each result and sorts
		by confidence descending so the best match is first.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.
			query_title: Original title for scoring (defaults to title).
			query_year: Original year for scoring (defaults to year).

		Returns:
			List of SearchResult instances sorted by match confidence.
		"""
		self._ensure_scraper()
		# determine cache type based on active scraper
		is_imdb = isinstance(
			self._scraper, moviemanager.scraper.imdb_scraper.ImdbScraper
		)
		cache_type = "imdb_search" if is_imdb else "tmdb_search"
		# check persistent cache before network call
		cached_dicts = self._cache.get_search_results(
			cache_type, title, year
		)
		if cached_dicts is not None:
			# reconstruct SearchResult dataclasses from cached dicts
			results = [
				moviemanager.scraper.types.SearchResult(**d)
				for d in cached_dicts
			]
		else:
			results = self._scraper.search(title, year)
			if is_imdb:
				prefetch_results = results[:_TMDB_POSTER_PREFETCH_LIMIT]
				for item in prefetch_results:
					self._prefer_tmdb_poster(item)
			# store in persistent cache
			self._cache.put_search_results(
				cache_type, title, year, results
			)
		# compute match confidence for each result
		ref_title = query_title or title
		ref_year = query_year or year
		for r in results:
			r.match_confidence = (
				moviemanager.api.match_confidence.compute_match_confidence(
					ref_title, ref_year,
					r.title, r.year,
					result_original_title=r.original_title,
					result_score=r.score,
				)
			)
		# sort by confidence descending (best match first)
		results.sort(
			key=lambda r: r.match_confidence, reverse=True
		)
		return results

	#============================================
	def apply_imdb_cookies(self, cookies: list) -> bool:
		"""Apply browser cookies to the active IMDB scraper session.

		Args:
			cookies: List of cookie dicts from a browser context.

		Returns:
			bool: True when cookies were applied to an IMDB scraper.
		"""
		self._ensure_scraper()
		if not isinstance(
			self._scraper, moviemanager.scraper.imdb_scraper.ImdbScraper
		):
			return False
		self._scraper.set_cookies(cookies)
		return True

	#============================================
	def search_movie_with_fallback(
		self, title: str, year: str = ""
	) -> tuple:
		"""Search with fallback strategies when initial search fails.

		Tries progressively broader searches:
		1. title + year (exact)
		2. title only (drop year)
		3. simplified title (remove parenthetical text, articles)

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			tuple: (results list, strategy description string).
		"""
		# strategy 1: title + year
		if year:
			results = self.search_movie(title, year)
			if results:
				strategy = f"title + year: {title} ({year})"
				return (results, strategy)
			# strategy 2: title only (drop year)
			results = self.search_movie(title)
			if results:
				strategy = f"title only: {title}"
				return (results, strategy)
		else:
			results = self.search_movie(title)
			if results:
				strategy = f"title: {title}"
				return (results, strategy)
		# strategy 3: simplified title
		simplified = _simplify_title(title)
		if simplified != title.lower().strip():
			results = self.search_movie(simplified)
			if results:
				strategy = f"simplified: {simplified}"
				return (results, strategy)
		# nothing found
		return ([], "no results")

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
		score = moviemanager.api.match_confidence.compute_match_confidence(
			query_title, query_year,
			result_title, result_year,
		)
		return score

	#============================================
	def scrape_movie(self, movie, tmdb_id: int = 0, imdb_id: str = "") -> None:
		"""Fetch and apply metadata to a movie from the active scraper.

		Maps MediaMetadata fields onto the Movie object, marks it
		as scraped, and writes a Kodi-format NFO file.

		Args:
			movie: Movie instance to update with scraped metadata.
			tmdb_id: TMDB ID to fetch metadata for.
			imdb_id: IMDB ID to fetch metadata for.
		"""
		self._ensure_scraper()
		is_imdb = isinstance(
			self._scraper, moviemanager.scraper.imdb_scraper.ImdbScraper
		)
		cache_type = "imdb_metadata" if is_imdb else "tmdb_metadata"
		# use imdb_id as the key for both scrapers (TMDB returns imdb_id)
		cache_key = imdb_id
		# check persistent cache before network call
		cached_dict = self._cache.get_metadata(
			cache_type, cache_key
		) if cache_key else None
		if cached_dict is not None:
			# reconstruct CastMember lists from nested dicts
			actors_raw = cached_dict.pop("actors", [])
			producers_raw = cached_dict.pop("producers", [])
			metadata = moviemanager.scraper.types.MediaMetadata(**cached_dict)
			metadata.actors = [
				moviemanager.scraper.types.CastMember(**a) for a in actors_raw
			]
			metadata.producers = [
				moviemanager.scraper.types.CastMember(**p) for p in producers_raw
			]
		else:
			metadata = self._scraper.get_metadata(
				tmdb_id=tmdb_id, imdb_id=imdb_id
			)
			if is_imdb:
				lookup_id = metadata.imdb_id or imdb_id
				tmdb_match_id, tmdb_poster_url = (
					self._lookup_tmdb_poster_for_imdb_id(lookup_id)
				)
				if tmdb_match_id and not metadata.tmdb_id:
					metadata.tmdb_id = tmdb_match_id
				if tmdb_poster_url:
					metadata.poster_url = tmdb_poster_url
			# store in persistent cache keyed by imdb_id
			store_key = metadata.imdb_id or imdb_id
			if store_key:
				self._cache.put_metadata(
					cache_type, store_key, metadata,
				)
		# supplement parental guide from IMDB when using TMDB
		if (self._imdb_scraper is not None
				and not metadata.parental_guide
				and metadata.imdb_id):
			# check parental guide cache first
			cached_guide = self._cache.get_parental_guide(
				metadata.imdb_id
			)
			if cached_guide is not None:
				metadata.parental_guide = cached_guide
			else:
				try:
					guide = self._imdb_scraper.get_parental_guide(
						metadata.imdb_id
					)
					metadata.parental_guide = guide
					# cache the parental guide result
					self._cache.put_parental_guide(
						metadata.imdb_id, guide
					)
				except Exception as err:
					_LOG.warning(
						"IMDB parental guide fetch failed: %s", err
					)
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
		movie.trailer_url = metadata.trailer_url
		movie.parental_guide = metadata.parental_guide
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
	def download_artwork(self, movie) -> list:
		"""Download artwork files for a movie.

		Downloads poster and fanart images to the movie directory
		based on settings and available URLs.

		Args:
			movie: Movie instance with artwork URLs.

		Returns:
			list: Paths of downloaded artwork files.
		"""
		downloaded = []
		if not movie.path:
			return downloaded
		# download poster
		if self._settings.download_poster and movie.poster_url:
			poster_path = os.path.join(movie.path, "poster.jpg")
			if not os.path.exists(poster_path):
				time.sleep(random.random())
				response = requests.get(movie.poster_url, timeout=30)
				response.raise_for_status()
				with open(poster_path, "wb") as f:
					f.write(response.content)
				downloaded.append(poster_path)
		# download fanart
		if self._settings.download_fanart and movie.fanart_url:
			fanart_path = os.path.join(movie.path, "fanart.jpg")
			if not os.path.exists(fanart_path):
				time.sleep(random.random())
				response = requests.get(movie.fanart_url, timeout=30)
				response.raise_for_status()
				with open(fanart_path, "wb") as f:
					f.write(response.content)
				downloaded.append(fanart_path)
		return downloaded

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

	#============================================
	def download_trailer(self, movie) -> str:
		"""Download a movie trailer using yt-dlp.

		Args:
			movie: Movie instance with trailer_url set.

		Returns:
			str: Path to downloaded trailer file, or empty string.
		"""
		if not movie.trailer_url or not movie.path:
			return ""
		output_path = os.path.join(movie.path, "trailer.mp4")
		# skip if trailer already exists
		if os.path.exists(output_path):
			return output_path
		cmd = [
			"yt-dlp",
			"-o", output_path,
			"--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
			"--no-playlist",
			movie.trailer_url,
		]
		subprocess.run(cmd, check=True, timeout=300)
		return output_path

	#============================================
	def download_subtitles(self, movie, languages: str = "en") -> list:
		"""Download subtitles for a movie from OpenSubtitles.

		Args:
			movie: Movie instance with imdb_id set.
			languages: Comma-separated language codes.

		Returns:
			list: Paths of downloaded subtitle files.
		"""
		if not movie.imdb_id or not movie.path:
			return []
		api_key = self._settings.opensubtitles_api_key
		if not api_key:
			raise ValueError(
				"OpenSubtitles API key is not configured. "
				"Set it in Settings > API Keys."
			)
		import moviemanager.scraper.subtitle_scraper
		scraper = moviemanager.scraper.subtitle_scraper.SubtitleScraper(
			api_key
		)
		results = scraper.search(
			imdb_id=movie.imdb_id, languages=languages
		)
		if not results:
			return []
		# group by language, take best per language (highest download count)
		downloaded = []
		by_lang = {}
		for r in results:
			lang = r.get("language", "en")
			if lang not in by_lang:
				by_lang[lang] = r
			elif r.get("download_count", 0) > by_lang[lang].get("download_count", 0):
				by_lang[lang] = r
		for lang, best in by_lang.items():
			file_id = best.get("file_id", 0)
			if not file_id:
				continue
			# name subtitle file with language code
			srt_filename = f"subtitles.{lang}.srt"
			srt_path = os.path.join(movie.path, srt_filename)
			# skip if already exists
			if os.path.exists(srt_path):
				downloaded.append(srt_path)
				continue
			result_path = scraper.download(file_id, srt_path)
			if result_path:
				downloaded.append(result_path)
		return downloaded


#============================================
def _simplify_title(title: str) -> str:
	"""Simplify a movie title for broader search matching.

	Removes parenthetical text, leading articles, and extra whitespace.

	Args:
		title: Original movie title.

	Returns:
		str: Simplified title string.
	"""
	# remove parenthetical text like "(Extended Cut)" or "(2020)"
	simplified = re.sub(r"\s*\(.*?\)", "", title)
	# strip leading articles
	simplified = re.sub(r"^(The|A|An)\s+", "", simplified, flags=re.IGNORECASE)
	# collapse whitespace and strip
	simplified = re.sub(r"\s+", " ", simplified).strip()
	return simplified


# simple assertion for _simplify_title
assert _simplify_title("The Matrix (1999)") == "Matrix"
assert _simplify_title("A Beautiful Mind") == "Beautiful Mind"
assert _simplify_title("Clerks") == "Clerks"
