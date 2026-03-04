"""IMDB parental guide scraper using GraphQL API with curl_cffi fallback.

Primary transport is the IMDB GraphQL API via curl_cffi with Chrome TLS
impersonation (fast, no HTML parsing needed). Falls back to QWebEnginePage
browser transport for HTML page parsing only when the GraphQL request
itself fails (network error, non-200 status).
"""

# Standard Library
import re
import json
import time
import random
import logging

# PIP3 modules
import curl_cffi.requests

# local repo modules
import moviemanager.scraper.interfaces


# module logger
_LOG = logging.getLogger(__name__)

# IMDB base URL for page loads via transport
_IMDB_BASE = "https://www.imdb.com"


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
def _fetch_parental_guide_graphql(imdb_id: str) -> dict:
	"""Fetch parental guide via IMDB GraphQL API with curl_cffi.

	Calls the IMDB GraphQL endpoint directly instead of scraping HTML.
	This is faster and more reliable than parsing __NEXT_DATA__ from
	the parental guide page, which no longer contains severity data.

	Args:
		imdb_id: IMDB movie ID (tt format).

	Returns:
		dict: Category name to severity string mapping, or empty dict
		      if the movie has no parental guide data on IMDB.

	Raises:
		ConnectionError: If the GraphQL request fails (network error,
		                 non-200 status, or unexpected response structure).
	"""
	graphql_url = "https://api.graphql.imdb.com/"
	# GraphQL query for parental guide severity data
	query = (
		"query ParentsGuide($titleId: ID!) {"
		"  title(id: $titleId) {"
		"    parentsGuide {"
		"      categories {"
		"        category { id text }"
		"        severity { text }"
		"      }"
		"    }"
		"  }"
		"}"
	)
	payload = {
		"query": query,
		"variables": {"titleId": imdb_id},
	}
	# rate-limit courtesy pause
	time.sleep(random.random())
	response = curl_cffi.requests.post(
		graphql_url, json=payload, impersonate="chrome", timeout=15,
	)
	if response.status_code != 200:
		msg = f"IMDB GraphQL returned HTTP {response.status_code} for {imdb_id}"
		_LOG.warning(msg)
		raise ConnectionError(msg)
	data = response.json()
	# navigate to categories list
	categories = _safe_get(
		data, "data", "title", "parentsGuide", "categories", default=None
	)
	# categories is null when the movie has no parental guide data
	if categories is None:
		return {}
	guide = {}
	for cat in categories:
		cat_name = _safe_get(cat, "category", "text", default="")
		severity = _safe_get(cat, "severity", "text", default="")
		if cat_name and severity:
			guide[cat_name] = severity
	return guide


#============================================
class ImdbParentalGuideScraper(
	moviemanager.scraper.interfaces.ParentalGuideProvider,
):
	"""IMDB parental guide scraper using GraphQL API and browser fallback.

	Primary transport is the IMDB GraphQL API via curl_cffi with Chrome
	TLS impersonation. Falls back to QWebEnginePage browser transport
	for HTML parsing only when the GraphQL request fails.
	"""

	# capabilities advertised by this scraper
	capabilities = {
		moviemanager.scraper.interfaces.ProviderCapability.PARENTAL_GUIDE,
	}

	# no API keys required (uses GraphQL API with curl_cffi)
	requires_keys = []

	#============================================
	def __init__(self):
		"""Initialize the parental guide scraper."""
		self._transport = None

	#============================================
	def set_transport(self, transport) -> None:
		"""Set the browser transport for fallback HTML page loading.

		Args:
			transport: ImdbBrowserTransport instance.
		"""
		self._transport = transport

	#============================================
	def get_parental_guide(self, imdb_id: str) -> dict:
		"""Fetch parental guide data for a movie via IMDB GraphQL API.

		Uses the GraphQL API via curl_cffi as the primary (and usually
		only) transport. Falls back to the QWebEnginePage browser
		transport only if the GraphQL request itself fails (network
		error, non-200 status).

		Args:
			imdb_id: IMDB movie ID (tt format).

		Returns:
			dict: Category name to severity string mapping.
		"""
		if not imdb_id:
			return {}
		# try GraphQL API first -- fast, no HTML parsing needed
		try:
			guide = _fetch_parental_guide_graphql(imdb_id)
		except ConnectionError:
			guide = None
		# GraphQL succeeded
		if guide is not None:
			if guide:
				_LOG.info(
					"Parental guide for %s fetched via GraphQL API",
					imdb_id,
				)
			else:
				# empty dict means movie has no parental guide on IMDB
				_LOG.info(
					"No parental guide data available on IMDB for %s",
					imdb_id,
				)
			return guide
		# GraphQL request failed; fall back to browser transport
		_LOG.info(
			"GraphQL API failed for %s, falling back to browser transport",
			imdb_id,
		)
		if self._transport is None:
			_LOG.warning(
				"IMDB browser transport not configured, "
				"cannot fetch parental guide for %s", imdb_id,
			)
			return {}
		# rate limit before transport call
		time.sleep(1 + random.random())
		url = f"{_IMDB_BASE}/title/{imdb_id}/parentalguide"
		# use shorter timeout; WAF failures at 30s waste wall-clock time
		html = self._transport.fetch_html(url, timeout_sec=15)
		guide = _parse_parental_guide_html(html)
		return guide
