"""Persistent JSON-file cache for API metadata responses.

Caches search results, metadata, and parental guide data with a 6-month TTL.
Each query type gets its own JSON file under ~/.cache/movie_organizer/.
"""

# Standard Library
import os
import json
import time
import logging
import tempfile
import dataclasses


# module logger
_LOG = logging.getLogger(__name__)

# 182 days in seconds (approximately 6 months)
_DEFAULT_TTL_SECONDS = 182 * 24 * 60 * 60

# valid cache type names mapped to filenames
_CACHE_FILES = {
	"imdb_search": "imdb_search.json",
	"imdb_metadata": "imdb_metadata.json",
	"imdb_parental_guide": "imdb_parental_guide.json",
	"tmdb_search": "tmdb_search.json",
	"tmdb_metadata": "tmdb_metadata.json",
	"tmdb_poster_lookup": "tmdb_poster_lookup.json",
}


#============================================
def _normalize_key(raw_key: str) -> str:
	"""Normalize a cache key by lowercasing and stripping whitespace.

	Args:
		raw_key: Raw key string.

	Returns:
		Normalized key string.
	"""
	normalized = raw_key.strip().lower()
	return normalized


#============================================
def _serialize_value(value) -> object:
	"""Convert dataclass instances (and lists thereof) to JSON-safe dicts.

	Args:
		value: A dataclass, list of dataclasses, dict, or primitive.

	Returns:
		JSON-serializable object.
	"""
	if dataclasses.is_dataclass(value) and not isinstance(value, type):
		result = dataclasses.asdict(value)
		return result
	if isinstance(value, list):
		result = [_serialize_value(item) for item in value]
		return result
	if isinstance(value, dict):
		result = {k: _serialize_value(v) for k, v in value.items()}
		return result
	return value


#============================================
#============================================
def _json_default(obj: object) -> str:
	"""Fallback handler for non-serializable objects in json.dump.

	Args:
		obj: Non-serializable object encountered during JSON encoding.

	Returns:
		String representation of the object.
	"""
	_LOG.warning(
		"Non-serializable object in cache data: %s (type %s)",
		obj, type(obj).__name__,
	)
	return str(obj)


