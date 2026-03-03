"""IMDB scraper using the GraphQL API with curl_cffi transport."""

# Standard Library
import re
import time
import random
import logging

# PIP3 modules
import curl_cffi.requests

# local repo modules
import moviemanager.scraper.interfaces
import moviemanager.scraper.types


# module logger
_LOG = logging.getLogger(__name__)

# GraphQL endpoint that bypasses WAF challenges
_GRAPHQL_URL = "https://graphql.imdb.com/"

# GraphQL query to fetch full movie metadata in one request
_METADATA_QUERY = """query GetTitle($id: ID!) {
  title(id: $id) {
    titleText { text }
    originalTitleText { text }
    releaseYear { year }
    releaseDate { day month year }
    ratingsSummary { aggregateRating voteCount topRanking { rank } }
    plot { plotText { plainText } }
    runtime { seconds }
    certificate { rating }
    genres { genres { text } }
    primaryImage { url }
    taglines(first: 1) { edges { node { text } } }
    countriesOfOrigin { countries { id text } }
    spokenLanguages { spokenLanguages { id text } }
    companyCredits(first: 5) {
      edges {
        node {
          company { companyText { text } }
          category { text }
        }
      }
    }
    principalCredits {
      category { text }
      credits(limit: 20) {
        name {
          id
          nameText { text }
          primaryImage { url }
        }
        ... on Cast { characters { name } }
      }
    }
    keywords(first: 20) { edges { node { text } } }
    parentsGuide {
      categories {
        category { text }
        severity { text }
      }
    }
  }
}"""

# GraphQL query for fetching only parental guide data
_PARENTAL_GUIDE_QUERY = """query ParentalGuide($id: ID!) {
  title(id: $id) {
    parentsGuide {
      categories {
        category { text }
        severity { text }
      }
    }
  }
}"""

# GraphQL query for searching titles
_SEARCH_QUERY = """query SearchTitle($searchTerm: String!) {
  mainSearch(first: 10, options: {searchTerm: $searchTerm, type: TITLE}) {
    edges {
      node {
        entity {
          ... on Title {
            id
            titleText { text }
            originalTitleText { text }
            releaseYear { year }
            primaryImage { url }
            plot { plotText { plainText } }
            ratingsSummary { aggregateRating }
            titleType { text }
          }
        }
      }
    }
  }
}"""


#============================================
def _fetch_graphql(query: str, variables: dict, session) -> dict:
	"""POST a GraphQL query to the IMDB endpoint.

	Args:
		query: GraphQL query string.
		variables: Variables dict for the query.
		session: curl_cffi Session instance.

	Returns:
		dict: Parsed JSON response data.

	Raises:
		ConnectionError: If AWS WAF challenge is returned (HTTP 202).
		RuntimeError: If the response contains GraphQL errors.
	"""
	# rate-limit courtesy pause
	time.sleep(random.random())
	response = session.post(
		_GRAPHQL_URL,
		headers={"content-type": "application/json"},
		json={"query": query, "variables": variables},
		timeout=30,
	)
	# detect WAF challenge (HTTP 202 means blocked)
	if response.status_code == 202:
		raise ConnectionError(
			"AWS WAF challenge detected on IMDB GraphQL endpoint. "
			"The request was blocked by IMDB's bot protection."
		)
	response.raise_for_status()
	data = response.json()
	# check for GraphQL-level errors
	if "errors" in data and not data.get("data"):
		error_msgs = [e.get("message", "") for e in data["errors"]]
		error_text = "; ".join(error_msgs)
		raise RuntimeError(f"IMDB GraphQL error: {error_text}")
	result = data.get("data", {})
	return result


#============================================
def _safe_get(obj: dict, *keys, default=None):
	"""Safely traverse nested dict keys, returning default if any key is missing.

	Args:
		obj: Root dictionary to traverse.
		*keys: Sequence of keys to follow.
		default: Value to return if any key is missing or None.

	Returns:
		The value at the nested key path, or default.
	"""
	current = obj
	for key in keys:
		if not isinstance(current, dict):
			return default
		current = current.get(key)
		if current is None:
			return default
	return current


