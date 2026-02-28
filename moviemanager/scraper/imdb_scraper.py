"""IMDB scraper implementing MetadataProvider via direct JSON parsing.

Uses curl_cffi with browser impersonation to fetch IMDB pages,
then parses __NEXT_DATA__ JSON (search) and JSON-LD (movie details)
to extract structured metadata. No cinemagoer dependency.
"""

# Standard Library
import re
import html
import json
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

# base URLs for IMDB pages
_SEARCH_URL = "https://www.imdb.com/find/"
_TITLE_URL = "https://www.imdb.com/title/"
_PARENTAL_GUIDE_URL_SUFFIX = "/parentalguide/"

# regex patterns for extracting embedded JSON from HTML
_NEXT_DATA_RE = re.compile(
	r'<script id="__NEXT_DATA__" type="application/json">'
	r'(.*?)</script>'
)
_JSON_LD_RE = re.compile(
	r'<script type="application/ld\+json">(.*?)</script>'
)


#============================================
class ImdbScraper(moviemanager.scraper.interfaces.MetadataProvider):
	"""IMDB metadata scraper using direct JSON parsing.

	Fetches IMDB search and detail pages with curl_cffi browser
	impersonation, then extracts structured data from embedded
	__NEXT_DATA__ and JSON-LD script blocks.
	"""

	#============================================
	def __init__(self):
		"""Initialize the IMDB scraper with a persistent HTTP session."""
		# reuse a single session for connection pooling and cookie persistence
		self._session = curl_cffi.requests.Session(impersonate="chrome")

	#============================================
	def search(self, title: str, year: str = "") -> list:
		"""Search IMDB for movies matching a title.

		Fetches the IMDB find page and parses the __NEXT_DATA__ JSON
		blob to extract title search results.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			list: List of SearchResult dataclasses.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		# build query with optional year
		query = title
		if year:
			query = f"{title} ({year})"
		# fetch search page with browser impersonation
		html = _fetch_page(
			_SEARCH_URL,
			params={"q": query, "s": "tt", "ttype": "ft"},
			session=self._session,
		)
		# parse __NEXT_DATA__ JSON from the page
		results = _parse_search_results(html)
		return results

	#============================================
	def get_metadata(
		self, tmdb_id: int = 0, imdb_id: str = ""
	) -> moviemanager.scraper.types.MediaMetadata:
		"""Fetch full metadata for a movie from IMDB.

		Fetches the IMDB title page and parses the JSON-LD block
		to extract complete movie metadata.

		Args:
			tmdb_id: TMDB movie ID (unused, kept for interface).
			imdb_id: IMDB movie ID (tt format).

		Returns:
			MediaMetadata: Complete movie metadata.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		# build URL for the movie detail page
		url = f"{_TITLE_URL}{imdb_id}/"
		html = _fetch_page(url, session=self._session)
		# parse JSON-LD from the detail page
		metadata = _parse_movie_detail(html, imdb_id)
		# fetch parental guide page for severity levels
		time.sleep(random.random())
		pg_url = f"{_TITLE_URL}{imdb_id}{_PARENTAL_GUIDE_URL_SUFFIX}"
		pg_html = _fetch_page_safe(pg_url, session=self._session)
		if pg_html:
			metadata.parental_guide = _parse_parental_guide(pg_html)
		return metadata


#============================================
def _fetch_page(
	url: str,
	params: dict = None,
	session: curl_cffi.requests.Session = None,
) -> str:
	"""Fetch an IMDB page using curl_cffi with browser impersonation.

	Args:
		url: URL to fetch.
		params: Optional query parameters.
		session: Optional reusable session for connection pooling.

	Returns:
		str: HTML content of the page.

	Raises:
		ConnectionError: If the HTTP request fails or rate limited.
	"""
	if session is not None:
		response = session.get(url, params=params, timeout=30)
	else:
		response = curl_cffi.requests.get(
			url, params=params, impersonate="chrome", timeout=30,
		)
	if response.status_code == 429:
		_LOG.warning("IMDB rate limit (HTTP 429) for %s", url)
		raise ConnectionError(f"IMDB rate limit (HTTP 429) for {url}")
	if response.status_code != 200:
		raise ConnectionError(
			f"IMDB returned HTTP {response.status_code} for {url}"
		)
	html_text = response.text
	return html_text


