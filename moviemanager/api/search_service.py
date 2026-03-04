"""Movie search service with fallback strategies and match scoring."""

# Standard Library
import re
import logging

# local repo modules
import moviemanager.api.api_cache
import moviemanager.api.match_confidence
import moviemanager.core.settings
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.tmdb_scraper
import moviemanager.scraper.types


# module logger
_LOG = logging.getLogger(__name__)
_TMDB_POSTER_PREFETCH_LIMIT = 3


#============================================
class SearchService:
	"""Search for movies by title using the active scraper.

	Supports fallback search strategies (drop year, simplify title)
	and computes match confidence for each result. Caches search
	results and TMDB poster lookups.
	"""

	#============================================
	def __init__(
		self,
		settings: moviemanager.core.settings.Settings,
		cache: moviemanager.api.api_cache.ApiCache,
	):
		"""Initialize the search service.

		Args:
			settings: Application settings.
			cache: Shared API cache instance.
		"""
		self._settings = settings
		self._cache = cache
		self._tmdb_lookup_scraper = None
		self._tmdb_lookup_spec = ""
		self._tmdb_poster_cache = {}

	#============================================
	def _get_tmdb_lookup_scraper(self):
		"""Return a TMDB scraper for poster lookup, or None."""
		api_key = self._settings.tmdb_api_key.strip()
		if not api_key:
			return None
		spec = f"{api_key}|{self._settings.scrape_language}"
		if (
			self._tmdb_lookup_scraper is not None
			and self._tmdb_lookup_spec == spec
		):
			return self._tmdb_lookup_scraper
		self._tmdb_lookup_scraper = (
			moviemanager.scraper.tmdb_scraper.TmdbScraper(
				api_key=api_key,
				language=self._settings.scrape_language,
			)
		)
		self._tmdb_lookup_spec = spec
		self._tmdb_poster_cache = {}
		return self._tmdb_lookup_scraper

	#============================================
	def _lookup_tmdb_poster_for_imdb_id(
		self, imdb_id: str,
	) -> tuple:
		"""Resolve TMDB id/poster URL for an IMDB id with caching."""
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
			tmdb_id, poster_url = lookup_scraper.find_by_imdb_id(
				imdb_id
			)
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
		self, scraper, title: str, year: str = "",
		query_title: str = "", query_year: str = "",
		query_runtime: int = 0,
	) -> list:
		"""Search for movie metadata by title.

		Computes match confidence for each result and sorts
		by confidence descending so the best match is first.

		Args:
			scraper: Active scraper instance (TMDB or IMDB).
			title: Movie title to search for.
			year: Optional release year to narrow results.
			query_title: Original title for scoring (defaults to title).
			query_year: Original year for scoring (defaults to year).
			query_runtime: Runtime in minutes (0 if unknown).

		Returns:
			List of SearchResult instances sorted by match confidence.
		"""
		# determine cache type based on active scraper
		is_imdb = isinstance(
			scraper,
			moviemanager.scraper.imdb_scraper.ImdbScraper,
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
			results = scraper.search(title, year)
			if is_imdb:
				prefetch_results = (
					results[:_TMDB_POSTER_PREFETCH_LIMIT]
				)
				for item in prefetch_results:
					self._prefer_tmdb_poster(item)
			# only cache non-empty results (empty means search failed)
			if results:
				self._cache.put_search_results(
					cache_type, title, year, results
				)
		# compute match confidence for each result
		ref_title = query_title or title
		ref_year = query_year or year
		for r in results:
			r.match_confidence = (
				moviemanager.api.match_confidence
				.compute_match_confidence(
					ref_title, ref_year,
					r.title, r.year,
					result_original_title=r.original_title,
					result_score=r.score,
					query_runtime=query_runtime,
					result_runtime=r.runtime,
				)
			)
		# sort by confidence descending (best match first)
		results.sort(
			key=lambda r: r.match_confidence, reverse=True
		)
		return results

	#============================================
	def search_movie_with_fallback(
		self, scraper, title: str, year: str = "",
		query_runtime: int = 0,
	) -> tuple:
		"""Search with fallback strategies when initial search fails.

		Tries progressively broader searches:
		1. title + year (exact)
		2. title only (drop year)
		3. simplified title (remove parenthetical text, articles)

		Args:
			scraper: Active scraper instance.
			title: Movie title to search for.
			year: Optional release year to narrow results.
			query_runtime: Runtime in minutes (0 if unknown).

		Returns:
			tuple: (results list, strategy description string).
		"""
		# strategy 1: title + year
		if year:
			results = self.search_movie(
				scraper, title, year,
				query_runtime=query_runtime,
			)
			if results:
				strategy = f"title + year: {title} ({year})"
				return (results, strategy)
			# strategy 2: title only (drop year)
			results = self.search_movie(
				scraper, title,
				query_runtime=query_runtime,
			)
			if results:
				strategy = f"title only: {title}"
				return (results, strategy)
		else:
			results = self.search_movie(
				scraper, title,
				query_runtime=query_runtime,
			)
			if results:
				strategy = f"title: {title}"
				return (results, strategy)
		# strategy 3: simplified title
		simplified = _simplify_title(title)
		if simplified != title.lower().strip():
			results = self.search_movie(
				scraper, simplified,
				query_runtime=query_runtime,
			)
			if results:
				strategy = f"simplified: {simplified}"
				return (results, strategy)
		# nothing found
		return ([], "no results")


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
	simplified = re.sub(
		r"^(The|A|An)\s+", "", simplified, flags=re.IGNORECASE
	)
	# collapse whitespace and strip
	simplified = re.sub(r"\s+", " ", simplified).strip()
	return simplified


# simple assertion for _simplify_title
assert _simplify_title("The Matrix (1999)") == "Matrix"
assert _simplify_title("A Beautiful Mind") == "Beautiful Mind"
assert _simplify_title("Clerks") == "Clerks"