#============================================
def _upgrade_poster_url(url: str) -> str:
	"""Strip IMDB image resize parameters to get full resolution.

	IMDB appends resize suffixes like ._V1_UX300_.jpg to poster URLs.
	Stripping these gives the full-size original image.

	Args:
		url: IMDB image URL, possibly with resize parameters.

	Returns:
		str: Clean URL without resize parameters.
	"""
	if not url:
		return ""
	# match ._V1_ followed by resize params before .jpg
	# keep just ._V1_.jpg for full resolution
	cleaned = re.sub(r"\._V1_[^.]*\.jpg$", "._V1_.jpg", url)
	return cleaned


#============================================
def _parse_graphql_parental_guide(title_data: dict) -> dict:
	"""Extract parental guide severity levels from GraphQL response.

	Args:
		title_data: The title object from GraphQL response.

	Returns:
		dict: Category name to severity string mapping.
	"""
	guide = {}
	pg_data = _safe_get(title_data, "parentsGuide", default={})
	categories = pg_data.get("categories", []) or []
	for cat in categories:
		cat_name = _safe_get(cat, "category", "text", default="")
		severity = _safe_get(cat, "severity", "text", default="")
		if cat_name and severity:
			guide[cat_name] = severity
	return guide


#============================================
def _parse_graphql_cast(title_data: dict) -> list:
	"""Extract actors with character roles from GraphQL principalCredits.

	Args:
		title_data: The title object from GraphQL response.

	Returns:
		list: List of CastMember dataclasses for actors.
	"""
	actors = []
	credits_list = title_data.get("principalCredits", []) or []
	for credit_group in credits_list:
		category = _safe_get(credit_group, "category", "text", default="")
		if category not in ("Stars", "Cast"):
			continue
		credits = credit_group.get("credits", []) or []
		for person in credits:
			name = _safe_get(person, "name", "nameText", "text", default="")
			imdb_id = _safe_get(person, "name", "id", default="")
			thumb_url = _safe_get(person, "name", "primaryImage", "url", default="")
			# extract character name from characters list
			characters = person.get("characters", []) or []
			role = ""
			if characters:
				role = characters[0].get("name", "")
			cast_member = moviemanager.scraper.types.CastMember(
				name=name,
				role=role,
				thumb_url=_upgrade_poster_url(thumb_url),
				imdb_id=imdb_id,
				department="Acting",
			)
			actors.append(cast_member)
	return actors


#============================================
def _extract_principal_credits(title_data: dict, category_name: str) -> str:
	"""Extract names from a principalCredits category as a comma-joined string.

	Args:
		title_data: The title object from GraphQL response.
		category_name: Category to extract (e.g. 'Director', 'Writer').

	Returns:
		str: Comma-separated names, or empty string.
	"""
	credits_list = title_data.get("principalCredits", []) or []
	for credit_group in credits_list:
		category = _safe_get(credit_group, "category", "text", default="")
		if category != category_name:
			continue
		credits = credit_group.get("credits", []) or []
		names = []
		for person in credits:
			name = _safe_get(person, "name", "nameText", "text", default="")
			if name:
				names.append(name)
		result = ", ".join(names)
		return result
	return ""


#============================================
def _extract_producers(title_data: dict) -> list:
	"""Extract producers from principalCredits.

	Args:
		title_data: The title object from GraphQL response.

	Returns:
		list: List of CastMember dataclasses with department='Production'.
	"""
	producers = []
	credits_list = title_data.get("principalCredits", []) or []
	for credit_group in credits_list:
		category = _safe_get(credit_group, "category", "text", default="")
		if "Producer" not in category:
			continue
		credits = credit_group.get("credits", []) or []
		for person in credits:
			name = _safe_get(person, "name", "nameText", "text", default="")
			imdb_id = _safe_get(person, "name", "id", default="")
			if name:
				producer = moviemanager.scraper.types.CastMember(
					name=name,
					imdb_id=imdb_id,
					department="Production",
				)
				producers.append(producer)
	return producers


#============================================
def _extract_studio(title_data: dict) -> str:
	"""Extract first production company name from companyCredits.

	Args:
		title_data: The title object from GraphQL response.

	Returns:
		str: Studio name, or empty string.
	"""
	edges = _safe_get(title_data, "companyCredits", "edges", default=[])
	for edge in edges:
		node = edge.get("node", {})
		cat_text = _safe_get(node, "category", "text", default="")
		# only use production companies, not distributors
		if "Production" in cat_text:
			studio = _safe_get(node, "company", "companyText", "text", default="")
			return studio
	return ""


