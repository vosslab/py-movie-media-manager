"""Movie metadata scraping service with cache and parental guide support."""

# Standard Library
import os
import time
import random
import datetime
import logging

# local repo modules
import moviemanager.api.api_cache
import moviemanager.core.nfo.writer
import moviemanager.core.settings
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.interfaces
import moviemanager.scraper.types


# module logger
_LOG = logging.getLogger(__name__)

# number of days before re-checking a movie with no parental guide
_PARENTAL_GUIDE_RECHECK_DAYS = 90


#============================================
class ScrapeService:
	"""Fetch and apply metadata from scraper providers.

	Handles cache hits, IMDB supplement for parental guides,
	metadata-to-movie mapping, and NFO writing. Tracks failed
	parental guide fetches for deferred retry.
	"""

	#============================================
	def __init__(
		self,
		settings: moviemanager.core.settings.Settings,
		cache: moviemanager.api.api_cache.ApiCache,
		search_service=None,
	):
		"""Initialize the scrape service.

		Args:
			settings: Application settings.
			cache: Shared API cache instance.
			search_service: SearchService for TMDB poster lookups.
		"""
		self._settings = settings
		self._cache = cache
		self._search_service = search_service
		# track failed parental guide fetches for deferred retry
		self._failed_parental_guides = []

	#============================================
	def scrape_movie(
		self, movie, scraper, imdb_scraper=None,
		ensure_transport_fn=None,
		tmdb_id: int = 0, imdb_id: str = "",
		bypass_cache: bool = False,
	) -> None:
		"""Fetch and apply metadata to a movie from the active scraper.

		Maps MediaMetadata fields onto the Movie object, marks it
		as scraped, and writes a Kodi-format NFO file.

		Args:
			movie: Movie instance to update with scraped metadata.
			scraper: Active scraper instance (TMDB or IMDB).
			imdb_scraper: Optional IMDB supplement scraper for parental guide.
			ensure_transport_fn: Callable to lazily create IMDB transport.
			tmdb_id: TMDB ID to fetch metadata for.
			imdb_id: IMDB ID to fetch metadata for.
			bypass_cache: Skip cache lookup and force fresh fetch.
		"""
		is_imdb = isinstance(
			scraper,
			moviemanager.scraper.imdb_scraper.ImdbScraper,
		)
		cache_type = "imdb_metadata" if is_imdb else "tmdb_metadata"
		# use imdb_id as the key for both scrapers
		cache_key = imdb_id
		# check persistent cache (skip when refreshing)
		cached_dict = None
		if not bypass_cache and cache_key:
			cached_dict = self._cache.get_metadata(
				cache_type, cache_key
			)
		if cached_dict is not None:
			# reconstruct CastMember lists from nested dicts
			actors_raw = cached_dict.pop("actors", [])
			producers_raw = cached_dict.pop("producers", [])
			metadata = moviemanager.scraper.types.MediaMetadata(
				**cached_dict
			)
			metadata.actors = [
				moviemanager.scraper.types.CastMember(**a)
				for a in actors_raw
			]
			metadata.producers = [
				moviemanager.scraper.types.CastMember(**p)
				for p in producers_raw
			]
		else:
			# ensure transport is ready for IMDB page loads
			if is_imdb and ensure_transport_fn:
				ensure_transport_fn()
			metadata = scraper.get_metadata(
				tmdb_id=tmdb_id, imdb_id=imdb_id
			)
			if is_imdb and self._search_service:
				lookup_id = metadata.imdb_id or imdb_id
				tmdb_match_id, tmdb_poster_url = (
					self._search_service
					._lookup_tmdb_poster_for_imdb_id(lookup_id)
				)
				if tmdb_match_id and not metadata.tmdb_id:
					metadata.tmdb_id = tmdb_match_id
				if tmdb_poster_url:
					metadata.poster_url = tmdb_poster_url
			# only cache metadata with meaningful content
			store_key = metadata.imdb_id or imdb_id
			if store_key and (metadata.title or metadata.imdb_id):
				self._cache.put_metadata(
					cache_type, store_key, metadata,
				)
		# supplement parental guide from IMDB when using TMDB
		if (imdb_scraper is not None
				and (bypass_cache or not metadata.parental_guide)
				and metadata.imdb_id):
			self._fetch_parental_guide_supplement(
				movie, metadata, imdb_scraper,
				ensure_transport_fn, bypass_cache,
			)
		# map MediaMetadata fields to the Movie object
		_apply_metadata_to_movie(movie, metadata)
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
	def _fetch_parental_guide_supplement(
		self, movie, metadata, imdb_scraper,
		ensure_transport_fn, bypass_cache: bool,
	) -> None:
		"""Fetch parental guide from IMDB supplement scraper.

		Args:
			movie: Movie instance for skip-check context.
			metadata: MediaMetadata to update with guide data.
			imdb_scraper: IMDB scraper with parental guide capability.
			ensure_transport_fn: Callable to create transport lazily.
			bypass_cache: Skip cache lookup when True.
		"""
		# skip if confirmed empty and checked within 90 days
		skip_guide = _should_skip_parental_guide(
			movie, metadata.parental_guide,
		)
		if skip_guide and not bypass_cache:
			_LOG.debug(
				"Skipping parental guide for %s"
				" (checked %s)", metadata.imdb_id,
				movie.parental_guide_checked,
			)
			return
		# check parental guide cache first (skip when refreshing)
		cached_guide = None
		if not bypass_cache:
			cached_guide = self._cache.get_parental_guide(
				metadata.imdb_id
			)
		if cached_guide is not None:
			metadata.parental_guide = cached_guide
			# mark checked date on cache hit
			today = datetime.date.today().isoformat()
			metadata.parental_guide_checked = today
			return
		# ensure transport is ready for parental guide page
		if ensure_transport_fn:
			ensure_transport_fn()
		try:
			guide = imdb_scraper.get_parental_guide(
				metadata.imdb_id
			)
			metadata.parental_guide = guide
			# mark checked whether empty or populated
			today = datetime.date.today().isoformat()
			metadata.parental_guide_checked = today
			# only cache non-empty parental guide results
			if guide:
				self._cache.put_parental_guide(
					metadata.imdb_id, guide
				)
		except Exception as err:
			_LOG.warning(
				"IMDB parental guide fetch failed: %s", err,
			)
			# record for deferred retry later
			self._failed_parental_guides.append(
				(metadata.imdb_id, movie)
			)

	#============================================
	def fetch_parental_guides(
		self, movies: list, scraper, imdb_scraper=None,
		ensure_transport_fn=None, progress_callback=None,
	) -> dict:
		"""Fetch parental guide data for movies missing it.

		Filters to movies with imdb_id that either have no guide data
		and have not been checked, or were checked over 90 days ago.

		Args:
			movies: List of Movie instances to check.
			scraper: Active scraper instance.
			imdb_scraper: Optional IMDB supplement scraper.
			ensure_transport_fn: Callable to create transport lazily.
			progress_callback: Optional callable(current, total, message).

		Returns:
			Dict with fetched, no_data, failed, skipped counts.
		"""
		if ensure_transport_fn:
			ensure_transport_fn()
		# determine which scraper to use for parental guide
		guide_scraper = imdb_scraper or scraper
		if not isinstance(
			guide_scraper,
			moviemanager.scraper.interfaces.ParentalGuideProvider,
		):
			_LOG.warning(
				"No parental guide provider available"
			)
			result = {
				"fetched": 0, "no_data": 0,
				"failed": 0, "skipped": len(movies),
			}
			return result
		# filter to eligible movies
		eligible = []
		skipped = 0
		for movie in movies:
			if not movie.imdb_id:
				skipped += 1
				continue
			# already has parental guide data
			if movie.parental_guide:
				skipped += 1
				continue
			# skip if checked recently (within 90 days)
			if _should_skip_parental_guide(
				movie, movie.parental_guide
			):
				skipped += 1
				continue
			eligible.append(movie)
		fetched = 0
		no_data = 0
		failed = 0
		total = len(eligible)
		for i, movie in enumerate(eligible):
			# build progress message with running tally
			stats_parts = []
			if fetched:
				stats_parts.append(f"{fetched} fetched")
			if failed:
				stats_parts.append(f"{failed} failed")
			stats_suffix = ""
			if stats_parts:
				stats_suffix = " - " + ", ".join(stats_parts)
			if progress_callback:
				progress_msg = (
					f"Parental guide: {movie.title}"
					f" ({i + 1}/{total}){stats_suffix}"
				)
				progress_callback(i, total, progress_msg)
			# delay between requests
			time.sleep(1 + random.random())
			# check cache first
			cached_guide = self._cache.get_parental_guide(
				movie.imdb_id
			)
			if cached_guide is not None:
				movie.parental_guide = cached_guide
				movie.parental_guide_checked = (
					datetime.date.today().isoformat()
				)
				fetched += 1
				_LOG.info(
					"Parental guide cached for %s (%d/%d)"
					" - %d fetched, %d failed",
					movie.imdb_id, i + 1, total,
					fetched, failed,
				)
				# write updated NFO
				if movie.nfo_path:
					moviemanager.core.nfo.writer.write_nfo(
						movie, movie.nfo_path
					)
				continue
			try:
				guide = guide_scraper.get_parental_guide(
					movie.imdb_id
				)
				today = datetime.date.today().isoformat()
				movie.parental_guide_checked = today
				if guide:
					movie.parental_guide = guide
					self._cache.put_parental_guide(
						movie.imdb_id, guide
					)
					fetched += 1
					_LOG.info(
						"Parental guide fetched for %s (%d/%d)"
						" - %d fetched, %d failed",
						movie.imdb_id, i + 1, total,
						fetched, failed,
					)
				else:
					# confirmed no data on IMDB
					no_data += 1
					_LOG.info(
						"Parental guide empty for %s (%d/%d)"
						" - %d no_data, %d failed",
						movie.imdb_id, i + 1, total,
						no_data, failed,
					)
				# write updated NFO
				if movie.nfo_path:
					moviemanager.core.nfo.writer.write_nfo(
						movie, movie.nfo_path
					)
			except Exception as err:
				failed += 1
				_LOG.warning(
					"Parental guide failed for %s (%d/%d)"
					" - %d fetched, %d failed: %s",
					movie.imdb_id, i + 1, total,
					fetched, failed, err,
				)
		result = {
			"fetched": fetched, "no_data": no_data,
			"failed": failed, "skipped": skipped,
		}
		return result

	#============================================
	def has_failed_parental_guides(self) -> bool:
		"""Return True if there are parental guide fetches to retry.

		Returns:
			bool: True when at least one fetch failed.
		"""
		has_failures = len(self._failed_parental_guides) > 0
		return has_failures

	#============================================
	def clear_failed_parental_guides(self) -> None:
		"""Clear the list of failed parental guide fetches."""
		self._failed_parental_guides.clear()

	#============================================
	def retry_failed_parental_guides(
		self, imdb_scraper, ensure_transport_fn=None,
	) -> dict:
		"""Retry previously failed parental guide fetches.

		Iterates the failed list with a delay between requests to
		allow WAF immunity cookies to propagate. On success, updates
		the movie object and caches the result.

		Args:
			imdb_scraper: IMDB scraper for parental guide fetching.
			ensure_transport_fn: Callable to create transport lazily.

		Returns:
			Dict with retried, succeeded, and still_failed counts.
		"""
		if ensure_transport_fn:
			ensure_transport_fn()
		failures = list(self._failed_parental_guides)
		self._failed_parental_guides.clear()
		succeeded = 0
		still_failed = []
		for imdb_id, movie in failures:
			# delay between retries to avoid overloading IMDB
			time.sleep(1 + random.random())
			try:
				guide = imdb_scraper.get_parental_guide(imdb_id)
				movie.parental_guide = guide
				if guide:
					self._cache.put_parental_guide(imdb_id, guide)
				succeeded += 1
			except Exception as err:
				_LOG.warning(
					"Parental guide retry failed for %s: %s",
					imdb_id, err,
				)
				still_failed.append(imdb_id)
		result = {
			"retried": len(failures),
			"succeeded": succeeded,
			"still_failed": still_failed,
		}
		return result


