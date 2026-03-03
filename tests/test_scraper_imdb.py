"""Unit tests for the IMDB GraphQL scraper with mocked network calls.

Tests cover search, get_metadata, parental guide parsing, cast extraction,
WAF detection, poster URL cleanup, and cookie injection.
"""

# Standard Library
import os
import sys
import unittest.mock

# PIP3 modules
import pytest

# add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types


# ---- sample GraphQL response fixtures ----

# minimal metadata response for Clerks (tt0109445)
SAMPLE_METADATA_RESPONSE = {
	"data": {
		"title": {
			"titleText": {"text": "Clerks"},
			"originalTitleText": {"text": "Clerks"},
			"releaseYear": {"year": 1994},
			"releaseDate": {"day": 9, "month": 11, "year": 1994},
			"ratingsSummary": {
				"aggregateRating": 7.7,
				"voteCount": 239766,
				"topRanking": {"rank": 920},
			},
			"plot": {
				"plotText": {
					"plainText": "A day in the lives of two convenience clerks."
				}
			},
			"runtime": {"seconds": 5520},
			"certificate": {"rating": "R"},
			"genres": {"genres": [{"text": "Comedy"}]},
			"primaryImage": {
				"url": "https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg"
			},
			"taglines": {
				"edges": [{"node": {"text": "Just because they serve you..."}}]
			},
			"countriesOfOrigin": {
				"countries": [{"id": "US", "text": "United States"}]
			},
			"spokenLanguages": {
				"spokenLanguages": [{"id": "en", "text": "English"}]
			},
			"companyCredits": {
				"edges": [
					{
						"node": {
							"company": {"companyText": {"text": "View Askew Productions"}},
							"category": {"text": "Production Companies"},
						}
					},
					{
						"node": {
							"company": {"companyText": {"text": "Miramax"}},
							"category": {"text": "Distributors"},
						}
					},
				]
			},
			"principalCredits": [
				{
					"category": {"text": "Director"},
					"credits": [
						{
							"name": {
								"id": "nm0003620",
								"nameText": {"text": "Kevin Smith"},
								"primaryImage": {"url": "https://example.com/smith._V1_.jpg"},
							}
						}
					],
				},
				{
					"category": {"text": "Writer"},
					"credits": [
						{
							"name": {
								"id": "nm0003620",
								"nameText": {"text": "Kevin Smith"},
								"primaryImage": None,
							}
						}
					],
				},
				{
					"category": {"text": "Stars"},
					"credits": [
						{
							"name": {
								"id": "nm0004778",
								"nameText": {"text": "Brian O'Halloran"},
								"primaryImage": {"url": "https://example.com/brian._V1_.jpg"},
							},
							"characters": [{"name": "Dante Hicks"}],
						},
						{
							"name": {
								"id": "nm0000492",
								"nameText": {"text": "Jeff Anderson"},
								"primaryImage": None,
							},
							"characters": [{"name": "Randal Graves"}],
						},
					],
				},
				{
					"category": {"text": "Producers"},
					"credits": [
						{
							"name": {
								"id": "nm0588201",
								"nameText": {"text": "Scott Mosier"},
								"primaryImage": None,
							}
						}
					],
				},
			],
			"keywords": {
				"edges": [
					{"node": {"text": "convenience store"}},
					{"node": {"text": "slacker"}},
				]
			},
			"parentsGuide": {
				"categories": [
					{"category": {"text": "Sex & Nudity"}, "severity": {"text": "Moderate"}},
					{"category": {"text": "Violence & Gore"}, "severity": {"text": "Mild"}},
					{"category": {"text": "Profanity"}, "severity": {"text": "Severe"}},
					{"category": {"text": "Alcohol, Drugs & Smoking"}, "severity": {"text": "Moderate"}},
					{"category": {"text": "Frightening & Intense Scenes"}, "severity": {"text": "Mild"}},
				]
			},
		}
	}
}

# minimal search response
SAMPLE_SEARCH_RESPONSE = {
	"data": {
		"mainSearch": {
			"edges": [
				{
					"node": {
						"entity": {
							"id": "tt0109445",
							"titleText": {"text": "Clerks"},
							"originalTitleText": {"text": "Clerks"},
							"releaseYear": {"year": 1994},
							"primaryImage": {
								"url": "https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg"
							},
							"plot": {
								"plotText": {"plainText": "Two clerks work at a store."}
							},
							"ratingsSummary": {"aggregateRating": 7.7},
							"titleType": {"text": "Movie"},
						}
					}
				},
				{
					"node": {
						"entity": {
							"id": "tt12629970",
							"titleText": {"text": "Clerks (1994)"},
							"originalTitleText": {"text": "Clerks (1994)"},
							"releaseYear": {"year": 2018},
							"primaryImage": None,
							"plot": None,
							"ratingsSummary": {"aggregateRating": None},
							"titleType": {"text": "TV Episode"},
						}
					}
				},
			]
		}
	}
}