#============================================
def _parse_graphql_metadata(data: dict, imdb_id: str) -> moviemanager.scraper.types.MediaMetadata:
	"""Map GraphQL title response to a MediaMetadata dataclass.

	Args:
		data: The GraphQL response data dict containing 'title' key.
		imdb_id: The IMDB ID used for the query.

	Returns:
		MediaMetadata: Populated metadata dataclass.
	"""
	title_data = data.get("title", {}) or {}
	# basic text fields
	title = _safe_get(title_data, "titleText", "text", default="")
	original_title = _safe_get(title_data, "originalTitleText", "text", default="")
	# year
	year_int = _safe_get(title_data, "releaseYear", "year", default=0)
	year = str(year_int) if year_int else ""
	# release date
	rd = title_data.get("releaseDate") or {}
	release_date = ""
	if rd.get("year") and rd.get("month") and rd.get("day"):
		release_date = f"{rd['year']}-{rd['month']:02d}-{rd['day']:02d}"
	# rating and votes
	ratings = title_data.get("ratingsSummary") or {}
	rating = float(ratings.get("aggregateRating") or 0.0)
	votes = int(ratings.get("voteCount") or 0)
	top_ranking = _safe_get(ratings, "topRanking", "rank", default=0)
	top250 = int(top_ranking) if top_ranking and int(top_ranking) <= 250 else 0
	# plot
	plot = _safe_get(title_data, "plot", "plotText", "plainText", default="")
	# runtime in minutes (API returns seconds)
	runtime_seconds = _safe_get(title_data, "runtime", "seconds", default=0)
	runtime = int(runtime_seconds) // 60 if runtime_seconds else 0
	# certification
	certification = _safe_get(title_data, "certificate", "rating", default="")
	# genres
	raw_genres = _safe_get(title_data, "genres", "genres", default=[])
	genres = [g.get("text", "") for g in raw_genres if g.get("text")]
	# poster URL (full resolution)
	raw_poster = _safe_get(title_data, "primaryImage", "url", default="")
	poster_url = _upgrade_poster_url(raw_poster)
	# tagline
	tagline_edges = _safe_get(title_data, "taglines", "edges", default=[])
	tagline = ""
	if tagline_edges:
		tagline = _safe_get(tagline_edges[0], "node", "text", default="")
	# countries
	raw_countries = _safe_get(title_data, "countriesOfOrigin", "countries", default=[])
	country_names = []
	for c in raw_countries:
		# prefer text name, fall back to id code
		cname = c.get("text") or c.get("id", "")
		if cname:
			country_names.append(cname)
	country = ", ".join(country_names)
	# spoken languages
	raw_langs = _safe_get(title_data, "spokenLanguages", "spokenLanguages", default=[])
	lang_names = []
	for lang in raw_langs:
		lname = lang.get("text") or lang.get("id", "")
		if lname:
			lang_names.append(lname)
	spoken_languages = ", ".join(lang_names)
	# studio (first production company)
	studio = _extract_studio(title_data)
	# director and writer from principalCredits
	director = _extract_principal_credits(title_data, "Director")
	writer = _extract_principal_credits(title_data, "Writer")
	# cast (actors with characters)
	actors = _parse_graphql_cast(title_data)
	# producers
	producers = _extract_producers(title_data)
	# keywords/tags
	keyword_edges = _safe_get(title_data, "keywords", "edges", default=[])
	tags = []
	for edge in keyword_edges:
		kw = _safe_get(edge, "node", "text", default="")
		if kw:
			tags.append(kw)
	# parental guide
	parental_guide = _parse_graphql_parental_guide(title_data)
	metadata = moviemanager.scraper.types.MediaMetadata(
		title=title,
		original_title=original_title,
		year=year,
		tagline=tagline,
		plot=plot,
		runtime=runtime,
		certification=certification,
		country=country,
		spoken_languages=spoken_languages,
		release_date=release_date,
		rating=rating,
		votes=votes,
		top250=top250,
		director=director,
		writer=writer,
		studio=studio,
		genres=genres,
		tags=tags,
		parental_guide=parental_guide,
		actors=actors,
		producers=producers,
		imdb_id=imdb_id,
		poster_url=poster_url,
		media_source="imdb",
	)
	return metadata


