"""Unit tests for the IMDB scraper with CDN suggestion API and HTML parsing.

Tests cover suggestion search, __NEXT_DATA__ metadata parsing, parental guide
HTML parsing, cast extraction, poster URL cleanup, and transport integration.
"""

# Standard Library
import os
import sys
import json
import unittest.mock

# PIP3 modules
import pytest

# add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types


# ---- sample CDN suggestion API fixtures ----

SAMPLE_SUGGESTION_RESPONSE = {
	"d": [
		{
			"id": "tt0109445",
			"l": "Clerks",
			"qid": "movie",
			"rank": 2345,
			"y": 1994,
			"i": {
				"imageUrl": "https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg",
				"width": 300,
				"height": 450,
			},
		},
		{
			"id": "tt0305056",
			"l": "Clerks II",
			"qid": "movie",
			"rank": 5678,
			"y": 2006,
			"i": {
				"imageUrl": "https://m.media-amazon.com/images/M/def._V1_.jpg",
				"width": 300,
				"height": 450,
			},
		},
		{
			"id": "tt12629970",
			"l": "Clerks (1994)",
			"qid": "tvEpisode",
			"rank": 99999,
			"y": 2018,
		},
		{
			"id": "nm0003620",
			"l": "Kevin Smith",
			"qid": "",
			"rank": 1000,
		},
	],
	"q": "clerks",
	"v": 1,
}

# ---- sample __NEXT_DATA__ fixtures for title page ----

SAMPLE_NEXT_DATA_TITLE = {
	"props": {
		"pageProps": {
			"aboveTheFoldData": {
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
				"parentsGuide": {
					"categories": [
						{"category": {"text": "Sex & Nudity"}, "severity": {"text": "Moderate"}},
						{"category": {"text": "Violence & Gore"}, "severity": {"text": "Mild"}},
						{"category": {"text": "Profanity"}, "severity": {"text": "Severe"}},
						{"category": {"text": "Alcohol, Drugs & Smoking"}, "severity": {"text": "Moderate"}},
						{"category": {"text": "Frightening & Intense Scenes"}, "severity": {"text": "Mild"}},
					]
				},
			},
			"mainColumnData": {
				"cast": {
					"edges": [
						{
							"node": {
								"name": {"id": "nm0004778"},
								"characters": [{"name": "Dante Hicks"}],
							}
						},
						{
							"node": {
								"name": {"id": "nm0000492"},
								"characters": [{"name": "Randal Graves"}],
							}
						},
					]
				},
				"keywords": {
					"edges": [
						{"node": {"text": "convenience store"}},
						{"node": {"text": "slacker"}},
					]
				},
			},
		}
	}
}

# ---- sample __NEXT_DATA__ for parental guide page ----

SAMPLE_NEXT_DATA_PARENTAL_GUIDE = {
	"props": {
		"pageProps": {
			"contentData": {
				"section": {
					"items": [
						{
							"id": "advisory-nudity",
							"severityVote": {"severity": "Moderate"},
						},
						{
							"id": "advisory-violence",
							"severityVote": {"severity": "Mild"},
						},
						{
							"id": "advisory-profanity",
							"severityVote": {"severity": "Severe"},
						},
						{
							"id": "advisory-alcohol",
							"severityVote": {"severity": "Moderate"},
						},
						{
							"id": "advisory-frightening",
							"severityVote": {"severity": "Mild"},
						},
					]
				}
			}
		}
	}
}


#============================================
def _make_title_html(next_data: dict) -> str:
	"""Build a minimal IMDB page HTML with __NEXT_DATA__ script tag.

	Args:
		next_data: Dict to serialize as __NEXT_DATA__ JSON.

	Returns:
		str: HTML string with embedded __NEXT_DATA__.
	"""
	json_str = json.dumps(next_data)
	html = (
		"<html><head>"
		'<script id="__NEXT_DATA__" type="application/json">'
		+ json_str
		+ "</script>"
		"</head><body></body></html>"
	)
	return html


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
# Tests for CDN suggestion API parsing
#============================================

def test_parse_suggestion_results_filters_movies():
	"""Suggestion parser filters to movie types, excludes TV episodes and people."""
	entries = SAMPLE_SUGGESTION_RESPONSE["d"]
	results = moviemanager.scraper.imdb_scraper._parse_suggestion_results(entries)
	# only the two movies, not the TV episode or person
	assert len(results) == 2
	assert results[0].title == "Clerks"
	assert results[0].imdb_id == "tt0109445"
	assert results[0].year == "1994"
	assert results[1].title == "Clerks II"
	assert results[1].imdb_id == "tt0305056"
	assert results[1].year == "2006"


