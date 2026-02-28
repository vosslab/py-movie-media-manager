"""Tests for the IMDB scraper module (JSON parsing approach)."""

# Standard Library
import json
import unittest.mock

# local repo modules
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types


#============================================
def _build_search_html(results: list) -> str:
	"""Build fake IMDB search HTML with __NEXT_DATA__ JSON.

	Args:
		results: List of dicts matching the IMDB titleResults format.

	Returns:
		str: HTML string with embedded __NEXT_DATA__ script block.
	"""
	next_data = {
		"props": {
			"pageProps": {
				"titleResults": {
					"results": results,
					"hasExactMatches": bool(results),
				}
			}
		}
	}
	json_str = json.dumps(next_data)
	html = (
		'<html><head>'
		'<script id="__NEXT_DATA__" type="application/json">'
		+ json_str
		+ '</script></head><body></body></html>'
	)
	return html


#============================================
def _build_detail_html(ld_data: dict) -> str:
	"""Build fake IMDB detail HTML with JSON-LD block.

	Args:
		ld_data: Dict matching the IMDB JSON-LD schema.org format.

	Returns:
		str: HTML string with embedded JSON-LD script block.
	"""
	json_str = json.dumps(ld_data)
	html = (
		'<html><head>'
		'<script type="application/ld+json">'
		+ json_str
		+ '</script></head><body></body></html>'
	)
	return html


#============================================
def _build_detail_html_with_next_data(ld_data: dict, next_data: dict) -> str:
	"""Build fake IMDB detail HTML with both JSON-LD and __NEXT_DATA__.

	Args:
		ld_data: Dict matching the IMDB JSON-LD schema.org format.
		next_data: Dict matching the IMDB __NEXT_DATA__ format.

	Returns:
		str: HTML string with both embedded script blocks.
	"""
	ld_json_str = json.dumps(ld_data)
	next_json_str = json.dumps(next_data)
	html = (
		'<html><head>'
		'<script type="application/ld+json">'
		+ ld_json_str
		+ '</script>'
		'<script id="__NEXT_DATA__" type="application/json">'
		+ next_json_str
		+ '</script></head><body></body></html>'
	)
	return html