#============================================
class MockResponse:
	"""Mock curl_cffi response object."""

	def __init__(self, status_code: int, json_data: dict):
		"""Set up mock response.

		Args:
			status_code: HTTP status code.
			json_data: Dict to return from json().
		"""
		self.status_code = status_code
		self._json_data = json_data

	def json(self) -> dict:
		"""Return the mock JSON data."""
		return self._json_data

	def raise_for_status(self) -> None:
		"""Raise if status >= 400."""
		if self.status_code >= 400:
			raise Exception(f"HTTP {self.status_code}")


#============================================
# Tests for _upgrade_poster_url
#============================================

def test_upgrade_poster_url_removes_resize():
	"""Resize parameters are stripped from poster URLs."""
	url = "https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg"
	result = moviemanager.scraper.imdb_scraper._upgrade_poster_url(url)
	expected = "https://m.media-amazon.com/images/M/abc._V1_.jpg"
	assert result == expected


#============================================
def test_upgrade_poster_url_keeps_clean():
	"""Already-clean URLs are returned unchanged."""
	url = "https://m.media-amazon.com/images/M/abc._V1_.jpg"
	result = moviemanager.scraper.imdb_scraper._upgrade_poster_url(url)
	assert result == url


#============================================
def test_upgrade_poster_url_empty():
	"""Empty input returns empty string."""
	result = moviemanager.scraper.imdb_scraper._upgrade_poster_url("")
	assert result == ""


#============================================
def test_upgrade_poster_url_complex_resize():
	"""Complex resize suffixes like _UY300_CR0,0,200,300_ are stripped."""
	url = "https://m.media-amazon.com/images/M/movie._V1_UY300_CR0,0,200,300_.jpg"
	result = moviemanager.scraper.imdb_scraper._upgrade_poster_url(url)
	expected = "https://m.media-amazon.com/images/M/movie._V1_.jpg"
	assert result == expected


#============================================
# Tests for _safe_get
#============================================

def test_safe_get_nested():
	"""Nested dict traversal returns correct value."""
	data = {"a": {"b": {"c": 42}}}
	result = moviemanager.scraper.imdb_scraper._safe_get(data, "a", "b", "c")
	assert result == 42


#============================================
def test_safe_get_missing_key():
	"""Missing intermediate key returns default."""
	data = {"a": {"x": 1}}
	result = moviemanager.scraper.imdb_scraper._safe_get(
		data, "a", "b", "c", default="missing"
	)
	assert result == "missing"


#============================================
def test_safe_get_none_value():
	"""None intermediate value returns default."""
	data = {"a": None}
	result = moviemanager.scraper.imdb_scraper._safe_get(
		data, "a", "b", default="fallback"
	)
	assert result == "fallback"


#============================================
# Tests for parental guide parsing
#============================================

def test_parse_parental_guide():
	"""Parental guide categories are extracted correctly."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	result = moviemanager.scraper.imdb_scraper._parse_graphql_parental_guide(
		title_data
	)
	assert "Sex & Nudity" in result
	assert result["Sex & Nudity"] == "Moderate"
	assert "Profanity" in result
	assert result["Profanity"] == "Severe"
	assert len(result) == 5


#============================================
def test_parse_parental_guide_empty():
	"""Empty parental guide data returns empty dict."""
	result = moviemanager.scraper.imdb_scraper._parse_graphql_parental_guide({})
	assert result == {}


#============================================
# Tests for cast extraction
#============================================

def test_parse_cast():
	"""Cast members with character roles are extracted."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	actors = moviemanager.scraper.imdb_scraper._parse_graphql_cast(title_data)
	assert len(actors) == 2
	# first actor
	assert actors[0].name == "Brian O'Halloran"
	assert actors[0].role == "Dante Hicks"
	assert actors[0].department == "Acting"
	assert actors[0].imdb_id == "nm0004778"
	# second actor
	assert actors[1].name == "Jeff Anderson"
	assert actors[1].role == "Randal Graves"


#============================================
def test_parse_cast_empty():
	"""No principalCredits returns empty actor list."""
	actors = moviemanager.scraper.imdb_scraper._parse_graphql_cast({})
	assert actors == []


#============================================
# Tests for principal credits extraction
#============================================

