"""Tests for Bayesian match confidence scoring."""

# Standard Library
import sys
import os

# ensure repo root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.api.match_confidence


#============================================
def test_exact_title_and_year():
	"""Exact title + year should score very high (>= 0.9)."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "The Matrix", "1999",
	)
	assert score >= 0.9, f"Expected >= 0.9, got {score}"


#============================================
def test_exact_title_year_off_by_one():
	"""Exact title, year off by 1 should score >= 0.7."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "The Matrix", "2000",
	)
	assert score >= 0.7, f"Expected >= 0.7, got {score}"


#============================================
def test_similar_title_with_article():
	"""Similar title with dropped article + year should score >= 0.7."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "Matrix", "1999",
	)
	assert score >= 0.7, f"Expected >= 0.7, got {score}"


#============================================
def test_different_title_low_score():
	"""Completely different title should score < 0.3."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "Frozen", "2013",
	)
	assert score < 0.3, f"Expected < 0.3, got {score}"


#============================================
def test_token_reorder_reasonable_score():
	"""Reordered tokens should still produce a reasonable score."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"Batman Returns", "1992", "Returns Batman", "1992",
	)
	assert score > 0.5, f"Expected > 0.5, got {score}"


#============================================
def test_missing_query_year_moderate_score():
	"""Missing query year should produce a moderate score."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "", "The Matrix", "1999",
	)
	# should still be decent because title matches perfectly
	assert score >= 0.7, f"Expected >= 0.7, got {score}"


#============================================
def test_popularity_tiebreaker():
	"""Among similar titles, higher-rated result scores slightly higher."""
	# use year off-by-1 so score does not saturate at 1.0
	score_high = moviemanager.api.match_confidence.compute_match_confidence(
		"Inception", "2010", "Inception", "2011",
		result_score=8.8,
	)
	score_low = moviemanager.api.match_confidence.compute_match_confidence(
		"Inception", "2010", "Inception", "2011",
		result_score=3.2,
	)
	assert score_high > score_low, (
		f"High-rated ({score_high}) should beat low-rated ({score_low})"
	)


#============================================
def test_original_title_match():
	"""Match against original_title when it differs from title."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"Crouching Tiger Hidden Dragon", "2000",
		"Wo hu cang long", "2000",
		result_original_title="Crouching Tiger, Hidden Dragon",
	)
	assert score >= 0.7, f"Expected >= 0.7, got {score}"


#============================================
def test_empty_result_title():
	"""Empty result title should score very low."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "", "",
	)
	assert score < 0.3, f"Expected < 0.3, got {score}"


#============================================
def test_score_within_bounds():
	"""Score should always be between 0.0 and 1.0."""
	# test a variety of inputs
	test_cases = [
		("The Matrix", "1999", "The Matrix", "1999", 10.0),
		("A", "", "B", "", 0.0),
		("", "", "", "", 0.0),
		("Extremely Long Movie Title Part Two", "2025",
			"Short", "1990", 1.0),
	]
	for qt, qy, rt, ry, rs in test_cases:
		score = moviemanager.api.match_confidence.compute_match_confidence(
			qt, qy, rt, ry, result_score=rs,
		)
		assert 0.0 <= score <= 1.0, (
			f"Score {score} out of bounds for ({qt}, {qy}, {rt}, {ry})"
		)


#============================================
def test_normalize_title_internal():
	"""Test the internal _normalize_title helper."""
	normalize = moviemanager.api.match_confidence._normalize_title
	assert normalize("The Matrix") == "matrix"
	assert normalize("A Beautiful Mind") == "beautiful mind"
	assert normalize("An Inconvenient Truth") == "inconvenient truth"
	assert normalize("  Extra   Spaces  ") == "extra spaces"
	assert normalize("UPPERCASE") == "uppercase"


#============================================
def test_year_proximity_internal():
	"""Test the internal _year_proximity bell curve helper."""
	prox = moviemanager.api.match_confidence._year_proximity
	# exact match is 1.0
	assert prox("1999", "1999") == 1.0
	# off-by-1 should be high (bell curve ~0.88)
	assert prox("1999", "2000") > 0.8
	# off-by-2 should be moderate (~0.61)
	assert prox("1999", "2001") > 0.5
	# off-by-5 should be very low
	assert prox("1999", "2004") < 0.2
	# bell curve: scores decrease monotonically with distance
	assert prox("1999", "2000") > prox("1999", "2001")
	assert prox("1999", "2001") > prox("1999", "2003")
	# missing years
	assert prox("", "1999") == 0.5
	assert prox("1999", "") == 0.3


#============================================
def test_runtime_proximity_internal():
	"""Test the internal _runtime_proximity bell curve helper."""
	prox = moviemanager.api.match_confidence._runtime_proximity
	# exact match is 1.0
	assert prox(120, 120) == 1.0
	# off-by-5 minutes should be high (~0.95)
	assert prox(120, 125) > 0.9
	# off-by-15 minutes should be moderate (~0.61)
	assert prox(120, 135) > 0.5
	# off-by-30 minutes should be low
	assert prox(120, 150) < 0.5
	# bell curve: scores decrease monotonically with distance
	assert prox(120, 125) > prox(120, 135)
	assert prox(120, 135) > prox(120, 150)
	# missing runtime returns neutral
	assert prox(0, 120) == 0.5
	assert prox(120, 0) == 0.5
	assert prox(0, 0) == 0.5


#============================================
def test_runtime_improves_match():
	"""Matching runtime should boost confidence vs missing runtime."""
	# same title/year but one has matching runtime, other has none
	score_with_runtime = (
		moviemanager.api.match_confidence.compute_match_confidence(
			"Inception", "2010", "Inception", "2010",
			query_runtime=148, result_runtime=148,
		)
	)
	score_no_runtime = (
		moviemanager.api.match_confidence.compute_match_confidence(
			"Inception", "2010", "Inception", "2010",
			query_runtime=148, result_runtime=0,
		)
	)
	assert score_with_runtime > score_no_runtime, (
		f"Runtime match ({score_with_runtime}) should beat "
		f"no runtime ({score_no_runtime})"
	)


#============================================
def test_runtime_mismatch_hurts():
	"""Very different runtime should reduce confidence."""
	# same title/year, one with close runtime, one with far runtime
	score_close = (
		moviemanager.api.match_confidence.compute_match_confidence(
			"Inception", "2010", "Inception", "2010",
			query_runtime=148, result_runtime=150,
		)
	)
	score_far = (
		moviemanager.api.match_confidence.compute_match_confidence(
			"Inception", "2010", "Inception", "2010",
			query_runtime=148, result_runtime=90,
		)
	)
	assert score_close > score_far, (
		f"Close runtime ({score_close}) should beat "
		f"far runtime ({score_far})"
	)