#============================================
def _fetch_page_safe(
	url: str,
	params: dict = None,
	session: curl_cffi.requests.Session = None,
) -> str:
	"""Fetch an IMDB page, returning empty string on failure.

	Wraps _fetch_page and catches ConnectionError so callers
	can degrade gracefully without try/except blocks.

	Args:
		url: URL to fetch.
		params: Optional query parameters.
		session: Optional reusable session for connection pooling.

	Returns:
		str: HTML content of the page, or empty string on failure.
	"""
	if session is not None:
		response = session.get(url, params=params, timeout=30)
	else:
		response = curl_cffi.requests.get(
			url, params=params, impersonate="chrome", timeout=30,
		)
	if response.status_code != 200:
		_LOG.debug("Failed to fetch %s (HTTP %d)", url, response.status_code)
		return ""
	html_text = response.text
	return html_text


#============================================
def _parse_parental_guide(html: str) -> dict:
	"""Parse parental guide severity levels from IMDB page HTML.

	Extracts __NEXT_DATA__ JSON and reads category severity
	summaries from the parental guide data structure.

	Args:
		html: Raw HTML of the IMDB parental guide page.

	Returns:
		dict: Mapping of category name to severity level string,
			e.g. {"Sex & Nudity": "Moderate", "Profanity": "Severe"}.
			Returns empty dict if parsing fails.
	"""
	match = _NEXT_DATA_RE.search(html)
	if not match:
		_LOG.debug("No __NEXT_DATA__ found in IMDB parental guide page")
		return {}
	data = json.loads(match.group(1))
	# navigate to contentData.categories
	props = data.get("props", {})
	page_props = props.get("pageProps", {})
	content_data = page_props.get("contentData", {})
	categories = content_data.get("categories", [])
	if not categories:
		_LOG.debug("No parental guide categories found in __NEXT_DATA__")
		return {}
	# extract severity level for each category
	guide = {}
	for category in categories:
		title = category.get("title", "")
		severity_summary = category.get("severitySummary", {}) or {}
		severity_text = severity_summary.get("text", "")
		if title and severity_text:
			guide[title] = severity_text
	return guide


#============================================
def _parse_search_results(html: str) -> list:
	"""Parse search results from IMDB __NEXT_DATA__ JSON.

	Extracts titleResults from the embedded __NEXT_DATA__ script
	block and maps each result to a SearchResult dataclass.

	Args:
		html: Raw HTML of the IMDB search page.

	Returns:
		list: List of SearchResult dataclasses.
	"""
	match = _NEXT_DATA_RE.search(html)
	if not match:
		_LOG.warning("No __NEXT_DATA__ found in IMDB search page")
		return []
	data = json.loads(match.group(1))
	# navigate to title results
	props = data.get("props", {}).get("pageProps", {})
	title_results = props.get("titleResults", {})
	raw_results = title_results.get("results", [])
	results = []
	for item in raw_results:
		imdb_id = item.get("index", "")
		list_item = item.get("listItem", {})
		# extract title text
		result_title = list_item.get("titleText", "")
		if not result_title:
			result_title = list_item.get("originalTitleText", "")
		# extract year
		result_year = str(list_item.get("releaseYear", "") or "")
		# extract rating from ratingSummary
		rating_summary = list_item.get("ratingSummary", {})
		score = float(rating_summary.get("aggregateRating", 0) or 0)
		# extract overview/plot
		overview = list_item.get("plot", "") or ""
		# extract poster URL and upgrade to full resolution
		primary_image = list_item.get("primaryImage", {}) or {}
		poster_url = _upgrade_poster_url(primary_image.get("url", "") or "")
		search_result = moviemanager.scraper.types.SearchResult(
			title=result_title,
			year=result_year,
			imdb_id=imdb_id,
			overview=overview,
			poster_url=poster_url,
			score=score,
		)
		results.append(search_result)
	return results


