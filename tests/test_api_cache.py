"""Unit tests for the persistent API cache module.

Tests cover round-trip serialization, TTL expiration, cache miss behavior,
key normalization, clear/remove operations, corrupt JSON handling,
and automatic directory creation.
"""

# Standard Library
import os
import sys
import json
import time

# add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.api.api_cache
import moviemanager.scraper.types


#============================================
def _make_search_result(title: str = "Clerks", year: str = "1994") -> object:
	"""Create a sample SearchResult dataclass for testing."""
	result = moviemanager.scraper.types.SearchResult(
		title=title,
		year=year,
		imdb_id="tt0109445",
		tmdb_id=2292,
		overview="A day in the lives of two convenience clerks.",
		poster_url="https://example.com/poster.jpg",
		score=7.7,
		match_confidence=0.85,
	)
	return result


#============================================
def _make_metadata() -> object:
	"""Create a sample MediaMetadata dataclass for testing."""
	actor = moviemanager.scraper.types.CastMember(
		name="Brian O'Halloran",
		role="Dante Hicks",
		tmdb_id=12345,
	)
	producer = moviemanager.scraper.types.CastMember(
		name="Kevin Smith",
		role="Producer",
		department="Production",
	)
	metadata = moviemanager.scraper.types.MediaMetadata(
		title="Clerks",
		year="1994",
		plot="A day in the lives of two convenience clerks.",
		runtime=92,
		rating=7.7,
		votes=239766,
		director="Kevin Smith",
		genres=["Comedy"],
		actors=[actor],
		producers=[producer],
		imdb_id="tt0109445",
		tmdb_id=2292,
	)
	return metadata


#============================================
class TestSearchResultsCache:
	"""Tests for search result caching."""

	def test_round_trip_imdb_search(self, tmp_path):
		"""Search results survive a put/get round trip."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		results = [_make_search_result(), _make_search_result("Clerks II", "2006")]
		cache.put_search_results("imdb_search", "clerks", "1994", results)
		cached = cache.get_search_results("imdb_search", "clerks", "1994")
		assert cached is not None
		assert len(cached) == 2
		assert cached[0]["title"] == "Clerks"
		assert cached[1]["title"] == "Clerks II"
		assert cached[0]["imdb_id"] == "tt0109445"

	def test_round_trip_tmdb_search(self, tmp_path):
		"""TMDB search results survive a put/get round trip."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		results = [_make_search_result()]
		cache.put_search_results("tmdb_search", "Clerks", "1994", results)
		cached = cache.get_search_results("tmdb_search", "clerks", "1994")
		assert cached is not None
		assert len(cached) == 1

	def test_cache_miss_returns_none(self, tmp_path):
		"""A cache miss returns None."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		result = cache.get_search_results("imdb_search", "nonexistent", "2000")
		assert result is None


#============================================
class TestMetadataCache:
	"""Tests for metadata caching."""

	def test_round_trip_imdb_metadata(self, tmp_path):
		"""IMDB metadata survives a put/get round trip."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		metadata = _make_metadata()
		cache.put_metadata("imdb_metadata", "tt0109445", metadata)
		cached = cache.get_metadata("imdb_metadata", "tt0109445")
		assert cached is not None
		assert cached["title"] == "Clerks"
		assert cached["director"] == "Kevin Smith"
		assert len(cached["actors"]) == 1
		assert cached["actors"][0]["name"] == "Brian O'Halloran"
		assert cached["actors"][0]["role"] == "Dante Hicks"

	def test_round_trip_tmdb_metadata_composite_key(self, tmp_path):
		"""TMDB metadata with composite key survives round trip."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		metadata = _make_metadata()
		cache.put_metadata("tmdb_metadata", "2292", metadata, secondary_id="tt0109445")
		cached = cache.get_metadata("tmdb_metadata", "2292", secondary_id="tt0109445")
		assert cached is not None
		assert cached["title"] == "Clerks"

	def test_metadata_miss(self, tmp_path):
		"""Missing metadata returns None."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		result = cache.get_metadata("imdb_metadata", "tt9999999")
		assert result is None


#============================================
class TestParentalGuideCache:
	"""Tests for parental guide caching."""

	def test_round_trip(self, tmp_path):
		"""Parental guide data survives round trip."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		guide = {
			"nudity": "Mild",
			"violence": "Moderate",
			"profanity": "Severe",
		}
		cache.put_parental_guide("tt0109445", guide)
		cached = cache.get_parental_guide("tt0109445")
		assert cached is not None
		assert cached["profanity"] == "Severe"

	def test_miss(self, tmp_path):
		"""Missing parental guide returns None."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		result = cache.get_parental_guide("tt9999999")
		assert result is None


#============================================
class TestPosterLookupCache:
	"""Tests for TMDB poster lookup caching."""

	def test_round_trip(self, tmp_path):
		"""Poster lookup survives round trip as a tuple."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		cache.put_poster_lookup("tt0109445", 2292, "https://image.tmdb.org/poster.jpg")
		result = cache.get_poster_lookup("tt0109445")
		assert result is not None
		assert result == (2292, "https://image.tmdb.org/poster.jpg")

	def test_miss(self, tmp_path):
		"""Missing poster lookup returns None."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		result = cache.get_poster_lookup("tt9999999")
		assert result is None