#============================================
def _should_skip_parental_guide(movie, current_guide: dict) -> bool:
	"""Return True if parental guide fetch should be skipped.

	Skips when the movie has no guide data but was checked within
	the recheck window (90 days).

	Args:
		movie: Movie instance with parental_guide_checked field.
		current_guide: Current parental guide dict (from metadata).

	Returns:
		True if the fetch should be skipped.
	"""
	# if guide already has data, no need to skip
	if current_guide:
		return False
	# if never checked, do not skip
	if not movie.parental_guide_checked:
		return False
	# parse the checked date and compare to today
	checked_date = datetime.date.fromisoformat(
		movie.parental_guide_checked
	)
	days_since = (datetime.date.today() - checked_date).days
	should_skip = days_since < _PARENTAL_GUIDE_RECHECK_DAYS
	return should_skip


#============================================
def _apply_metadata_to_movie(movie, metadata) -> None:
	"""Map MediaMetadata fields onto a Movie object.

	Args:
		movie: Movie instance to update.
		metadata: MediaMetadata with fetched values.
	"""
	movie.title = metadata.title or movie.title
	movie.original_title = (
		metadata.original_title or movie.original_title
	)
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
	# only update checked date if it was set during this scrape
	if metadata.parental_guide_checked:
		movie.parental_guide_checked = (
			metadata.parental_guide_checked
		)
	# convert CastMember dataclasses to dicts for NFO writer
	movie.actors = [
		{"name": a.name, "role": a.role, "tmdb_id": a.tmdb_id}
		for a in metadata.actors
	]
	movie.scraped = True