#============================================
def _parse_movie_detail(html: str, imdb_id: str) -> moviemanager.scraper.types.MediaMetadata:
	"""Parse movie metadata from IMDB JSON-LD block.

	Extracts structured metadata from the JSON-LD script block
	on an IMDB movie detail page.

	Args:
		html: Raw HTML of the IMDB movie detail page.
		imdb_id: IMDB movie ID for the metadata record.

	Returns:
		MediaMetadata: Complete movie metadata dataclass.
	"""
	match = _JSON_LD_RE.search(html)
	if not match:
		_LOG.warning("No JSON-LD found in IMDB detail page for %s", imdb_id)
		# return minimal metadata with just the imdb_id
		minimal = moviemanager.scraper.types.MediaMetadata(
			imdb_id=imdb_id, media_source="imdb",
		)
		return minimal
	data = json.loads(match.group(1))
	# extract title
	title = data.get("name", "")
	# extract year from datePublished (format: YYYY-MM-DD)
	date_published = data.get("datePublished", "")
	year_str = date_published[:4] if date_published else ""
	# extract rating and votes from aggregateRating
	agg_rating = data.get("aggregateRating", {}) or {}
	rating = float(agg_rating.get("ratingValue", 0) or 0)
	votes = int(agg_rating.get("ratingCount", 0) or 0)
	# extract certification
	certification = data.get("contentRating", "") or ""
	# extract genres (list of strings)
	genres = list(data.get("genre", []))
	# extract description/plot
	plot = data.get("description", "") or ""
	# extract runtime from ISO 8601 duration (e.g. PT1H32M)
	runtime = _parse_iso_duration(data.get("duration", ""))
	# extract poster URL
	poster_url = data.get("image", "") or ""
	# extract director names
	director = _extract_person_names(data.get("director", []))
	# extract writer names from creator list (filter to Person type)
	raw_creators = data.get("creator", [])
	writer_persons = [
		c for c in raw_creators
		if isinstance(c, dict) and c.get("@type") == "Person"
	]
	writer = _extract_person_names(writer_persons)
	# extract actors as CastMember dataclasses
	actors = _extract_actors(data.get("actor", []))
	# extract trailer URL
	trailer_data = data.get("trailer", {}) or {}
	trailer_url = trailer_data.get("url", "") or ""
	# extract release date
	release_date = date_published
	metadata = moviemanager.scraper.types.MediaMetadata(
		title=title,
		year=year_str,
		plot=plot,
		runtime=runtime,
		rating=rating,
		votes=votes,
		genres=genres,
		certification=certification,
		director=director,
		writer=writer,
		actors=actors,
		imdb_id=imdb_id,
		poster_url=poster_url,
		trailer_url=trailer_url,
		release_date=release_date,
		media_source="imdb",
	)
	# upgrade poster URL to full resolution
	metadata.poster_url = _upgrade_poster_url(metadata.poster_url)
	# supplement metadata with __NEXT_DATA__ fields
	next_data = _parse_next_data_detail(html)
	fields = _extract_next_data_fields(next_data)
	# only override if the current value is empty/default
	metadata.original_title = fields.get("original_title", "") or metadata.original_title
	metadata.tagline = fields.get("tagline", "") or metadata.tagline
	metadata.country = fields.get("country", "") or metadata.country
	metadata.spoken_languages = fields.get("spoken_languages", "") or metadata.spoken_languages
	metadata.studio = fields.get("studio", "") or metadata.studio
	metadata.top250 = fields.get("top250", 0) or metadata.top250
	metadata.tags = fields.get("tags", []) or metadata.tags
	# enrich actor roles from __NEXT_DATA__ cast data
	cast_roles = _extract_cast_roles(next_data)
	for actor in metadata.actors:
		if actor.name in cast_roles and not actor.role:
			actor.role = cast_roles[actor.name]
	# extract producers from __NEXT_DATA__ principalCredits
	metadata.producers = _extract_producers(next_data)
	return metadata


