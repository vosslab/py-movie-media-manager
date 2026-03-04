"""TMDB scraper implementing MetadataProvider and ArtworkProvider."""

# Standard Library
import time
import random

# PIP3 modules
import tmdbv3api

# local repo modules
import moviemanager.scraper.interfaces
import moviemanager.scraper.types


# image base URLs used by TMDB
_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
_ORIGINAL_BASE = "https://image.tmdb.org/t/p/original"


#============================================
def _safe_str(value: object, fallback: str = "") -> str:
	"""Coerce a value to str, returning fallback for non-data types.

	tmdbv3api AsObj objects sometimes leak bound methods or other
	non-primitive types via getattr(). This helper catches those
	and returns the fallback instead.

	Args:
		value: Value to coerce to string.
		fallback: Returned when value is None or not a data type.

	Returns:
		String value, or fallback if value is not usable as data.
	"""
	if value is None:
		return fallback
	if callable(value) and not isinstance(value, str):
		return fallback
	result = str(value)
	return result


#============================================
class TmdbScraper(
	moviemanager.scraper.interfaces.MetadataProvider,
	moviemanager.scraper.interfaces.ArtworkProvider,
):
	"""Scraper that fetches movie data from The Movie Database (TMDB).

	Implements both MetadataProvider and ArtworkProvider using the
	tmdbv3api library for API access.
	"""

	# capabilities advertised by this scraper
	capabilities = {
		moviemanager.scraper.interfaces.ProviderCapability.SEARCH,
		moviemanager.scraper.interfaces.ProviderCapability.METADATA,
		moviemanager.scraper.interfaces.ProviderCapability.ARTWORK,
	}

	# settings keys required to instantiate this scraper
	requires_keys = ["tmdb_api_key"]

	#============================================
	def __init__(self, api_key: str, language: str = "en"):
		"""Initialize the TMDB scraper with an API key.

		Args:
			api_key: TMDB API key for authentication.
			language: ISO 639-1 language code for results.
		"""
		# configure the shared TMDb settings object
		self._tmdb = tmdbv3api.TMDb()
		self._tmdb.api_key = api_key
		self._tmdb.language = language
		# reusable Movie endpoint object
		self._tmdb_movie = tmdbv3api.Movie()
		# reusable Find endpoint object (for imdb_id -> tmdb mapping)
		self._tmdb_find = tmdbv3api.Find()

	#============================================
	def search(self, title: str, year: str = "") -> list:
		"""Search TMDB for movies matching a title and optional year.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			list: List of SearchResult dataclasses.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		raw_results = list(self._tmdb_movie.search(title))
		# if a year was given, also search with year appended
		if year:
			time.sleep(random.random())
			query_with_year = f"{title} {year}"
			extra = list(self._tmdb_movie.search(query_with_year))
			# merge results, avoiding duplicates by tmdb id
			seen_ids = {getattr(r, "id", 0) for r in raw_results}
			for item in extra:
				item_id = getattr(item, "id", 0)
				if item_id not in seen_ids:
					raw_results.append(item)
					seen_ids.add(item_id)
		# map raw API objects to SearchResult dataclasses
		results = []
		for item in raw_results:
			# extract year from release_date if available
			# coerce via _safe_str to guard against AsObj bound methods
			release_date = _safe_str(getattr(item, "release_date", ""))
			item_year = release_date[:4] if len(release_date) >= 4 else ""
			# build poster URL if poster_path exists
			poster_path = _safe_str(getattr(item, "poster_path", None))
			poster_url = ""
			if poster_path:
				poster_url = f"{_POSTER_BASE}{poster_path}"
			# coerce all string fields to guard against AsObj bound methods
			item_title = _safe_str(getattr(item, "title", ""))
			item_original_title = _safe_str(getattr(item, "original_title", ""))
			item_overview = _safe_str(getattr(item, "overview", ""))
			# skip entries with no usable title
			if not item_title and not item_original_title:
				continue
			search_result = moviemanager.scraper.types.SearchResult(
				title=item_title,
				original_title=item_original_title,
				year=item_year,
				tmdb_id=getattr(item, "id", 0),
				overview=item_overview,
				poster_url=poster_url,
				score=float(getattr(item, "vote_average", 0.0) or 0.0),
			)
			results.append(search_result)
		return results

	#============================================
	def get_metadata(
		self, tmdb_id: int = 0, imdb_id: str = ""
	) -> moviemanager.scraper.types.MediaMetadata:
		"""Fetch full metadata for a movie from TMDB.

		Args:
			tmdb_id: TMDB movie ID.
			imdb_id: IMDB movie ID (tt format).

		Returns:
			MediaMetadata: Complete movie metadata.
		"""
		# resolve tmdb_id from imdb_id when tmdb_id is missing
		if not tmdb_id and imdb_id:
			tmdb_id, _ = self.find_by_imdb_id(imdb_id)
		if not tmdb_id:
			# cannot fetch details without a valid tmdb_id
			empty = moviemanager.scraper.types.MediaMetadata(
				imdb_id=imdb_id,
			)
			return empty
		# rate-limit courtesy pause
		time.sleep(random.random())
		detail = self._tmdb_movie.details(
			tmdb_id, append_to_response="credits,releases,videos"
		)
		# extract basic fields with safe defaults
		# coerce via _safe_str to guard against AsObj bound methods
		release_date = _safe_str(getattr(detail, "release_date", ""))
		year_str = release_date[:4] if len(release_date) >= 4 else ""
		# extract genres list
		raw_genres = getattr(detail, "genres", []) or []
		genres = [g.get("name", "") if isinstance(g, dict) else getattr(g, "name", "") for g in raw_genres]
		# extract credits
		credits_obj = getattr(detail, "credits", None)
		director = ""
		writer = ""
		actors = []
		if credits_obj:
			# crew: director and writers
			crew_list = getattr(credits_obj, "crew", []) or []
			directors = []
			writers = []
			for member in crew_list:
				job = getattr(member, "job", "") if not isinstance(member, dict) else member.get("job", "")
				dept = getattr(member, "department", "") if not isinstance(member, dict) else member.get("department", "")
				name = getattr(member, "name", "") if not isinstance(member, dict) else member.get("name", "")
				if job == "Director":
					directors.append(name)
				if dept == "Writing":
					writers.append(name)
			director = ", ".join(directors)
			writer = ", ".join(writers)
			# cast: map to CastMember dataclass
			cast_list = getattr(credits_obj, "cast", []) or []
			for person in cast_list:
				cast_name = getattr(person, "name", "") if not isinstance(person, dict) else person.get("name", "")
				character = getattr(person, "character", "") if not isinstance(person, dict) else person.get("character", "")
				person_id = getattr(person, "id", 0) if not isinstance(person, dict) else person.get("id", 0)
				cast_member = moviemanager.scraper.types.CastMember(
					name=cast_name,
					role=character,
					tmdb_id=person_id,
				)
				actors.append(cast_member)
		# studio from first production company
		companies = getattr(detail, "production_companies", []) or []
		studio = ""
		if companies:
			first = companies[0]
			studio = first.get("name", "") if isinstance(first, dict) else getattr(first, "name", "")
		# country from production countries
		countries = getattr(detail, "production_countries", []) or []
		country_names = []
		for c in countries:
			cname = c.get("name", "") if isinstance(c, dict) else getattr(c, "name", "")
			country_names.append(cname)
		country = ", ".join(country_names)
		# spoken languages
		raw_langs = getattr(detail, "spoken_languages", []) or []
		lang_names = []
		for lang in raw_langs:
			lname = lang.get("english_name", "") if isinstance(lang, dict) else getattr(lang, "english_name", "")
			lang_names.append(lname)
		spoken_languages = ", ".join(lang_names)
		# artwork URLs
		poster_path = getattr(detail, "poster_path", None)
		poster_url = f"{_POSTER_BASE}{poster_path}" if poster_path else ""
		backdrop_path = getattr(detail, "backdrop_path", None)
		fanart_url = f"{_ORIGINAL_BASE}{backdrop_path}" if backdrop_path else ""
		# certification from US release info
		certification = _extract_us_certification(detail)
		# extract trailer URL from videos
		videos = getattr(detail, "videos", None)
		trailer_url = ""
		if videos:
			results_list = getattr(videos, "results", []) or []
			for video in results_list:
				# handle both dict and object API responses
				site = video.get("site", "") if isinstance(video, dict) else getattr(video, "site", "")
				vtype = video.get("type", "") if isinstance(video, dict) else getattr(video, "type", "")
				key = video.get("key", "") if isinstance(video, dict) else getattr(video, "key", "")
				if site == "YouTube" and vtype == "Trailer" and key:
					trailer_url = f"https://www.youtube.com/watch?v={key}"
					break
		metadata = moviemanager.scraper.types.MediaMetadata(
			title=_safe_str(getattr(detail, "title", "")),
			original_title=_safe_str(getattr(detail, "original_title", "")),
			year=year_str,
			plot=_safe_str(getattr(detail, "overview", "")),
			tagline=_safe_str(getattr(detail, "tagline", "")),
			runtime=int(getattr(detail, "runtime", 0) or 0),
			rating=float(getattr(detail, "vote_average", 0.0) or 0.0),
			votes=int(getattr(detail, "vote_count", 0) or 0),
			genres=genres,
			director=director,
			writer=writer,
			actors=actors,
			studio=studio,
			country=country,
			spoken_languages=spoken_languages,
			imdb_id=_safe_str(getattr(detail, "imdb_id", "")),
			tmdb_id=getattr(detail, "id", 0),
			poster_url=poster_url,
			fanart_url=fanart_url,
			certification=certification,
			release_date=release_date,
			trailer_url=trailer_url,
		)
		return metadata

	#============================================
	def find_by_imdb_id(self, imdb_id: str) -> tuple:
		"""Resolve TMDB movie id and poster URL from an IMDB id.

		Args:
			imdb_id: IMDB id string like ``tt0468569``.

		Returns:
			tuple: ``(tmdb_id, poster_url)`` where missing values are
				``0`` and ``""``.
		"""
		if not imdb_id:
			return (0, "")
		# rate-limit courtesy pause
		time.sleep(random.random())
		result = self._tmdb_find.find_by_imdb_id(imdb_id)
		movie_results = getattr(result, "movie_results", []) or []
		if not movie_results:
			return (0, "")
		first = movie_results[0]
		if isinstance(first, dict):
			tmdb_id = int(first.get("id", 0) or 0)
			poster_path = first.get("poster_path", "") or ""
		else:
			tmdb_id = int(getattr(first, "id", 0) or 0)
			poster_path = getattr(first, "poster_path", "") or ""
		poster_url = ""
		if poster_path:
			poster_url = f"{_POSTER_BASE}{poster_path}"
		return (tmdb_id, poster_url)

	#============================================
	def get_artwork(self, tmdb_id: int = 0, imdb_id: str = "") -> dict:
		"""Fetch available artwork URLs for a movie from TMDB.

		Args:
			tmdb_id: TMDB movie ID.
			imdb_id: IMDB movie ID.

		Returns:
			dict: Mapping of artwork type to list of URL strings.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		images_data = self._tmdb_movie.images(tmdb_id)
		# extract poster and backdrop file paths
		posters_raw = getattr(images_data, "posters", []) or []
		backdrops_raw = getattr(images_data, "backdrops", []) or []
		poster_urls = []
		for img in posters_raw:
			file_path = getattr(img, "file_path", "") if not isinstance(img, dict) else img.get("file_path", "")
			if file_path:
				full_url = f"{_ORIGINAL_BASE}{file_path}"
				poster_urls.append(full_url)
		fanart_urls = []
		for img in backdrops_raw:
			file_path = getattr(img, "file_path", "") if not isinstance(img, dict) else img.get("file_path", "")
			if file_path:
				full_url = f"{_ORIGINAL_BASE}{file_path}"
				fanart_urls.append(full_url)
		artwork = {"poster": poster_urls, "fanart": fanart_urls}
		return artwork


#============================================
def _extract_us_certification(detail: object) -> str:
	"""Extract US certification from TMDB releases data.

	Args:
		detail: TMDB movie detail object with releases attribute.

	Returns:
		str: US certification string, or empty string if not found.
	"""
	releases_obj = getattr(detail, "releases", None)
	if not releases_obj:
		return ""
	countries_list = getattr(releases_obj, "countries", []) or []
	for entry in countries_list:
		iso = getattr(entry, "iso_3166_1", "") if not isinstance(entry, dict) else entry.get("iso_3166_1", "")
		if iso == "US":
			cert = getattr(entry, "certification", "") if not isinstance(entry, dict) else entry.get("certification", "")
			return cert
	return ""
