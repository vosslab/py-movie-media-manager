"""Live IMDB scraper tests using real network calls.

Search tests hit the CDN suggestion API which has no WAF protection.
Metadata and parental guide tests are skipped because they require
a QWebEnginePage transport with a running Qt event loop.

Test movie: Clerks (1994, tt0109445)
"""

# Standard Library
import os
import sys

# PIP3 modules
import pytest

# add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.scraper.imdb_scraper


#============================================
@pytest.mark.slow
def test_search_clerks():
	"""Search for Clerks returns results with Clerks 1994 present."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("Clerks", year="1994")
	# should find at least one result
	assert len(results) > 0, "Search for Clerks 1994 returned no results"
	# find Clerks 1994 in results
	titles = [r.title for r in results]
	years = [r.year for r in results]
	# Clerks should be in the results
	found = False
	for r in results:
		if "Clerks" in r.title and r.year == "1994":
			found = True
			break
	assert found, (
		f"Clerks 1994 not found in results: "
		f"{list(zip(titles, years))}"
	)


#============================================
@pytest.mark.slow
def test_search_clerks_imdb_id():
	"""Search for Clerks returns tt0109445 as the IMDB ID."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("Clerks", year="1994")
	assert len(results) > 0, "Search returned no results"
	# find the Clerks entry and verify its IMDB ID
	clerks_ids = [r.imdb_id for r in results if "Clerks" in r.title]
	assert "tt0109445" in clerks_ids, (
		f"tt0109445 not found in result IDs: {clerks_ids}"
	)


#============================================
@pytest.mark.slow
def test_search_filters_non_movies():
	"""CDN suggestion API filters out non-movie types."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("Clerks")
	# all results should have imdb_id starting with tt
	for r in results:
		assert r.imdb_id.startswith("tt"), (
			f"Non-title ID in results: {r.imdb_id}"
		)


#============================================
@pytest.mark.slow
def test_search_poster_url():
	"""Search results include poster URLs without resize parameters."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("Clerks", year="1994")
	assert len(results) > 0, "Search returned no results"
	# find result with a poster
	results_with_poster = [r for r in results if r.poster_url]
	if results_with_poster:
		# poster URL should not have resize params like _UX300_
		url = results_with_poster[0].poster_url
		assert "_UX" not in url, f"Poster URL has resize: {url}"
		assert "_UY" not in url, f"Poster URL has resize: {url}"


#============================================
@pytest.mark.slow
def test_search_empty_query():
	"""Empty search query returns empty results gracefully."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("")
	assert results == []


# NOTE: metadata and parental guide live tests are not included here.
# Those endpoints require QWebEnginePage transport with a running Qt
# event loop, which pytest cannot provide. The metadata/parental guide
# parsing logic is thoroughly covered by mocked unit tests in
# test_scraper_imdb.py using sample __NEXT_DATA__ fixtures.