#============================================
def _parse_next_data_detail(html: str) -> dict:
	"""Extract page data sections from __NEXT_DATA__ on a detail page.

	Parses the embedded __NEXT_DATA__ JSON and returns a combined dict
	with aboveTheFoldData and mainColumnData for supplementary metadata.

	Args:
		html: Raw HTML of the IMDB movie detail page.

	Returns:
		dict: Combined dict with 'aboveTheFold' and 'mainColumn' keys,
			or empty dict on failure.
	"""
	match = _NEXT_DATA_RE.search(html)
	if not match:
		_LOG.debug("No __NEXT_DATA__ found in IMDB detail page")
		return {}
	data = json.loads(match.group(1))
	# navigate to pageProps
	props = data.get("props", {})
	page_props = props.get("pageProps", {})
	above_fold = page_props.get("aboveTheFoldData", {}) or {}
	main_column = page_props.get("mainColumnData", {}) or {}
	if not above_fold:
		_LOG.debug("No aboveTheFoldData found in __NEXT_DATA__")
	# return combined structure for field extraction
	result = {
		"aboveTheFold": above_fold,
		"mainColumn": main_column,
	}
	return result


#============================================
def _extract_next_data_fields(next_data_sections: dict) -> dict:
	"""Extract supplementary metadata fields from __NEXT_DATA__ sections.

	Pulls fields not available in JSON-LD from aboveTheFoldData and
	mainColumnData in the parsed __NEXT_DATA__ structure.

	Args:
		next_data_sections: Dict with 'aboveTheFold' and 'mainColumn' keys.

	Returns:
		dict: Flat dict with original_title, tagline, country,
			spoken_languages, studio, top250, and tags.
	"""
	if not next_data_sections:
		return {}
	above_fold = next_data_sections.get("aboveTheFold", {}) or {}
	main_column = next_data_sections.get("mainColumn", {}) or {}
	# original title (only if different from display title)
	title_text = above_fold.get("titleText", {}) or {}
	original_title_data = above_fold.get("originalTitleText", {}) or {}
	display_title = title_text.get("text", "")
	original_title = original_title_data.get("text", "")
	if original_title == display_title:
		# no need to store when identical
		original_title = ""
	# tagline from aboveTheFoldData first, fallback to mainColumnData
	tagline_data = above_fold.get("tagline", {}) or {}
	tagline = tagline_data.get("text", "") or ""
	if not tagline:
		tagline_data = main_column.get("tagline", {}) or {}
		tagline = tagline_data.get("text", "") or ""
	# countries of origin (use text if available, fall back to id)
	countries_data = above_fold.get("countriesOfOrigin", {}) or {}
	countries_list = countries_data.get("countries", []) or []
	country_names = []
	for c in countries_list:
		# prefer text field, fall back to id code
		name = c.get("text", "") or c.get("id", "")
		if name:
			country_names.append(name)
	country = ", ".join(country_names)
	# spoken languages from aboveTheFoldData first, fallback to mainColumnData
	languages_data = above_fold.get("spokenLanguages", {}) or {}
	languages_list = languages_data.get("spokenLanguages", []) or []
	if not languages_list:
		# fallback to mainColumnData for spoken languages
		languages_data = main_column.get("spokenLanguages", {}) or {}
		languages_list = languages_data.get("spokenLanguages", []) or []
	language_names = []
	for lang in languages_list:
		# prefer text field, fall back to id code
		name = lang.get("text", "") or lang.get("id", "")
		if name:
			language_names.append(name)
	spoken_languages = ", ".join(language_names)
	# production studio (first company only)
	production_data = above_fold.get("production", {}) or {}
	production_edges = production_data.get("edges", []) or []
	studio = ""
	if production_edges:
		first_node = production_edges[0].get("node", {}) or {}
		company_data = first_node.get("company", {}) or {}
		company_text = company_data.get("companyText", {}) or {}
		studio = company_text.get("text", "") or ""
	# top 250 ranking
	meter_data = above_fold.get("meterRanking", {}) or {}
	top250 = int(meter_data.get("currentRank", 0) or 0)
	# keyword tags
	keywords_data = above_fold.get("keywords", {}) or {}
	keywords_edges = keywords_data.get("edges", []) or []
	tags = []
	for edge in keywords_edges:
		node = edge.get("node", {}) or {}
		tag_text = node.get("text", "")
		if tag_text:
			tags.append(tag_text)
	fields = {
		"original_title": original_title,
		"tagline": tagline,
		"country": country,
		"spoken_languages": spoken_languages,
		"studio": studio,
		"top250": top250,
		"tags": tags,
	}
	return fields


