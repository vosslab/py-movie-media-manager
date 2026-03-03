"""IMDB scraper using CDN suggestion API and QWebEnginePage transport.

Search uses the IMDB suggestion CDN (no WAF). Parental guide and metadata
use QWebEnginePage to load HTML pages, which solves AWS WAF JavaScript
challenges automatically via the Chromium engine.
"""

# Standard Library
import re
import json
import time
import random
import logging

# PIP3 modules
import requests

# local repo modules
import moviemanager.scraper.interfaces
import moviemanager.scraper.types


# module logger
_LOG = logging.getLogger(__name__)

# CDN suggestion endpoint (no WAF protection)
_SUGGESTION_URL = "https://v2.sg.media-imdb.com/suggestion/titles/x/{query}.json"

# IMDB base URL for page loads via transport
_IMDB_BASE = "https://www.imdb.com"

# allowed title types from suggestion API
_ALLOWED_TYPES = {"movie", "short", "tvMovie"}

# HTTP session for suggestion API (no WAF, plain requests)
_SUGGESTION_HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
		"AppleWebKit/537.36 (KHTML, like Gecko) "
		"Chrome/124.0.0.0 Safari/537.36"
	),
}


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
def _fetch_suggestion(query: str) -> list:
	"""Fetch search suggestions from IMDB CDN endpoint.

	The suggestion API has no WAF protection, so plain HTTP works.

	Args:
		query: Search query string.

	Returns:
		list: Raw suggestion dicts from the API response.
	"""
	# normalize query for URL: lowercase, strip whitespace
	normalized = query.strip().lower()
	if not normalized:
		return []
	# rate-limit courtesy pause
	time.sleep(random.random())
	url = _SUGGESTION_URL.format(query=normalized)
	response = requests.get(url, headers=_SUGGESTION_HEADERS, timeout=15)
	if response.status_code != 200:
		_LOG.warning(
			"IMDB suggestion API returned HTTP %d for query: %s",
			response.status_code, query,
		)
		return []
	data = response.json()
	# the 'd' key contains the list of suggestion entries
	entries = data.get("d", [])
	return entries


#============================================
def _parse_suggestion_results(entries: list) -> list:
	"""Parse CDN suggestion entries into SearchResult objects.

	Filters to movie types only (excludes TV episodes, podcasts, etc).

	Args:
		entries: Raw suggestion dicts from the CDN API.

	Returns:
		list: List of SearchResult dataclasses.
	"""
	results = []
	for entry in entries:
		# filter by title type (qid field)
		qid = entry.get("qid", "")
		if qid and qid not in _ALLOWED_TYPES:
			continue
		# skip entries without an IMDB ID
		imdb_id = entry.get("id", "")
		if not imdb_id or not imdb_id.startswith("tt"):
			continue
		title = entry.get("l", "")
		year_val = entry.get("y", 0)
		year = str(year_val) if year_val else ""
		# poster image (thumbnail from CDN)
		image_info = entry.get("i", {}) or {}
		poster_url = _upgrade_poster_url(image_info.get("imageUrl", ""))
		# rank (lower is more popular)
		rank = entry.get("rank", 0)
		# use inverse rank as a rough popularity score (0-10 scale)
		score = 0.0
		if rank and rank > 0:
			score = max(0.0, min(10.0, 10.0 - (rank / 10000.0)))
		search_result = moviemanager.scraper.types.SearchResult(
			title=title,
			year=year,
			imdb_id=imdb_id,
			poster_url=poster_url,
			score=score,
		)
		results.append(search_result)
	return results


#============================================
def _extract_next_data_json(html: str) -> dict:
	"""Extract __NEXT_DATA__ JSON from an IMDB page's HTML.

	IMDB embeds structured metadata in a script tag with id="__NEXT_DATA__".
	This contains the same data as the GraphQL API.

	Args:
		html: Full HTML content of an IMDB page.

	Returns:
		dict: Parsed JSON data, or empty dict if not found.
	"""
	# find the __NEXT_DATA__ script tag
	pattern = r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>'
	match = re.search(pattern, html, re.DOTALL)
	if not match:
		_LOG.warning("__NEXT_DATA__ script tag not found in IMDB page")
		return {}
	raw_json = match.group(1)
	data = json.loads(raw_json)
	return data