#============================================
class ImdbScraper(moviemanager.scraper.interfaces.MetadataProvider):
	"""IMDB scraper using the GraphQL API with curl_cffi transport.

	Fetches movie metadata directly from IMDB's GraphQL endpoint,
	bypassing the HTML pages that require WAF challenge solving.
	"""

	#============================================
	def __init__(self):
		"""Initialize the IMDB scraper with a curl_cffi session."""
		self._session = curl_cffi.requests.Session(impersonate="chrome")

	#============================================
	def set_cookies(self, cookies: list) -> None:
		"""Inject browser cookies into the session.

		Args:
			cookies: List of cookie dicts with keys: name, value, domain, path.
		"""
		for cookie in cookies:
			name = cookie.get("name", "")
			value = cookie.get("value", "")
			domain = cookie.get("domain", "")
			if name and value:
				self._session.cookies.set(name, value, domain=domain)
		_LOG.info("Injected %d cookies into IMDB scraper session", len(cookies))

	#============================================
	def search(self, title: str, year: str = "") -> list:
		"""Search IMDB for movies matching a title and optional year.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			list: List of SearchResult dataclasses.
		"""
		# build search term with optional year
		search_term = title
		if year:
			search_term = f"{title} {year}"
		data = _fetch_graphql(
			_SEARCH_QUERY,
			{"searchTerm": search_term},
			self._session,
		)
		# parse search results from response
		edges = _safe_get(data, "mainSearch", "edges", default=[])
		results = []
		for edge in edges:
			entity = _safe_get(edge, "node", "entity", default={})
			if not entity:
				continue
			# skip non-movie types (TV episodes, podcasts, etc.)
			title_type = _safe_get(entity, "titleType", "text", default="")
			if title_type and title_type not in ("Movie", "Short", "TV Movie"):
				continue
			# extract IMDB ID from the entity id field
			result_imdb_id = entity.get("id", "")
			result_title = _safe_get(entity, "titleText", "text", default="")
			result_original = _safe_get(entity, "originalTitleText", "text", default="")
			result_year_int = _safe_get(entity, "releaseYear", "year", default=0)
			result_year = str(result_year_int) if result_year_int else ""
			raw_poster = _safe_get(entity, "primaryImage", "url", default="")
			result_poster = _upgrade_poster_url(raw_poster)
			result_overview = _safe_get(entity, "plot", "plotText", "plainText", default="")
			result_score = float(
				_safe_get(entity, "ratingsSummary", "aggregateRating", default=0.0) or 0.0
			)
			search_result = moviemanager.scraper.types.SearchResult(
				title=result_title,
				original_title=result_original,
				year=result_year,
				imdb_id=result_imdb_id,
				overview=result_overview,
				poster_url=result_poster,
				score=result_score,
			)
			results.append(search_result)
		return results

	#============================================
	def get_metadata(
		self, tmdb_id: int = 0, imdb_id: str = ""
	) -> moviemanager.scraper.types.MediaMetadata:
		"""Fetch full metadata for a movie from IMDB via GraphQL.

		Args:
			tmdb_id: TMDB movie ID (not used by IMDB scraper).
			imdb_id: IMDB movie ID (tt format).

		Returns:
			MediaMetadata: Complete movie metadata.

		Raises:
			ValueError: If no imdb_id is provided.
		"""
		if not imdb_id:
			raise ValueError("IMDB scraper requires an imdb_id")
		data = _fetch_graphql(
			_METADATA_QUERY,
			{"id": imdb_id},
			self._session,
		)
		metadata = _parse_graphql_metadata(data, imdb_id)
		return metadata

	#============================================
	def get_parental_guide(self, imdb_id: str) -> dict:
		"""Fetch only parental guide data for a movie.

		Args:
			imdb_id: IMDB movie ID (tt format).

		Returns:
			dict: Category name to severity string mapping.
		"""
		if not imdb_id:
			return {}
		data = _fetch_graphql(
			_PARENTAL_GUIDE_QUERY, {"id": imdb_id}, self._session,
		)
		title_data = data.get("title", {}) or {}
		guide = _parse_graphql_parental_guide(title_data)
		return guide


# simple assertion for _upgrade_poster_url
assert _upgrade_poster_url(
	"https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg"
) == "https://m.media-amazon.com/images/M/abc._V1_.jpg"
assert _upgrade_poster_url(
	"https://m.media-amazon.com/images/M/abc._V1_.jpg"
) == "https://m.media-amazon.com/images/M/abc._V1_.jpg"
assert _upgrade_poster_url("") == ""