#============================================
def test_parse_suggestion_poster_url_cleaned():
	"""Suggestion result poster URLs have resize params stripped."""
	entries = SAMPLE_SUGGESTION_RESPONSE["d"]
	results = moviemanager.scraper.imdb_scraper._parse_suggestion_results(entries)
	assert results[0].poster_url.endswith("._V1_.jpg")
	assert "UX300" not in results[0].poster_url


#============================================
def test_parse_suggestion_empty():
	"""Empty suggestion list returns empty results."""
	results = moviemanager.scraper.imdb_scraper._parse_suggestion_results([])
	assert results == []


#============================================
def test_parse_suggestion_no_image():
	"""Suggestion entry without image gets empty poster URL."""
	entries = [
		{
			"id": "tt9999999",
			"l": "No Poster Movie",
			"qid": "movie",
			"rank": 50000,
			"y": 2020,
		}
	]
	results = moviemanager.scraper.imdb_scraper._parse_suggestion_results(entries)
	assert len(results) == 1
	assert results[0].poster_url == ""


#============================================
def test_parse_suggestion_score_from_rank():
	"""Suggestion results compute a popularity score from rank."""
	entries = SAMPLE_SUGGESTION_RESPONSE["d"]
	results = moviemanager.scraper.imdb_scraper._parse_suggestion_results(entries)
	# lower rank = more popular = higher score
	assert results[0].score > results[1].score
	# scores are in 0-10 range
	assert 0.0 <= results[0].score <= 10.0


#============================================
def test_search_uses_suggestion_api():
	"""Search delegates to CDN suggestion API."""
	mock_response = unittest.mock.Mock()
	mock_response.status_code = 200
	mock_response.json.return_value = SAMPLE_SUGGESTION_RESPONSE
	with unittest.mock.patch(
		"moviemanager.scraper.imdb_scraper.requests.get",
		return_value=mock_response,
	) as mock_get:
		scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
		results = scraper.search("Clerks", year="1994")
	# verify suggestion API was called
	assert mock_get.called
	call_url = mock_get.call_args[0][0]
	assert "suggestion" in call_url
	# verify results parsed correctly
	assert len(results) == 2
	assert results[0].title == "Clerks"


