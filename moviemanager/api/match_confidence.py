"""Bayesian-inspired match confidence scoring for movie search results.

Computes how well a search result matches a query using weighted
signals: title similarity, year proximity, token overlap, and
a popularity prior. API-agnostic -- works with plain strings and
floats so it can be used with any metadata provider.
"""

# Standard Library
import difflib
import math
import re


#============================================
def _normalize_title(title: str) -> str:
	"""Normalize a movie title for comparison.

	Lowercases, strips whitespace, removes leading articles
	(the/a/an), and collapses runs of whitespace.

	Args:
		title: Raw movie title string.

	Returns:
		str: Normalized title for comparison.
	"""
	normalized = title.lower().strip()
	# remove leading articles
	normalized = re.sub(r"^(the|a|an)\s+", "", normalized)
	# collapse whitespace
	normalized = re.sub(r"\s+", " ", normalized).strip()
	return normalized


#============================================
def _title_similarity(query: str, candidate: str) -> float:
	"""Compute title similarity using SequenceMatcher.

	Args:
		query: Normalized query title.
		candidate: Normalized candidate title.

	Returns:
		float: Similarity ratio from 0.0 to 1.0.
	"""
	ratio = difflib.SequenceMatcher(None, query, candidate).ratio()
	return ratio


# Gaussian standard deviation for year proximity bell curve.
# sigma=2 gives: off-by-1 ~0.88, off-by-2 ~0.61, off-by-3 ~0.32
_YEAR_SIGMA = 2.0


#============================================
def _year_proximity(query_year: str, result_year: str) -> float:
	"""Score year proximity between query and result using a bell curve.

	Uses a Gaussian falloff so that small year differences (common
	across databases) are penalized gradually rather than with hard
	cutoffs. Exact match scores 1.0, and the score decays smoothly
	as the year difference increases.

	Missing query year returns 0.5 (neutral).
	Missing result year returns 0.3.

	Args:
		query_year: Year from the query (may be empty).
		result_year: Year from the search result (may be empty).

	Returns:
		float: Year proximity score from 0.0 to 1.0.
	"""
	if not query_year:
		return 0.5
	if not result_year:
		return 0.3
	try:
		q_year = int(query_year)
		r_year = int(result_year)
	except ValueError:
		return 0.3
	diff = abs(q_year - r_year)
	# Gaussian bell curve: exp(-diff^2 / (2 * sigma^2))
	score = math.exp(-(diff ** 2) / (2.0 * _YEAR_SIGMA ** 2))
	return score


#============================================
def _token_overlap(query: str, candidate: str) -> float:
	"""Compute Jaccard similarity of word tokens.

	Args:
		query: Normalized query title.
		candidate: Normalized candidate title.

	Returns:
		float: Jaccard similarity from 0.0 to 1.0.
	"""
	q_tokens = set(query.split())
	c_tokens = set(candidate.split())
	if not q_tokens or not c_tokens:
		return 0.0
	intersection = q_tokens & c_tokens
	union = q_tokens | c_tokens
	jaccard = len(intersection) / len(union)
	return jaccard


#============================================
def _popularity_prior(score: float) -> float:
	"""Convert a provider rating into a Bayesian prior.

	Normalizes the score to 0.0-1.0 range. Provider ratings
	are typically 0-10 scale.

	Args:
		score: Provider aggregate rating (e.g. IMDB/TMDB score).

	Returns:
		float: Normalized popularity score from 0.0 to 1.0.
	"""
	if not score or score <= 0:
		return 0.0
	clamped = min(score / 10.0, 1.0)
	return clamped


#============================================
def compute_match_confidence(
	query_title: str,
	query_year: str,
	result_title: str,
	result_year: str,
	result_original_title: str = "",
	result_score: float = 0.0,
) -> float:
	"""Compute confidence score for how well a result matches a query.

	Uses four weighted signals to produce a composite score:
	- Title similarity (0.50): difflib SequenceMatcher ratio
	- Year proximity (0.25): exact=1.0, off-by-1=0.7, etc.
	- Token overlap (0.15): Jaccard similarity of word tokens
	- Popularity prior (0.10): normalized provider rating

	Bonuses: exact title + exact year gets +0.1 boost.
	Clamps: title similarity below 0.3 caps final score at 0.3.

	All parameters are plain strings/floats -- no API-specific
	types are required.

	Args:
		query_title: Movie title from the user's library.
		query_year: Movie year from the user's library (may be empty).
		result_title: Title from the search result.
		result_year: Year from the search result (may be empty).
		result_original_title: Original title from the result (may be empty).
		result_score: Provider aggregate rating (0-10 scale).

	Returns:
		float: Confidence score from 0.0 to 1.0.
	"""
	# normalize titles for comparison
	q_norm = _normalize_title(query_title)
	r_norm = _normalize_title(result_title)
	# also check original title and take the better match
	title_sim = _title_similarity(q_norm, r_norm)
	if result_original_title:
		orig_norm = _normalize_title(result_original_title)
		orig_sim = _title_similarity(q_norm, orig_norm)
		title_sim = max(title_sim, orig_sim)
		# also use the better title for token overlap
		if orig_sim > _title_similarity(q_norm, r_norm):
			r_norm = orig_norm
	# compute individual signals
	year_score = _year_proximity(query_year, result_year)
	token_score = _token_overlap(q_norm, r_norm)
	pop_score = _popularity_prior(result_score)
	# weighted composite
	confidence = (
		0.50 * title_sim
		+ 0.25 * year_score
		+ 0.15 * token_score
		+ 0.10 * pop_score
	)
	# bonus: exact title + exact year
	if q_norm == r_norm and query_year and query_year == result_year:
		confidence = min(confidence + 0.1, 1.0)
	# clamp: very low title similarity caps the final score
	if title_sim < 0.3:
		confidence = min(confidence, 0.3)
	# ensure bounds
	confidence = max(0.0, min(1.0, confidence))
	return confidence


# simple assertions for basic behavior
assert compute_match_confidence("The Matrix", "1999", "The Matrix", "1999") >= 0.9
assert compute_match_confidence("The Matrix", "1999", "The Matrix", "2000") >= 0.7
assert compute_match_confidence("The Matrix", "1999", "Frozen", "2013") < 0.3
assert compute_match_confidence("Batman Returns", "", "Returns Batman", "") > 0.3