#============================================
def _parse_parental_guide_html(html: str) -> dict:
	"""Parse parental guide severity levels from IMDB parental guide page HTML.

	Extracts category-to-severity mapping from the __NEXT_DATA__ JSON
	embedded in the parental guide page.

	Args:
		html: Full HTML of the /title/{id}/parentalguide page.

	Returns:
		dict: Category name to severity string mapping.
	"""
	data = _extract_next_data_json(html)
	if not data:
		return {}
	# navigate to the parental guide section in __NEXT_DATA__
	# structure: props.pageProps.contentData.section.items[]
	page_props = _safe_get(data, "props", "pageProps", default={})
	content_data = _safe_get(page_props, "contentData", default={})
	# the parental guide page stores categories in section.items
	section = _safe_get(content_data, "section", default={})
	items = section.get("items", []) or []
	guide = {}
	for item in items:
		# each item has an id like "advisory-nudity" and a severityVote
		cat_id = item.get("id", "")
		# map advisory IDs to display names
		cat_name = _advisory_id_to_name(cat_id)
		if not cat_name:
			continue
		# severity is in severityVote.severity or votedSeverity
		severity = ""
		severity_vote = item.get("severityVote", {}) or {}
		if severity_vote:
			severity = severity_vote.get("severity", "")
		if not severity:
			severity = item.get("votedSeverity", "")
		if cat_name and severity:
			guide[cat_name] = severity
	# fallback: try the older parentsGuide structure
	if not guide:
		guide = _parse_parental_guide_from_above_fold(page_props)
	return guide


#============================================
def _advisory_id_to_name(advisory_id: str) -> str:
	"""Map IMDB advisory section IDs to display category names.

	Args:
		advisory_id: Advisory section ID (e.g. "advisory-nudity").

	Returns:
		str: Display name, or empty string if not recognized.
	"""
	mapping = {
		"advisory-nudity": "Sex & Nudity",
		"advisory-violence": "Violence & Gore",
		"advisory-profanity": "Profanity",
		"advisory-alcohol": "Alcohol, Drugs & Smoking",
		"advisory-frightening": "Frightening & Intense Scenes",
	}
	name = mapping.get(advisory_id, "")
	return name


#============================================
def _parse_parental_guide_from_above_fold(page_props: dict) -> dict:
	"""Fallback parser for parental guide from aboveTheFoldData.

	Some IMDB page versions embed the guide data differently.

	Args:
		page_props: The pageProps dict from __NEXT_DATA__.

	Returns:
		dict: Category name to severity string mapping.
	"""
	guide = {}
	above_fold = _safe_get(page_props, "aboveTheFoldData", default={})
	parents_guide = _safe_get(above_fold, "parentsGuide", default={})
	categories = parents_guide.get("categories", []) or []
	for cat in categories:
		cat_name = _safe_get(cat, "category", "text", default="")
		severity = _safe_get(cat, "severity", "text", default="")
		if cat_name and severity:
			guide[cat_name] = severity
	return guide