#============================================
def test_search_empty_title():
	"""Search with empty title returns empty list without calling API."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	# _fetch_suggestion returns [] for empty query, no HTTP call needed
	with unittest.mock.patch(
		"moviemanager.scraper.imdb_scraper.requests.get",
	) as mock_get:
		results = scraper.search("")
	# should not make any HTTP calls
	assert not mock_get.called
	assert results == []


#============================================
# Tests for __NEXT_DATA__ extraction
#============================================

def test_extract_next_data_json():
	"""__NEXT_DATA__ JSON is extracted from HTML."""
	html = _make_title_html({"test": "value"})
	result = moviemanager.scraper.imdb_scraper._extract_next_data_json(html)
	assert result == {"test": "value"}


#============================================
def test_extract_next_data_missing():
	"""Missing __NEXT_DATA__ returns empty dict."""
	html = "<html><body>No data</body></html>"
	result = moviemanager.scraper.imdb_scraper._extract_next_data_json(html)
	assert result == {}


#============================================
# Tests for metadata HTML parsing
#============================================

def test_parse_metadata_all_fields():
	"""Full metadata parsing populates all expected fields."""
	html = _make_title_html(SAMPLE_NEXT_DATA_TITLE)
	metadata = moviemanager.scraper.imdb_scraper._parse_metadata_html(
		html, "tt0109445"
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
	assert metadata.actors[0].role == "Dante Hicks"
	assert metadata.actors[0].department == "Acting"
	# producers
	assert len(metadata.producers) == 1
	assert metadata.producers[0].name == "Scott Mosier"


#============================================
def test_parse_metadata_empty_html():
	"""HTML without __NEXT_DATA__ returns minimal metadata."""
	html = "<html><body>Nothing here</body></html>"
	metadata = moviemanager.scraper.imdb_scraper._parse_metadata_html(
		html, "tt0000000"
	)
	assert metadata.title == ""
	assert metadata.year == ""
	assert metadata.imdb_id == "tt0000000"
	assert metadata.media_source == "imdb"


#============================================
def test_parse_metadata_empty_next_data():
	"""Empty __NEXT_DATA__ returns metadata with defaults."""
	html = _make_title_html({"props": {"pageProps": {}}})
	metadata = moviemanager.scraper.imdb_scraper._parse_metadata_html(
		html, "tt0000000"
	)
	assert metadata.title == ""
	assert metadata.year == ""
	assert metadata.rating == 0.0
	assert metadata.votes == 0
	assert metadata.runtime == 0
	assert metadata.genres == []
	assert metadata.actors == []
	assert metadata.imdb_id == "tt0000000"


#============================================
# Tests for cast extraction
#============================================

def test_parse_cast():
	"""Cast members with character roles are extracted."""
	above_fold = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["aboveTheFoldData"]
	main_column = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["mainColumnData"]
	actors = moviemanager.scraper.imdb_scraper._parse_cast(
		above_fold, main_column
	)
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
	actors = moviemanager.scraper.imdb_scraper._parse_cast({}, {})
	assert actors == []


#============================================
# Tests for principal credits extraction
#============================================

def test_extract_director():
	"""Director is extracted from principalCredits."""
	above_fold = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["aboveTheFoldData"]
	director = moviemanager.scraper.imdb_scraper._extract_principal_credits(
		above_fold, "Director"
	)
	assert director == "Kevin Smith"


#============================================
def test_extract_writer():
	"""Writer is extracted from principalCredits."""
	above_fold = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["aboveTheFoldData"]
	writer = moviemanager.scraper.imdb_scraper._extract_principal_credits(
		above_fold, "Writer"
	)
	assert writer == "Kevin Smith"


#============================================
def test_extract_missing_category():
	"""Missing category returns empty string."""
	above_fold = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["aboveTheFoldData"]
	result = moviemanager.scraper.imdb_scraper._extract_principal_credits(
		above_fold, "Cinematographer"
	)
	assert result == ""


#============================================
# Tests for producers extraction
#============================================

def test_extract_producers():
	"""Producers are extracted with Production department."""
	above_fold = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["aboveTheFoldData"]
	producers = moviemanager.scraper.imdb_scraper._extract_producers(above_fold)
	assert len(producers) == 1
	assert producers[0].name == "Scott Mosier"
	assert producers[0].department == "Production"
	assert producers[0].imdb_id == "nm0588201"


#============================================
# Tests for studio extraction
#============================================

def test_extract_studio():
	"""Production company is extracted, not distributors."""
	above_fold = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["aboveTheFoldData"]
	studio = moviemanager.scraper.imdb_scraper._extract_studio(above_fold)
	assert studio == "View Askew Productions"


#============================================
def test_extract_studio_empty():
	"""Empty companyCredits returns empty string."""
	studio = moviemanager.scraper.imdb_scraper._extract_studio({})
	assert studio == ""


#============================================
# Tests for parental guide HTML parsing
#============================================

def test_parse_parental_guide_html():
	"""Parental guide categories are extracted from HTML page."""
	html = _make_title_html(SAMPLE_NEXT_DATA_PARENTAL_GUIDE)
	result = moviemanager.scraper.imdb_scraper._parse_parental_guide_html(html)
	assert "Sex & Nudity" in result
	assert result["Sex & Nudity"] == "Moderate"
	assert "Profanity" in result
	assert result["Profanity"] == "Severe"
	assert len(result) == 5


#============================================
def test_parse_parental_guide_html_empty():
	"""Empty HTML returns empty parental guide."""
	html = "<html><body>No data</body></html>"
	result = moviemanager.scraper.imdb_scraper._parse_parental_guide_html(html)
	assert result == {}


#============================================
def test_parse_parental_guide_fallback_above_fold():
	"""Parental guide falls back to aboveTheFoldData format."""
	# use the title page format which has guide in aboveTheFoldData
	html = _make_title_html(SAMPLE_NEXT_DATA_TITLE)
	# the parental guide parser should find data in fallback path
	result = moviemanager.scraper.imdb_scraper._parse_parental_guide_html(html)
	# should find data from the aboveTheFoldData fallback
	assert len(result) == 5
	assert result["Profanity"] == "Severe"


#============================================
def test_advisory_id_to_name():
	"""Advisory IDs map to display names correctly."""
	assert moviemanager.scraper.imdb_scraper._advisory_id_to_name(
		"advisory-nudity"
	) == "Sex & Nudity"
	assert moviemanager.scraper.imdb_scraper._advisory_id_to_name(
		"advisory-violence"
	) == "Violence & Gore"
	assert moviemanager.scraper.imdb_scraper._advisory_id_to_name(
		"unknown-id"
	) == ""


#============================================
# Tests for keyword extraction
#============================================

def test_extract_keywords():
	"""Keywords are extracted from mainColumnData."""
	main_column = SAMPLE_NEXT_DATA_TITLE["props"]["pageProps"]["mainColumnData"]
	tags = moviemanager.scraper.imdb_scraper._extract_keywords(main_column)
	assert "convenience store" in tags
	assert "slacker" in tags


#============================================
def test_extract_keywords_empty():
	"""Empty mainColumnData returns empty keyword list."""
	tags = moviemanager.scraper.imdb_scraper._extract_keywords({})
	assert tags == []


#============================================
# Tests for top250 extraction
#============================================

def test_top250_above_range():
	"""Top ranking > 250 is set to zero."""
	html = _make_title_html(SAMPLE_NEXT_DATA_TITLE)
	metadata = moviemanager.scraper.imdb_scraper._parse_metadata_html(
		html, "tt0109445"
	)
	# sample data has rank 920 which is > 250
	assert metadata.top250 == 0


#============================================
def test_top250_within_range():
	"""Top ranking <= 250 is captured as top250."""
	data = json.loads(json.dumps(SAMPLE_NEXT_DATA_TITLE))
	# override rank to be within top 250
	data["props"]["pageProps"]["aboveTheFoldData"]["ratingsSummary"]["topRanking"]["rank"] = 42
	html = _make_title_html(data)
	metadata = moviemanager.scraper.imdb_scraper._parse_metadata_html(
		html, "tt0000001"
	)
	assert metadata.top250 == 42


#============================================
# Tests for get_metadata
#============================================

def test_get_metadata_requires_imdb_id():
	"""get_metadata raises ValueError when no imdb_id is given."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	with pytest.raises(ValueError, match="requires an imdb_id"):
		scraper.get_metadata()