#============================================
class TestTTLExpiration:
	"""Tests for TTL expiration behavior."""

	def test_expired_entry_returns_none(self, tmp_path):
		"""Entries older than TTL are treated as cache misses."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=60
		)
		# manually write an expired entry
		expired_data = {
			"clerks|1994": {
				"timestamp": time.time() - 120,
				"data": [{"title": "Clerks"}],
			}
		}
		os.makedirs(str(tmp_path), exist_ok=True)
		cache_path = os.path.join(str(tmp_path), "imdb_search.json")
		with open(cache_path, "w", encoding="utf-8") as f:
			json.dump(expired_data, f)
		result = cache.get_search_results("imdb_search", "clerks", "1994")
		assert result is None

	def test_fresh_entry_returns_data(self, tmp_path):
		"""Entries within TTL are returned normally."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		results = [_make_search_result()]
		cache.put_search_results("imdb_search", "clerks", "1994", results)
		cached = cache.get_search_results("imdb_search", "clerks", "1994")
		assert cached is not None


#============================================
class TestKeyNormalization:
	"""Tests for cache key normalization."""

	def test_case_insensitive(self, tmp_path):
		"""Keys are case-insensitive."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		results = [_make_search_result()]
		cache.put_search_results("imdb_search", "CLERKS", "1994", results)
		cached = cache.get_search_results("imdb_search", "clerks", "1994")
		assert cached is not None

	def test_whitespace_stripped(self, tmp_path):
		"""Leading/trailing whitespace is stripped from keys."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		results = [_make_search_result()]
		cache.put_search_results("imdb_search", "  clerks  ", "1994", results)
		cached = cache.get_search_results("imdb_search", "clerks", "1994")
		assert cached is not None


#============================================
class TestClearAndRemove:
	"""Tests for clear and remove operations."""

	def test_clear_single_type(self, tmp_path):
		"""Clearing one cache type removes only that file."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		cache.put_search_results("imdb_search", "clerks", "1994", [_make_search_result()])
		cache.put_parental_guide("tt0109445", {"nudity": "Mild"})
		cache.clear("imdb_search")
		# search cache is gone
		assert cache.get_search_results("imdb_search", "clerks", "1994") is None
		# parental guide cache is untouched
		assert cache.get_parental_guide("tt0109445") is not None

	def test_clear_all(self, tmp_path):
		"""Clearing without a type removes all cache files."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		cache.put_search_results("imdb_search", "clerks", "1994", [_make_search_result()])
		cache.put_parental_guide("tt0109445", {"nudity": "Mild"})
		cache.clear()
		assert cache.get_search_results("imdb_search", "clerks", "1994") is None
		assert cache.get_parental_guide("tt0109445") is None

	def test_remove_single_entry(self, tmp_path):
		"""Removing a single entry keeps other entries intact."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		cache.put_search_results("imdb_search", "clerks", "1994", [_make_search_result()])
		cache.put_search_results("imdb_search", "matrix", "1999", [_make_search_result("Matrix", "1999")])
		removed = cache.remove("imdb_search", "clerks|1994")
		assert removed is True
		assert cache.get_search_results("imdb_search", "clerks", "1994") is None
		assert cache.get_search_results("imdb_search", "matrix", "1999") is not None

	def test_remove_nonexistent_returns_false(self, tmp_path):
		"""Removing a nonexistent key returns False."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		removed = cache.remove("imdb_search", "nonexistent|2000")
		assert removed is False


#============================================
class TestCorruptJson:
	"""Tests for handling corrupt cache files."""

	def test_corrupt_json_returns_empty(self, tmp_path):
		"""Corrupt JSON file is handled gracefully."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		# write corrupt JSON
		cache_path = os.path.join(str(tmp_path), "imdb_search.json")
		with open(cache_path, "w", encoding="utf-8") as f:
			f.write("{not valid json!!!")
		result = cache.get_search_results("imdb_search", "clerks", "1994")
		assert result is None

	def test_non_dict_json_returns_empty(self, tmp_path):
		"""A JSON file containing a list instead of dict is reset."""
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=str(tmp_path), ttl_seconds=3600
		)
		cache_path = os.path.join(str(tmp_path), "imdb_search.json")
		with open(cache_path, "w", encoding="utf-8") as f:
			json.dump([1, 2, 3], f)
		result = cache.get_search_results("imdb_search", "clerks", "1994")
		assert result is None


#============================================
class TestDirectoryCreation:
	"""Tests for automatic directory creation."""

	def test_creates_missing_directory(self, tmp_path):
		"""Cache creates its directory on first write."""
		nested_dir = os.path.join(str(tmp_path), "nested", "cache", "dir")
		cache = moviemanager.api.api_cache.ApiCache(
			cache_dir=nested_dir, ttl_seconds=3600
		)
		cache.put_parental_guide("tt0109445", {"nudity": "Mild"})
		assert os.path.isdir(nested_dir)
		cached = cache.get_parental_guide("tt0109445")
		assert cached is not None
