"""Tests for Bayesian match confidence scoring."""

# Standard Library
import sys
import os

# ensure repo root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.api.match_confidence


#============================================
def test_exact_title_and_year() -> None:
	"""The correct movie outranks a wrong title or release year."""
	score = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "The Matrix", "1999",
	)
	wrong_title = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "Frozen", "2013",
	)
	wrong_year = moviemanager.api.match_confidence.compute_match_confidence(
		"The Matrix", "1999", "The Matrix", "2000",
	)
	assert score > wrong_title
	assert score > wrong_year


#============================================
def test_popularity_tiebreaker() -> None:
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
def test_score_within_bounds() -> None:
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
def test_runtime_improves_match() -> None:
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
def test_runtime_mismatch_hurts() -> None:
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