def test_extract_director():
	"""Director is extracted from principalCredits."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	director = moviemanager.scraper.imdb_scraper._extract_principal_credits(
		title_data, "Director"
	)
	assert director == "Kevin Smith"


#============================================
def test_extract_writer():
	"""Writer is extracted from principalCredits."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	writer = moviemanager.scraper.imdb_scraper._extract_principal_credits(
		title_data, "Writer"
	)
	assert writer == "Kevin Smith"


#============================================
def test_extract_missing_category():
	"""Missing category returns empty string."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	result = moviemanager.scraper.imdb_scraper._extract_principal_credits(
		title_data, "Cinematographer"
	)
	assert result == ""


#============================================
# Tests for producers extraction
#============================================

def test_extract_producers():
	"""Producers are extracted with Production department."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	producers = moviemanager.scraper.imdb_scraper._extract_producers(title_data)
	assert len(producers) == 1
	assert producers[0].name == "Scott Mosier"
	assert producers[0].department == "Production"
	assert producers[0].imdb_id == "nm0588201"


#============================================
# Tests for studio extraction
#============================================

def test_extract_studio():
	"""Production company is extracted, not distributors."""
	title_data = SAMPLE_METADATA_RESPONSE["data"]["title"]
	studio = moviemanager.scraper.imdb_scraper._extract_studio(title_data)
	assert studio == "View Askew Productions"


#============================================
def test_extract_studio_empty():
	"""Empty companyCredits returns empty string."""
	studio = moviemanager.scraper.imdb_scraper._extract_studio({})
	assert studio == ""


#============================================
# Tests for full metadata parsing
#============================================

def test_parse_metadata_all_fields():
	"""Full metadata parsing populates all expected fields."""
	data = SAMPLE_METADATA_RESPONSE["data"]
	metadata = moviemanager.scraper.imdb_scraper._parse_graphql_metadata(
		data, "tt0109445"
	)
	assert metadata.title == "Clerks"
	assert metadata.original_title == "Clerks"
	assert metadata.year == "1994"
	assert metadata.release_date == "1994-11-09"
	assert metadata.rating == 7.7
	assert metadata.votes == 239766
	assert metadata.runtime == 92
	assert metadata.certification == "R"
	assert metadata.genres == ["Comedy"]
	assert metadata.director == "Kevin Smith"
	assert metadata.writer == "Kevin Smith"
	assert metadata.studio == "View Askew Productions"
	assert metadata.country == "United States"
	assert metadata.spoken_languages == "English"
	assert metadata.imdb_id == "tt0109445"
	assert metadata.media_source == "imdb"
	# poster URL should have resize params stripped
	assert metadata.poster_url.endswith("._V1_.jpg")
	assert "UX300" not in metadata.poster_url
	# tagline
	assert "Just because" in metadata.tagline
	# tags/keywords
	assert "convenience store" in metadata.tags
	assert "slacker" in metadata.tags
	# parental guide
	assert len(metadata.parental_guide) == 5
	assert metadata.parental_guide["Profanity"] == "Severe"
	# actors
	assert len(metadata.actors) == 2
	assert metadata.actors[0].name == "Brian O'Halloran"
	# producers
	assert len(metadata.producers) == 1
	assert metadata.producers[0].name == "Scott Mosier"


#============================================
def test_parse_metadata_empty_response():
	"""Empty title data returns metadata with defaults."""
	data = {"title": {}}
	metadata = moviemanager.scraper.imdb_scraper._parse_graphql_metadata(
		data, "tt0000000"
	)
	assert metadata.title == ""
	assert metadata.year == ""
	assert metadata.rating == 0.0
	assert metadata.votes == 0
	assert metadata.runtime == 0
	assert metadata.genres == []
	assert metadata.actors == []
	assert metadata.imdb_id == "tt0000000"
	assert metadata.media_source == "imdb"


#============================================
# Tests for WAF detection
#============================================

def test_waf_detection_raises_connection_error():
	"""HTTP 202 from GraphQL raises ConnectionError with WAF message."""
	mock_response = MockResponse(202, {})
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	):
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		with pytest.raises(ConnectionError, match="AWS WAF challenge"):
			scraper.get_metadata(imdb_id="tt0109445")


#============================================
# Tests for search
#============================================

def test_search_returns_movies_only():
	"""Search filters out non-Movie types like TV Episode."""
	mock_response = MockResponse(200, SAMPLE_SEARCH_RESPONSE)
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	):
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		results = scraper.search("Clerks", year="1994")
	# only the Movie result, not the TV Episode
	assert len(results) == 1
	assert results[0].title == "Clerks"
	assert results[0].imdb_id == "tt0109445"
	assert results[0].year == "1994"
	assert results[0].score == 7.7