#============================================
def _parse_iso_duration(duration_str: str) -> int:
	"""Parse ISO 8601 duration string to minutes.

	Handles formats like PT1H32M, PT92M, PT2H.

	Args:
		duration_str: ISO 8601 duration string.

	Returns:
		int: Duration in minutes, or 0 if parsing fails.
	"""
	if not duration_str:
		return 0
	match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
	if not match:
		return 0
	hours = int(match.group(1) or 0)
	minutes = int(match.group(2) or 0)
	# ignore seconds for movie runtime
	total_minutes = hours * 60 + minutes
	return total_minutes


#============================================
def _extract_person_names(persons: list) -> str:
	"""Extract and join person names from JSON-LD person list.

	Args:
		persons: List of JSON-LD Person dicts with 'name' keys.

	Returns:
		str: Comma-separated person names.
	"""
	if not persons:
		return ""
	names = []
	for person in persons:
		if isinstance(person, dict):
			name = person.get("name", "")
			if name:
				names.append(name)
	result = ", ".join(names)
	return result


#============================================
def _extract_person_imdb_id(url: str) -> str:
	"""Extract IMDB person ID from a URL like /name/nm0003620/.

	Args:
		url: IMDB person URL.

	Returns:
		str: IMDB person ID (e.g. nm0003620), or empty string.
	"""
	if not url:
		return ""
	match = re.search(r"(nm\d+)", url)
	if match:
		person_id = match.group(1)
		return person_id
	return ""


#============================================
def _extract_actors(actor_list: list) -> list:
	"""Extract actors from JSON-LD actor list as CastMember objects.

	Args:
		actor_list: List of JSON-LD Person dicts.

	Returns:
		list: List of CastMember dataclasses.
	"""
	actors = []
	for person in actor_list:
		if not isinstance(person, dict):
			continue
		# decode HTML entities (JSON-LD may have &apos; etc.)
		name = html.unescape(person.get("name", ""))
		person_url = person.get("url", "")
		person_imdb_id = _extract_person_imdb_id(person_url)
		cast_member = moviemanager.scraper.types.CastMember(
			name=name,
			imdb_id=person_imdb_id,
			department="Acting",
		)
		actors.append(cast_member)
	return actors


#============================================
def _upgrade_poster_url(url: str) -> str:
	"""Strip IMDB image resize parameters for full-resolution poster.

	IMDB appends resize suffixes like ._V1_UY300_.jpg to image URLs.
	Removing everything between ._V1_ and .jpg yields the original
	full-resolution image, based on cinemagoer's get_fullsizeURL().

	Args:
		url: IMDB image URL, possibly with resize parameters.

	Returns:
		str: Full-resolution image URL, or original if no match.
	"""
	if not url:
		return ""
	# strip resize parameters after ._V1_ but before .jpg
	# e.g. ._V1_UY300_.jpg -> .jpg, but ._V1_.jpg stays unchanged
	upgraded = re.sub(r"\._V1_[^.]+\.jpg$", ".jpg", url)
	return upgraded