#============================================
def _parse_metadata_html(html: str, imdb_id: str) -> moviemanager.scraper.types.MediaMetadata:
	"""Parse full movie metadata from an IMDB title page's HTML.

	Extracts metadata from the __NEXT_DATA__ JSON embedded in the page.

	Args:
		html: Full HTML of the /title/{id}/ page.
		imdb_id: The IMDB ID used for the request.

	Returns:
		MediaMetadata: Populated metadata dataclass.
	"""
	data = _extract_next_data_json(html)
	if not data:
		# return minimal metadata with just the ID
		return moviemanager.scraper.types.MediaMetadata(
			imdb_id=imdb_id, media_source="imdb",
		)
	# navigate to the title data in __NEXT_DATA__
	page_props = _safe_get(data, "props", "pageProps", default={})
	above_fold = _safe_get(page_props, "aboveTheFoldData", default={})
	main_column = _safe_get(page_props, "mainColumnData", default={})
	# basic text fields
	title = _safe_get(above_fold, "titleText", "text", default="")
	original_title = _safe_get(
		above_fold, "originalTitleText", "text", default=""
	)
	# year
	year_int = _safe_get(above_fold, "releaseYear", "year", default=0)
	year = str(year_int) if year_int else ""
	# release date
	rd = above_fold.get("releaseDate") or {}
	release_date = ""
	if rd.get("year") and rd.get("month") and rd.get("day"):
		release_date = f"{rd['year']}-{rd['month']:02d}-{rd['day']:02d}"
	# rating and votes
	ratings = above_fold.get("ratingsSummary") or {}
	rating = float(ratings.get("aggregateRating") or 0.0)
	votes = int(ratings.get("voteCount") or 0)
	top_ranking = _safe_get(ratings, "topRanking", "rank", default=0)
	top250 = int(top_ranking) if top_ranking and int(top_ranking) <= 250 else 0
	# plot
	plot = _safe_get(above_fold, "plot", "plotText", "plainText", default="")
	# runtime (above fold has runtime in seconds)
	runtime_seconds = _safe_get(above_fold, "runtime", "seconds", default=0)
	runtime = int(runtime_seconds) // 60 if runtime_seconds else 0
	# certification
	certification = _safe_get(
		above_fold, "certificate", "rating", default=""
	)
	# genres
	raw_genres = _safe_get(above_fold, "genres", "genres", default=[])
	genres = [g.get("text", "") for g in raw_genres if g.get("text")]
	# poster URL (full resolution)
	raw_poster = _safe_get(above_fold, "primaryImage", "url", default="")
	poster_url = _upgrade_poster_url(raw_poster)
	# tagline
	tagline = ""
	tagline_edges = _safe_get(above_fold, "taglines", "edges", default=[])
	if tagline_edges:
		tagline = _safe_get(tagline_edges[0], "node", "text", default="")
	# countries
	raw_countries = _safe_get(
		above_fold, "countriesOfOrigin", "countries", default=[]
	)
	country_names = []
	for c in raw_countries:
		cname = c.get("text") or c.get("id", "")
		if cname:
			country_names.append(cname)
	country = ", ".join(country_names)
	# spoken languages
	raw_langs = _safe_get(
		above_fold, "spokenLanguages", "spokenLanguages", default=[]
	)
	lang_names = []
	for lang in raw_langs:
		lname = lang.get("text") or lang.get("id", "")
		if lname:
			lang_names.append(lname)
	spoken_languages = ", ".join(lang_names)
	# studio (first production company)
	studio = _extract_studio(above_fold)
	# director and writer from principalCredits
	director = _extract_principal_credits(above_fold, "Director")
	if not director:
		director = _extract_principal_credits(above_fold, "Directors")
	writer = _extract_principal_credits(above_fold, "Writer")
	if not writer:
		writer = _extract_principal_credits(above_fold, "Writers")
	# cast (actors with characters)
	actors = _parse_cast(above_fold, main_column)
	# producers
	producers = _extract_producers(above_fold)
	# keywords/tags
	tags = _extract_keywords(main_column)
	# parental guide
	parental_guide = {}
	pg_data = _safe_get(above_fold, "parentsGuide", default={})
	if pg_data:
		categories = pg_data.get("categories", []) or []
		for cat in categories:
			cat_name = _safe_get(cat, "category", "text", default="")
			severity = _safe_get(cat, "severity", "text", default="")
			if cat_name and severity:
				parental_guide[cat_name] = severity
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
def _extract_studio(title_data: dict) -> str:
	"""Extract first production company name from companyCredits.

	Args:
		title_data: The above-fold data from __NEXT_DATA__.

	Returns:
		str: Studio name, or empty string.
	"""
	edges = _safe_get(title_data, "companyCredits", "edges", default=[])
	for edge in edges:
		node = edge.get("node", {})
		cat_text = _safe_get(node, "category", "text", default="")
		# only use production companies, not distributors
		if "Production" in cat_text:
			studio = _safe_get(
				node, "company", "companyText", "text", default=""
			)
			return studio
	return ""