#============================================
def _make_search_result(
	imdb_id: str, title: str, year: int, rating: float = 0.0
) -> dict:
	"""Build an IMDB search result dict.

	Args:
		imdb_id: IMDB ID (e.g. tt0133093).
		title: Movie title.
		year: Release year.
		rating: Aggregate rating.

	Returns:
		dict: Search result matching IMDB __NEXT_DATA__ format.
	"""
	result = {
		"index": imdb_id,
		"listItem": {
			"titleText": title,
			"originalTitleText": title,
			"releaseYear": year,
			"ratingSummary": {
				"aggregateRating": rating,
				"voteCount": 100000,
			},
			"plot": f"Plot for {title}.",
			"primaryImage": {
				"url": f"https://example.com/{imdb_id}.jpg",
			},
			"runtime": 8160,
		},
	}
	return result


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_search_returns_results(mock_fetch, mock_sleep):
	"""Verify search maps JSON results to SearchResult list."""
	# build fake search results
	results_data = [
		_make_search_result("tt0133093", "The Matrix", 1999, 8.7),
		_make_search_result("tt0234215", "The Matrix Reloaded", 2003, 7.2),
	]
	mock_fetch.return_value = _build_search_html(results_data)
	# create scraper and search
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("The Matrix")
	# verify results
	assert len(results) == 2
	assert results[0].title == "The Matrix"
	assert results[0].imdb_id == "tt0133093"
	assert results[0].year == "1999"
	assert results[0].score == 8.7
	assert results[1].title == "The Matrix Reloaded"
	assert results[1].imdb_id == "tt0234215"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_search_empty(mock_fetch, mock_sleep):
	"""Verify search returns empty list when no results found."""
	mock_fetch.return_value = _build_search_html([])
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("xyznonexistent")
	assert results == []


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_rating(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify rating and votes are extracted from JSON-LD."""
	ld_data = {
		"@type": "Movie",
		"name": "The Matrix",
		"datePublished": "1999-03-31",
		"aggregateRating": {
			"ratingValue": 8.7,
			"ratingCount": 1900000,
		},
		"contentRating": "R",
		"genre": ["Action", "Sci-Fi"],
		"description": "A hacker discovers reality is a simulation.",
		"duration": "PT2H16M",
		"director": [],
		"actor": [],
		"creator": [],
	}
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0133093")
	assert metadata.rating == 8.7
	assert metadata.votes == 1900000
	assert metadata.title == "The Matrix"
	assert metadata.runtime == 136
	assert metadata.year == "1999"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_actors(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify actors are mapped to CastMember dataclasses."""
	ld_data = {
		"@type": "Movie",
		"name": "The Matrix",
		"datePublished": "1999-03-31",
		"aggregateRating": {"ratingValue": 8.7, "ratingCount": 1900000},
		"genre": [],
		"description": "",
		"duration": "PT2H16M",
		"director": [],
		"creator": [],
		"actor": [
			{
				"@type": "Person",
				"name": "Keanu Reeves",
				"url": "https://www.imdb.com/name/nm0000206/",
			},
			{
				"@type": "Person",
				"name": "Laurence Fishburne",
				"url": "https://www.imdb.com/name/nm0000401/",
			},
		],
	}
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0133093")
	assert len(metadata.actors) == 2
	assert metadata.actors[0].name == "Keanu Reeves"
	assert metadata.actors[0].imdb_id == "nm0000206"
	assert metadata.actors[0].department == "Acting"
	assert metadata.actors[1].name == "Laurence Fishburne"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_certification(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify certification is extracted from JSON-LD contentRating."""
	ld_data = {
		"@type": "Movie",
		"name": "The Shawshank Redemption",
		"datePublished": "1994-10-14",
		"aggregateRating": {"ratingValue": 9.3, "ratingCount": 2700000},
		"contentRating": "R",
		"genre": ["Drama"],
		"description": "",
		"duration": "PT2H22M",
		"director": [],
		"actor": [],
		"creator": [],
	}
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0111161")
	assert metadata.certification == "R"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_imdb_id_preserved(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify imdb_id is passed through to metadata output."""
	ld_data = {
		"@type": "Movie",
		"name": "Test Movie",
		"datePublished": "2020-01-01",
		"aggregateRating": {"ratingValue": 5.0, "ratingCount": 100},
		"genre": [],
		"description": "",
		"duration": "PT1H30M",
		"director": [],
		"actor": [],
		"creator": [],
	}
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt1234567")
	# verify output has correct imdb_id
	assert metadata.imdb_id == "tt1234567"
	# verify fetch was called with correct URL and session
	mock_fetch.assert_called_once()
	call_args = mock_fetch.call_args
	assert call_args[0][0] == "https://www.imdb.com/title/tt1234567/"
	assert call_args[1].get("session") is not None


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_director_and_writer(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify director and writer are extracted from JSON-LD."""
	ld_data = {
		"@type": "Movie",
		"name": "Clerks",
		"datePublished": "1994-11-09",
		"aggregateRating": {"ratingValue": 7.7, "ratingCount": 239000},
		"genre": ["Comedy"],
		"description": "A day in the lives of two convenience clerks.",
		"duration": "PT1H32M",
		"director": [
			{
				"@type": "Person",
				"name": "Kevin Smith",
				"url": "https://www.imdb.com/name/nm0003620/",
			},
		],
		"creator": [
			{"@type": "Organization", "url": "https://www.imdb.com/company/co0007545/"},
			{
				"@type": "Person",
				"name": "Kevin Smith",
				"url": "https://www.imdb.com/name/nm0003620/",
			},
		],
		"actor": [],
	}
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0109445")
	assert metadata.director == "Kevin Smith"
	assert metadata.writer == "Kevin Smith"


#============================================
def test_parse_iso_duration():
	"""Verify ISO 8601 duration parsing helper."""
	parse = moviemanager.scraper.imdb_scraper._parse_iso_duration
	assert parse("PT1H32M") == 92
	assert parse("PT2H") == 120
	assert parse("PT90M") == 90
	assert parse("PT2H16M") == 136
	assert parse("") == 0
	assert parse("invalid") == 0


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_search_with_year(mock_fetch, mock_sleep):
	"""Verify year is appended to search query when provided."""
	results_data = [
		_make_search_result("tt0109445", "Clerks", 1994, 7.7),
	]
	mock_fetch.return_value = _build_search_html(results_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("Clerks", year="1994")
	assert len(results) == 1
	assert results[0].title == "Clerks"
	assert results[0].year == "1994"
	# verify search URL included year in query params
	call_args = mock_fetch.call_args
	params = call_args[1].get("params", call_args[0][1] if len(call_args[0]) > 1 else {})
	assert "1994" in params.get("q", "")


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_no_jsonld(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify graceful handling when JSON-LD is missing."""
	mock_fetch.return_value = "<html><body>No JSON here</body></html>"
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0000000")
	# should return minimal metadata with imdb_id
	assert metadata.imdb_id == "tt0000000"
	assert metadata.media_source == "imdb"
	assert metadata.title == ""


#============================================
def _make_base_ld_data() -> dict:
	"""Build a minimal JSON-LD data dict for detail tests.

	Returns:
		dict: JSON-LD dict with basic movie fields.
	"""
	ld_data = {
		"@type": "Movie",
		"name": "Test Movie",
		"datePublished": "2020-01-01",
		"aggregateRating": {"ratingValue": 7.0, "ratingCount": 5000},
		"contentRating": "PG-13",
		"genre": ["Drama"],
		"description": "A test movie plot.",
		"duration": "PT1H45M",
		"director": [],
		"actor": [],
		"creator": [],
	}
	return ld_data


#============================================
def _make_next_data(above_fold: dict, main_column: dict = None) -> dict:
	"""Wrap aboveTheFoldData into a full __NEXT_DATA__ structure.

	Args:
		above_fold: The aboveTheFoldData dict contents.
		main_column: Optional mainColumnData dict contents.

	Returns:
		dict: Complete __NEXT_DATA__ dict.
	"""
	page_props = {
		"aboveTheFoldData": above_fold,
	}
	if main_column is not None:
		page_props["mainColumnData"] = main_column
	next_data = {
		"props": {
			"pageProps": page_props,
		}
	}
	return next_data


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_original_title(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify original_title extracted when it differs from display title."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Prueba Pelicula"},
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999901")
	assert metadata.original_title == "Prueba Pelicula"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_tagline(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify tagline is extracted from __NEXT_DATA__."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Test Movie"},
		"tagline": {"text": "Every story has a beginning."},
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999902")
	assert metadata.tagline == "Every story has a beginning."


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_country_and_languages(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify country and spoken_languages from __NEXT_DATA__."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Test Movie"},
		"countriesOfOrigin": {
			"countries": [
				{"text": "United States"},
				{"text": "United Kingdom"},
			]
		},
		"spokenLanguages": {
			"spokenLanguages": [
				{"text": "English"},
				{"text": "French"},
			]
		},
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999903")
	assert metadata.country == "United States, United Kingdom"
	assert metadata.spoken_languages == "English, French"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_studio(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify first production company extracted as studio."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Test Movie"},
		"production": {
			"edges": [
				{
					"node": {
						"company": {
							"companyText": {"text": "Miramax"}
						}
					}
				},
				{
					"node": {
						"company": {
							"companyText": {"text": "View Askew"}
						}
					}
				},
			]
		},
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999904")
	assert metadata.studio == "Miramax"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_top250(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify top250 rank extracted from meterRanking."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Test Movie"},
		"meterRanking": {"currentRank": 42},
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999905")
	assert metadata.top250 == 42


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_tags(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify keyword tags list extracted from __NEXT_DATA__."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Test Movie"},
		"keywords": {
			"edges": [
				{"node": {"text": "independent-film"}},
				{"node": {"text": "convenience-store"}},
				{"node": {"text": "dark-comedy"}},
			]
		},
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999906")
	assert len(metadata.tags) == 3
	assert "independent-film" in metadata.tags
	assert "convenience-store" in metadata.tags
	assert "dark-comedy" in metadata.tags


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_no_next_data(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify graceful degradation when __NEXT_DATA__ is absent."""
	ld_data = _make_base_ld_data()
	# use plain detail HTML with only JSON-LD, no __NEXT_DATA__
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999907")
	# JSON-LD fields should still be present
	assert metadata.title == "Test Movie"
	assert metadata.year == "2020"
	assert metadata.rating == 7.0
	# __NEXT_DATA__ fields should be empty/default
	assert metadata.original_title == ""
	assert metadata.tagline == ""
	assert metadata.country == ""
	assert metadata.spoken_languages == ""
	assert metadata.studio == ""
	assert metadata.top250 == 0
	assert metadata.tags == []


#============================================
def _build_parental_guide_html(categories: list) -> str:
	"""Build fake IMDB parental guide HTML with __NEXT_DATA__ JSON.

	Args:
		categories: List of category dicts with id, title, severitySummary.

	Returns:
		str: HTML string with embedded __NEXT_DATA__ script block.
	"""
	next_data = {
		"props": {
			"pageProps": {
				"contentData": {
					"categories": categories,
				}
			}
		}
	}
	json_str = json.dumps(next_data)
	html = (
		'<html><head>'
		'<script id="__NEXT_DATA__" type="application/json">'
		+ json_str
		+ '</script></head><body></body></html>'
	)
	return html


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_parental_guide(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify parental guide severity levels are parsed from page."""
	ld_data = _make_base_ld_data()
	# mock the detail page fetch
	mock_fetch.return_value = _build_detail_html(ld_data)
	# mock the parental guide page fetch
	categories = [
		{
			"id": "NUDITY",
			"title": "Sex & Nudity",
			"severitySummary": {"id": "moderateVotes", "text": "Moderate", "votes": 45},
		},
		{
			"id": "VIOLENCE",
			"title": "Violence & Gore",
			"severitySummary": {"id": "mildVotes", "text": "Mild", "votes": 30},
		},
		{
			"id": "PROFANITY",
			"title": "Profanity",
			"severitySummary": {"id": "severeVotes", "text": "Severe", "votes": 74},
		},
	]
	mock_fetch_safe.return_value = _build_parental_guide_html(categories)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0109445")
	# verify parental guide dict has correct keys and values
	assert len(metadata.parental_guide) == 3
	assert metadata.parental_guide["Sex & Nudity"] == "Moderate"
	assert metadata.parental_guide["Violence & Gore"] == "Mild"
	assert metadata.parental_guide["Profanity"] == "Severe"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_parental_guide_failure(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify graceful degradation when parental guide page fails."""
	ld_data = _make_base_ld_data()
	mock_fetch.return_value = _build_detail_html(ld_data)
	# parental guide fetch returns empty string (failure)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0000000")
	# parental guide should be empty dict on failure
	assert metadata.parental_guide == {}
	# other fields should still be populated
	assert metadata.title == "Test Movie"


#============================================
def test_parse_parental_guide_direct():
	"""Verify _parse_parental_guide extracts categories correctly."""
	categories = [
		{
			"id": "NUDITY",
			"title": "Sex & Nudity",
			"severitySummary": {"id": "moderateVotes", "text": "Moderate", "votes": 45},
		},
		{
			"id": "VIOLENCE",
			"title": "Violence & Gore",
			"severitySummary": {"id": "mildVotes", "text": "Mild", "votes": 30},
		},
		{
			"id": "PROFANITY",
			"title": "Profanity",
			"severitySummary": {"id": "severeVotes", "text": "Severe", "votes": 74},
		},
		{
			"id": "ALCOHOL",
			"title": "Alcohol, Drugs & Smoking",
			"severitySummary": {"id": "moderateVotes", "text": "Moderate", "votes": 41},
		},
		{
			"id": "FRIGHTENING",
			"title": "Frightening & Intense Scenes",
			"severitySummary": {"id": "noneVotes", "text": "None", "votes": 40},
		},
	]
	html = _build_parental_guide_html(categories)
	result = moviemanager.scraper.imdb_scraper._parse_parental_guide(html)
	assert len(result) == 5
	assert result["Sex & Nudity"] == "Moderate"
	assert result["Violence & Gore"] == "Mild"
	assert result["Profanity"] == "Severe"
	assert result["Alcohol, Drugs & Smoking"] == "Moderate"
	assert result["Frightening & Intense Scenes"] == "None"


#============================================
def test_parse_parental_guide_empty_html():
	"""Verify _parse_parental_guide returns empty dict for bad HTML."""
	result = moviemanager.scraper.imdb_scraper._parse_parental_guide(
		"<html><body>No data</body></html>"
	)
	assert result == {}


#============================================
def test_upgrade_poster_url():
	"""Verify IMDB resize parameters are stripped for full resolution."""
	upgrade = moviemanager.scraper.imdb_scraper._upgrade_poster_url
	# typical IMDB poster URL with resize suffix
	result = upgrade(
		"https://m.media-amazon.com/images/M/pic._V1_UY300_.jpg"
	)
	assert result == "https://m.media-amazon.com/images/M/pic.jpg"
	# URL with complex resize parameters
	result = upgrade(
		"https://m.media-amazon.com/images/M/abc._V1_QL75_UX190_.jpg"
	)
	assert result == "https://m.media-amazon.com/images/M/abc.jpg"


#============================================
def test_upgrade_poster_url_empty():
	"""Verify empty URL returns empty string."""
	upgrade = moviemanager.scraper.imdb_scraper._upgrade_poster_url
	assert upgrade("") == ""
	# non-IMDB URL without ._V1_ should pass through unchanged
	assert upgrade("https://example.com/pic.png") == "https://example.com/pic.png"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_actor_roles(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify actor character names are extracted from __NEXT_DATA__."""
	ld_data = {
		"@type": "Movie",
		"name": "The Matrix",
		"datePublished": "1999-03-31",
		"aggregateRating": {"ratingValue": 8.7, "ratingCount": 1900000},
		"genre": ["Action"],
		"description": "",
		"duration": "PT2H16M",
		"director": [],
		"creator": [],
		"actor": [
			{
				"@type": "Person",
				"name": "Keanu Reeves",
				"url": "https://www.imdb.com/name/nm0000206/",
			},
			{
				"@type": "Person",
				"name": "Laurence Fishburne",
				"url": "https://www.imdb.com/name/nm0000401/",
			},
		],
	}
	above_fold = {
		"titleText": {"text": "The Matrix"},
		"originalTitleText": {"text": "The Matrix"},
	}
	main_column = {
		"castV2": [
			{
				"credits": [
					{
						"name": {"nameText": {"text": "Keanu Reeves"}, "id": "nm0000206"},
						"creditedRoles": {
							"edges": [
								{
									"node": {
										"characters": {
											"edges": [
												{"node": {"name": "Neo"}}
											]
										}
									}
								}
							]
						},
					},
					{
						"name": {"nameText": {"text": "Laurence Fishburne"}, "id": "nm0000401"},
						"creditedRoles": {
							"edges": [
								{
									"node": {
										"characters": {
											"edges": [
												{"node": {"name": "Morpheus"}}
											]
										}
									}
								}
							]
						},
					},
				]
			}
		],
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold, main_column)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0133093")
	assert len(metadata.actors) == 2
	assert metadata.actors[0].name == "Keanu Reeves"
	assert metadata.actors[0].role == "Neo"
	assert metadata.actors[1].name == "Laurence Fishburne"
	assert metadata.actors[1].role == "Morpheus"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_poster_url_upgraded(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify poster URL has resize parameters stripped."""
	ld_data = _make_base_ld_data()
	ld_data["image"] = "https://m.media-amazon.com/images/M/test._V1_UY300_.jpg"
	mock_fetch.return_value = _build_detail_html(ld_data)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999908")
	assert metadata.poster_url == "https://m.media-amazon.com/images/M/test.jpg"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page_safe", return_value="")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper._fetch_page")
def test_get_metadata_producers(mock_fetch, mock_fetch_safe, mock_sleep):
	"""Verify producers extracted from __NEXT_DATA__ principalCredits."""
	ld_data = _make_base_ld_data()
	above_fold = {
		"titleText": {"text": "Test Movie"},
		"originalTitleText": {"text": "Test Movie"},
		"principalCredits": [
			{
				"category": {"id": "director", "text": "Director"},
				"credits": [
					{"name": {"nameText": {"text": "Test Director"}, "id": "nm0000001"}},
				],
			},
			{
				"category": {"id": "producer", "text": "Producer"},
				"credits": [
					{"name": {"nameText": {"text": "Scott Mosier"}, "id": "nm0004874"}},
					{"name": {"nameText": {"text": "Kevin Smith"}, "id": "nm0003620"}},
				],
			},
		],
	}
	mock_fetch.return_value = _build_detail_html_with_next_data(
		ld_data, _make_next_data(above_fold)
	)
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt9999909")
	assert len(metadata.producers) == 2
	assert metadata.producers[0].name == "Scott Mosier"
	assert metadata.producers[0].imdb_id == "nm0004874"
	assert metadata.producers[0].department == "Production"
	assert metadata.producers[1].name == "Kevin Smith"