#============================================
class ApiCache:
	"""Persistent JSON-file cache for movie API metadata.

	Stores cached responses in individual JSON files per query type
	under a configurable cache directory. Expired entries are purged
	on load.
	"""

	def __init__(self, cache_dir: str = "", ttl_seconds: int = _DEFAULT_TTL_SECONDS):
		"""Initialize the API cache.

		Args:
			cache_dir: Directory for cache files. Defaults to
				~/.cache/movie_organizer/.
			ttl_seconds: Time-to-live for cache entries in seconds.
				Defaults to 182 days.
		"""
		if not cache_dir:
			cache_dir = os.path.join(
				os.path.expanduser("~"), ".cache", "movie_organizer"
			)
		self._cache_dir = cache_dir
		self._ttl_seconds = ttl_seconds

	#============================================
	def _cache_file_path(self, cache_type: str) -> str:
		"""Return the full path for a cache type's JSON file.

		Args:
			cache_type: One of the keys in _CACHE_FILES.

		Returns:
			Absolute path to the cache file.
		"""
		filename = _CACHE_FILES[cache_type]
		path = os.path.join(self._cache_dir, filename)
		return path

	#============================================
	def _load_cache_file(self, cache_type: str) -> dict:
		"""Load a cache file, purging expired entries.

		Args:
			cache_type: Cache type name.

		Returns:
			Dict of non-expired cache entries.
		"""
		path = self._cache_file_path(cache_type)
		if not os.path.exists(path):
			return {}
		try:
			with open(path, "r", encoding="utf-8") as f:
				raw_data = json.load(f)
		except (json.JSONDecodeError, ValueError, OSError) as err:
			_LOG.warning("Corrupt cache file %s, resetting: %s", path, err)
			return {}
		if not isinstance(raw_data, dict):
			_LOG.warning("Cache file %s has invalid format, resetting", path)
			return {}
		# purge expired entries
		now = time.time()
		cleaned = {}
		for key, entry in raw_data.items():
			if not isinstance(entry, dict):
				continue
			timestamp = entry.get("timestamp", 0)
			if now - timestamp < self._ttl_seconds:
				cleaned[key] = entry
		return cleaned

	#============================================
	def _save_cache_file(self, cache_type: str, data: dict) -> None:
		"""Save cache data atomically via temp file + rename.

		Args:
			cache_type: Cache type name.
			data: Dict of cache entries to write.
		"""
		# ensure cache directory exists
		os.makedirs(self._cache_dir, exist_ok=True)
		path = self._cache_file_path(cache_type)
		# write to temp file then rename for atomicity
		fd, tmp_path = tempfile.mkstemp(
			dir=self._cache_dir, suffix=".tmp"
		)
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				json.dump(data, f, indent=2, ensure_ascii=False,
					default=_json_default)
			os.rename(tmp_path, path)
		except OSError:
			# clean up temp file on failure
			if os.path.exists(tmp_path):
				os.unlink(tmp_path)
			raise

	#============================================
	def _get(self, cache_type: str, key: str) -> object:
		"""Retrieve a cached value by type and key.

		Args:
			cache_type: Cache type name.
			key: Raw cache key (will be normalized).

		Returns:
			Cached data, or None if not found or expired.
		"""
		normalized = _normalize_key(key)
		data = self._load_cache_file(cache_type)
		entry = data.get(normalized)
		if entry is None:
			return None
		result = entry.get("data")
		return result

	#============================================
	def _put(self, cache_type: str, key: str, value: object) -> None:
		"""Store a value in the cache.

		Args:
			cache_type: Cache type name.
			key: Raw cache key (will be normalized).
			value: Data to cache (will be serialized).
		"""
		normalized = _normalize_key(key)
		data = self._load_cache_file(cache_type)
		serialized = _serialize_value(value)
		data[normalized] = {
			"timestamp": time.time(),
			"data": serialized,
		}
		self._save_cache_file(cache_type, data)

	#============================================
	def get_search_results(self, cache_type: str, title: str, year: str) -> list:
		"""Retrieve cached search results.

		Args:
			cache_type: "imdb_search" or "tmdb_search".
			title: Movie title.
			year: Release year (may be empty).

		Returns:
			List of SearchResult dicts, or None if cache miss.
		"""
		# normalize components before building the composite key
		clean_title = title.strip().lower()
		clean_year = year.strip()
		key = f"{clean_title}|{clean_year}"
		result = self._get(cache_type, key)
		return result

	#============================================
	def put_search_results(self, cache_type: str, title: str, year: str, results: list) -> None:
		"""Store search results in the cache.

		Args:
			cache_type: "imdb_search" or "tmdb_search".
			title: Movie title.
			year: Release year (may be empty).
			results: List of SearchResult dataclasses.
		"""
		# normalize components before building the composite key
		clean_title = title.strip().lower()
		clean_year = year.strip()
		key = f"{clean_title}|{clean_year}"
		self._put(cache_type, key, results)

	#============================================
	def get_metadata(self, cache_type: str, primary_id: str, secondary_id: str = "") -> dict:
		"""Retrieve cached metadata.

		Args:
			cache_type: "imdb_metadata" or "tmdb_metadata".
			primary_id: Primary ID (imdb_id or tmdb_id).
			secondary_id: Optional secondary ID for composite keys.

		Returns:
			MediaMetadata dict, or None if cache miss.
		"""
		if secondary_id:
			key = f"{primary_id}|{secondary_id}"
		else:
			key = primary_id
		result = self._get(cache_type, key)
		return result

	#============================================
	def put_metadata(self, cache_type: str, primary_id: str, value: object, secondary_id: str = "") -> None:
		"""Store metadata in the cache.

		Args:
			cache_type: "imdb_metadata" or "tmdb_metadata".
			primary_id: Primary ID (imdb_id or tmdb_id).
			value: MediaMetadata dataclass or dict.
			secondary_id: Optional secondary ID for composite keys.
		"""
		if secondary_id:
			key = f"{primary_id}|{secondary_id}"
		else:
			key = primary_id
		self._put(cache_type, key, value)

	#============================================
	def get_parental_guide(self, imdb_id: str) -> dict:
		"""Retrieve cached parental guide data.

		Args:
			imdb_id: IMDB ID string.

		Returns:
			Parental guide dict, or None if cache miss.
		"""
		result = self._get("imdb_parental_guide", imdb_id)
		return result

	#============================================
	def put_parental_guide(self, imdb_id: str, guide: dict) -> None:
		"""Store parental guide data in the cache.

		Args:
			imdb_id: IMDB ID string.
			guide: Parental guide severity dict.
		"""
		self._put("imdb_parental_guide", imdb_id, guide)

	#============================================
	def get_poster_lookup(self, imdb_id: str) -> tuple:
		"""Retrieve cached TMDB poster lookup result.

		Args:
			imdb_id: IMDB ID string.

		Returns:
			Tuple of (tmdb_id, poster_url), or None if cache miss.
		"""
		cached = self._get("tmdb_poster_lookup", imdb_id)
		if cached is None:
			return None
		# stored as a two-element list [tmdb_id, poster_url]
		tmdb_id = cached[0]
		poster_url = cached[1]
		result = (tmdb_id, poster_url)
		return result

	#============================================
	def put_poster_lookup(self, imdb_id: str, tmdb_id: int, poster_url: str) -> None:
		"""Store a TMDB poster lookup result in the cache.

		Args:
			imdb_id: IMDB ID string.
			tmdb_id: TMDB numeric ID.
			poster_url: URL to the poster image.
		"""
		# store as a two-element list
		self._put("tmdb_poster_lookup", imdb_id, [tmdb_id, poster_url])

	#============================================
	def clear(self, cache_type: str = "") -> None:
		"""Wipe one or all cache files.

		Args:
			cache_type: Cache type to clear. If empty, clears all.
		"""
		if cache_type:
			types_to_clear = [cache_type]
		else:
			types_to_clear = list(_CACHE_FILES.keys())
		for ct in types_to_clear:
			path = self._cache_file_path(ct)
			if os.path.exists(path):
				os.unlink(path)

	#============================================
	def remove(self, cache_type: str, key: str) -> bool:
		"""Delete a single entry from a cache file.

		Args:
			cache_type: Cache type name.
			key: Raw cache key to remove.

		Returns:
			True if the entry was found and removed, False otherwise.
		"""
		normalized = _normalize_key(key)
		data = self._load_cache_file(cache_type)
		if normalized not in data:
			return False
		del data[normalized]
		self._save_cache_file(cache_type, data)
		return True