#============================================
def test_get_metadata_requires_transport():
	"""get_metadata raises ConnectionError when transport is not set."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	with pytest.raises(ConnectionError, match="transport not configured"):
		scraper.get_metadata(imdb_id="tt0109445")


#============================================
def test_get_metadata_with_transport():
	"""get_metadata fetches HTML via transport and parses metadata."""
	html = _make_title_html(SAMPLE_NEXT_DATA_TITLE)
	mock_transport = unittest.mock.Mock()
	mock_transport.fetch_html.return_value = html
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	scraper.set_transport(mock_transport)
	metadata = scraper.get_metadata(imdb_id="tt0109445")
	# verify transport was called with correct URL
	mock_transport.fetch_html.assert_called_once()
	call_url = mock_transport.fetch_html.call_args[0][0]
	assert "tt0109445" in call_url
	# verify result
	assert metadata.title == "Clerks"
	assert metadata.imdb_id == "tt0109445"


#============================================
# Tests for get_parental_guide
#============================================

def test_get_parental_guide_with_transport():
	"""get_parental_guide fetches HTML via transport and parses guide."""
	html = _make_title_html(SAMPLE_NEXT_DATA_PARENTAL_GUIDE)
	mock_transport = unittest.mock.Mock()
	mock_transport.fetch_html.return_value = html
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	scraper.set_transport(mock_transport)
	guide = scraper.get_parental_guide("tt0109445")
	assert len(guide) == 5
	assert guide["Sex & Nudity"] == "Moderate"
	assert guide["Profanity"] == "Severe"
	# verify URL includes parentalguide path
	call_url = mock_transport.fetch_html.call_args[0][0]
	assert "parentalguide" in call_url


#============================================
def test_get_parental_guide_empty_id():
	"""get_parental_guide returns empty dict when no imdb_id is given."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	guide = scraper.get_parental_guide("")
	assert guide == {}


#============================================
def test_get_parental_guide_no_transport():
	"""get_parental_guide returns empty dict when transport is not set."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	guide = scraper.get_parental_guide("tt0109445")
	assert guide == {}