#============================================
def test_search_poster_url_cleaned():
	"""Search result poster URLs have resize params stripped."""
	mock_response = MockResponse(200, SAMPLE_SEARCH_RESPONSE)
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	):
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		results = scraper.search("Clerks")
	assert len(results) >= 1
	assert results[0].poster_url.endswith("._V1_.jpg")


#============================================
def test_search_empty_results():
	"""Empty search response returns empty list."""
	empty_response = {"data": {"mainSearch": {"edges": []}}}
	mock_response = MockResponse(200, empty_response)
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	):
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		results = scraper.search("xyznonexistent")
	assert results == []


#============================================
# Tests for get_metadata
#============================================

def test_get_metadata_calls_graphql():
	"""get_metadata sends correct IMDB ID to GraphQL."""
	mock_response = MockResponse(200, SAMPLE_METADATA_RESPONSE)
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	) as mock_post:
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		metadata = scraper.get_metadata(imdb_id="tt0109445")
	# verify the call was made
	assert mock_post.called
	# verify result
	assert metadata.title == "Clerks"
	assert metadata.imdb_id == "tt0109445"


#============================================
def test_get_metadata_requires_imdb_id():
	"""get_metadata raises ValueError when no imdb_id is given."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	with pytest.raises(ValueError, match="requires an imdb_id"):
		scraper.get_metadata()


#============================================
# Tests for set_cookies
#============================================

def test_set_cookies_injects_into_session():
	"""set_cookies adds cookies to the curl_cffi session."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	test_cookies = [
		{"name": "session-id", "value": "abc123", "domain": ".imdb.com"},
		{"name": "ubid-main", "value": "def456", "domain": ".imdb.com"},
	]
	scraper.set_cookies(test_cookies)
	# verify cookies are in the session jar
	jar = scraper._session.cookies
	assert jar.get("session-id") == "abc123"
	assert jar.get("ubid-main") == "def456"


#============================================
def test_set_cookies_empty_list():
	"""set_cookies with empty list does not crash."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	scraper.set_cookies([])


#============================================
# Tests for top250 extraction
#============================================

def test_top250_within_range():
	"""Top ranking <= 250 is captured as top250."""
	data = {"title": {
		"ratingsSummary": {"topRanking": {"rank": 42}, "aggregateRating": 8.5, "voteCount": 1000},
	}}
	metadata = moviemanager.scraper.imdb_scraper._parse_graphql_metadata(data, "tt0000001")
	assert metadata.top250 == 42


#============================================
def test_top250_above_range():
	"""Top ranking > 250 is set to zero."""
	data = {"title": {
		"ratingsSummary": {"topRanking": {"rank": 920}, "aggregateRating": 7.7, "voteCount": 200000},
	}}
	metadata = moviemanager.scraper.imdb_scraper._parse_graphql_metadata(data, "tt0000002")
	assert metadata.top250 == 0


#============================================
# Tests for get_parental_guide
#============================================

def test_get_parental_guide_mocked():
	"""get_parental_guide returns parsed category-to-severity mapping."""
	mock_graphql_response = {
		"data": {
			"title": {
				"parentsGuide": {
					"categories": [
						{"category": {"text": "Sex & Nudity"}, "severity": {"text": "Mild"}},
						{"category": {"text": "Violence & Gore"}, "severity": {"text": "Moderate"}},
						{"category": {"text": "Profanity"}, "severity": {"text": "Mild"}},
					]
				}
			}
		}
	}
	mock_response = MockResponse(200, mock_graphql_response)
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	):
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		guide = scraper.get_parental_guide("tt0109445")
	assert len(guide) == 3
	assert guide["Sex & Nudity"] == "Mild"
	assert guide["Violence & Gore"] == "Moderate"
	assert guide["Profanity"] == "Mild"


#============================================
def test_get_parental_guide_empty_id():
	"""get_parental_guide returns empty dict when no imdb_id is given."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	guide = scraper.get_parental_guide("")
	assert guide == {}


#============================================
def test_get_parental_guide_no_data():
	"""get_parental_guide returns empty dict when no guide data exists."""
	mock_graphql_response = {
		"data": {
			"title": {
				"parentsGuide": None
			}
		}
	}
	mock_response = MockResponse(200, mock_graphql_response)
	with unittest.mock.patch.object(
		moviemanager.scraper.imdb_scraper.curl_cffi.requests.Session,
		"post",
		return_value=mock_response,
	):
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		guide = scraper.get_parental_guide("tt0000001")
	assert guide == {}