#============================================
def _extract_cast_roles(next_data_sections: dict) -> dict:
	"""Extract actor-to-character-name mapping from __NEXT_DATA__.

	Reads mainColumnData.castV2 which has creditedRoles with
	character names for each cast member.

	Args:
		next_data_sections: Dict with 'aboveTheFold' and 'mainColumn' keys.

	Returns:
		dict: Mapping of actor name to character name string.
	"""
	if not next_data_sections:
		return {}
	main_column = next_data_sections.get("mainColumn", {}) or {}
	# castV2 is a list of groupings, each with credits
	cast_v2 = main_column.get("castV2", []) or []
	roles = {}
	for grouping in cast_v2:
		if not isinstance(grouping, dict):
			continue
		credits = grouping.get("credits", []) or []
		for credit in credits:
			# extract actor name
			name_data = credit.get("name", {}) or {}
			name_text = name_data.get("nameText", {}) or {}
			actor_name = name_text.get("text", "")
			if not actor_name:
				continue
			# extract character from creditedRoles
			credited_roles = credit.get("creditedRoles", {}) or {}
			role_edges = credited_roles.get("edges", []) or []
			if not role_edges:
				continue
			# get first role's character name
			role_node = role_edges[0].get("node", {}) or {}
			char_conn = role_node.get("characters", {}) or {}
			char_edges = char_conn.get("edges", []) or []
			if char_edges:
				char_node = char_edges[0].get("node", {}) or {}
				char_name = char_node.get("name", "")
				if char_name:
					roles[actor_name] = char_name
	return roles


#============================================
def _extract_producers(next_data_sections: dict) -> list:
	"""Extract producer credits from __NEXT_DATA__ principalCredits.

	Scans principalCredits entries in aboveTheFoldData for the
	producer category and builds CastMember objects.

	Args:
		next_data_sections: Dict with 'aboveTheFold' and 'mainColumn' keys.

	Returns:
		list: List of CastMember dataclasses with department='Production'.
	"""
	if not next_data_sections:
		return []
	above_fold = next_data_sections.get("aboveTheFold", {}) or {}
	principal_credits = above_fold.get("principalCredits", []) or []
	producers = []
	for credit_group in principal_credits:
		category = credit_group.get("category", {}) or {}
		category_id = category.get("id", "")
		if category_id != "producer":
			continue
		credits = credit_group.get("credits", []) or []
		for credit in credits:
			name_data = credit.get("name", {}) or {}
			name_text = name_data.get("nameText", {}) or {}
			name = name_text.get("text", "")
			person_id = name_data.get("id", "")
			if not name:
				continue
			producer = moviemanager.scraper.types.CastMember(
				name=name,
				imdb_id=person_id,
				department="Production",
			)
			producers.append(producer)
		# found producer category, no need to keep searching
		break
	return producers


# simple assertion for poster URL upgrade
assert _upgrade_poster_url(
	"https://m.media-amazon.com/images/M/pic._V1_UY300_.jpg"
) == "https://m.media-amazon.com/images/M/pic.jpg"
assert _upgrade_poster_url("") == ""
assert _upgrade_poster_url("https://example.com/pic.png") == "https://example.com/pic.png"
# ._V1_.jpg (no resize params) should stay unchanged
assert _upgrade_poster_url(
	"https://m.media-amazon.com/images/M/pic@._V1_.jpg"
) == "https://m.media-amazon.com/images/M/pic@._V1_.jpg"

# simple assertion for ISO duration parser
assert _parse_iso_duration("PT1H32M") == 92
assert _parse_iso_duration("PT2H") == 120
assert _parse_iso_duration("PT90M") == 90
assert _parse_iso_duration("") == 0