#============================================
def _extract_principal_credits(title_data: dict, category_name: str) -> str:
	"""Extract names from a principalCredits category as a comma-joined string.

	Args:
		title_data: The above-fold data from __NEXT_DATA__.
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
		title_data: The above-fold data from __NEXT_DATA__.

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
def _parse_cast(above_fold: dict, main_column: dict) -> list:
	"""Extract actors with character roles from __NEXT_DATA__.

	Tries principalCredits Stars/Cast from above-fold data first,
	then enriches with character names from mainColumnData castV2.

	Args:
		above_fold: The aboveTheFoldData dict.
		main_column: The mainColumnData dict.

	Returns:
		list: List of CastMember dataclasses for actors.
	"""
	actors = []
	credits_list = above_fold.get("principalCredits", []) or []
	for credit_group in credits_list:
		category = _safe_get(credit_group, "category", "text", default="")
		if category not in ("Stars", "Cast"):
			continue
		credits = credit_group.get("credits", []) or []
		for person in credits:
			name = _safe_get(person, "name", "nameText", "text", default="")
			person_imdb_id = _safe_get(person, "name", "id", default="")
			thumb_url = _safe_get(
				person, "name", "primaryImage", "url", default=""
			)
			# extract character name from characters list
			characters = person.get("characters", []) or []
			role = ""
			if characters:
				role = characters[0].get("name", "")
			cast_member = moviemanager.scraper.types.CastMember(
				name=name,
				role=role,
				thumb_url=_upgrade_poster_url(thumb_url),
				imdb_id=person_imdb_id,
				department="Acting",
			)
			actors.append(cast_member)
	# try to enrich character roles from mainColumnData castV2
	if main_column and actors:
		_enrich_cast_roles(actors, main_column)
	return actors


#============================================
def _enrich_cast_roles(actors: list, main_column: dict) -> None:
	"""Enrich actor roles with character names from castV2 data.

	Args:
		actors: List of CastMember to update in-place.
		main_column: The mainColumnData dict from __NEXT_DATA__.
	"""
	cast_edges = _safe_get(main_column, "cast", "edges", default=[])
	# build lookup from person ID to character name
	role_map = {}
	for edge in cast_edges:
		node = edge.get("node", {}) or {}
		person_id = _safe_get(node, "name", "id", default="")
		characters = node.get("characters", []) or []
		if person_id and characters:
			char_name = characters[0].get("name", "")
			if char_name:
				role_map[person_id] = char_name
	# apply role_map to actors missing character roles
	for actor in actors:
		if not actor.role and actor.imdb_id in role_map:
			actor.role = role_map[actor.imdb_id]


#============================================
def _extract_keywords(main_column: dict) -> list:
	"""Extract keyword tags from mainColumnData.

	Args:
		main_column: The mainColumnData dict from __NEXT_DATA__.

	Returns:
		list: List of keyword strings.
	"""
	keyword_edges = _safe_get(main_column, "keywords", "edges", default=[])
	tags = []
	for edge in keyword_edges:
		kw = _safe_get(edge, "node", "text", default="")
		if kw:
			tags.append(kw)
	return tags


#============================================
class ImdbScraper(moviemanager.scraper.interfaces.MetadataProvider):
	"""IMDB scraper using CDN suggestion API and QWebEnginePage transport.

	Search uses the WAF-free CDN suggestion API for fast results.
	Parental guide and metadata pages are loaded via the browser
	transport which handles WAF JavaScript challenges automatically.
	"""

	#============================================
	def __init__(self):
		"""Initialize the IMDB scraper."""
		self._transport = None

	#============================================
	def set_transport(self, transport) -> None:
		"""Set the browser transport for loading IMDB pages.

		Args:
			transport: ImdbBrowserTransport instance.
		"""
		self._transport = transport

	#============================================
	def search(self, title: str, year: str = "") -> list:
		"""Search IMDB for movies matching a title and optional year.

		Uses the CDN suggestion API which has no WAF protection.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			list: List of SearchResult dataclasses.
		"""
		# build search query with optional year
		query = title
		if year:
			query = f"{title} {year}"
		entries = _fetch_suggestion(query)
		results = _parse_suggestion_results(entries)
		return results

	#============================================
	def get_metadata(
		self, tmdb_id: int = 0, imdb_id: str = ""
	) -> moviemanager.scraper.types.MediaMetadata:
		"""Fetch full metadata for a movie from IMDB.

		Uses the browser transport to load the title page, then
		parses __NEXT_DATA__ JSON for structured metadata.

		Args:
			tmdb_id: TMDB movie ID (not used by IMDB scraper).
			imdb_id: IMDB movie ID (tt format).

		Returns:
			MediaMetadata: Complete movie metadata.

		Raises:
			ValueError: If no imdb_id is provided.
			ConnectionError: If transport is not set or page load fails.
		"""
		if not imdb_id:
			raise ValueError("IMDB scraper requires an imdb_id")
		if self._transport is None:
			raise ConnectionError(
				"IMDB browser transport not configured. "
				"Cannot fetch metadata without browser transport."
			)
		# rate limit before transport call
		time.sleep(1 + random.random())
		url = f"{_IMDB_BASE}/title/{imdb_id}/"
		html = self._transport.fetch_html(url)
		metadata = _parse_metadata_html(html, imdb_id)
		return metadata

	#============================================
	def get_parental_guide(self, imdb_id: str) -> dict:
		"""Fetch parental guide data for a movie.

		Uses the browser transport to load the parental guide page,
		then parses the severity data from __NEXT_DATA__ JSON.

		Args:
			imdb_id: IMDB movie ID (tt format).

		Returns:
			dict: Category name to severity string mapping.
		"""
		if not imdb_id:
			return {}
		if self._transport is None:
			_LOG.warning(
				"IMDB browser transport not configured, "
				"cannot fetch parental guide for %s", imdb_id,
			)
			return {}
		# rate limit before transport call
		time.sleep(1 + random.random())
		url = f"{_IMDB_BASE}/title/{imdb_id}/parentalguide"
		html = self._transport.fetch_html(url)
		guide = _parse_parental_guide_html(html)
		return guide


# simple assertion for _upgrade_poster_url
assert _upgrade_poster_url(
	"https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg"
) == "https://m.media-amazon.com/images/M/abc._V1_.jpg"
assert _upgrade_poster_url(
	"https://m.media-amazon.com/images/M/abc._V1_.jpg"
) == "https://m.media-amazon.com/images/M/abc._V1_.jpg"
assert _upgrade_poster_url("") == ""
