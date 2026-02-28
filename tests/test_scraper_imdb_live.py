"""Live IMDB scraper tests using real network calls.

These tests hit the real IMDB website and verify that the JSON
parsing approach returns actual movie data. Marked as slow since
they require network access.

Test movie: Clerks (1994, tt0109445)
"""

# Standard Library
import os
import re
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
def test_get_metadata_clerks():
	"""Fetch full metadata for Clerks (tt0109445) and verify fields."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0109445")
	# verify title
	assert metadata.title == "Clerks", f"Title: {metadata.title}"
	# verify year
	assert metadata.year == "1994", f"Year: {metadata.year}"
	# verify runtime is reasonable (92 minutes)
	assert metadata.runtime > 80, f"Runtime too short: {metadata.runtime}"
	assert metadata.runtime < 120, f"Runtime too long: {metadata.runtime}"
	# verify director contains Smith
	assert "Smith" in metadata.director, (
		f"Director: {metadata.director}"
	)
	# verify actors list is non-empty
	assert len(metadata.actors) > 0, "No actors returned"
	# verify rating is reasonable
	assert metadata.rating > 5.0, f"Rating too low: {metadata.rating}"
	assert metadata.rating < 10.0, f"Rating too high: {metadata.rating}"
	# verify votes are substantial
	assert metadata.votes > 100000, f"Votes too low: {metadata.votes}"
	# verify genre includes Comedy
	assert "Comedy" in metadata.genres, f"Genres: {metadata.genres}"
	# verify IMDB ID is preserved
	assert metadata.imdb_id == "tt0109445"
	# verify media source
	assert metadata.media_source == "imdb"
	# verify __NEXT_DATA__ supplementary fields
	assert metadata.country, f"Country is empty: {metadata.country}"
	# country uses text if available, otherwise id code like US
	assert "US" in metadata.country or "United States" in metadata.country, (
		f"Country: {metadata.country}"
	)
	assert "English" in metadata.spoken_languages, (
		f"Languages: {metadata.spoken_languages}"
	)
	assert len(metadata.tags) > 0, "No keyword tags returned"
	# verify poster URL has no resize params (._V1_.jpg alone is OK)
	if metadata.poster_url:
		# ._V1_.jpg is the full-res base URL, but ._V1_UY300_.jpg has resize
		has_resize = re.search(r"\._V1_[^.]+\.jpg$", metadata.poster_url)
		assert not has_resize, (
			f"Poster URL has resize params: {metadata.poster_url}"
		)
	# verify at least one actor has a character role assigned
	actors_with_roles = [a for a in metadata.actors if a.role]
	assert len(actors_with_roles) > 0, (
		f"No actors have roles: {[(a.name, a.role) for a in metadata.actors]}"
	)
	# producers may not be available on all detail pages
	# principalCredits is not always present in __NEXT_DATA__
	if metadata.producers:
		# verify they are CastMember-like objects with correct department
		assert all(p.department == "Production" for p in metadata.producers), (
			f"Producer departments: {[(p.name, p.department) for p in metadata.producers]}"
		)


#============================================
@pytest.mark.slow
def test_get_metadata_clerks_parental_guide():
	"""Verify Clerks parental guide has expected categories."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0109445")
	assert len(metadata.parental_guide) > 0, "Parental guide is empty"
	# verify expected keys exist
	expected_keys = ["Sex & Nudity", "Violence & Gore", "Profanity"]
	for key in expected_keys:
		assert key in metadata.parental_guide, f"Missing key: {key}"
	# verify severity values are non-empty strings
	for key, value in metadata.parental_guide.items():
		assert isinstance(value, str), f"Value for {key} is not a string"
		assert len(value) > 0, f"Value for {key} is empty"
