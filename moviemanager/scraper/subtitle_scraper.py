"""OpenSubtitles REST API client for subtitle search and download."""

# Standard Library
import time
import random
import logging

# PIP3 modules
import requests

# local repo modules
import moviemanager.scraper.interfaces


# OpenSubtitles REST API base URL
_API_BASE = "https://api.opensubtitles.com/api/v1"

# module logger
_log = logging.getLogger(__name__)


#============================================
class SubtitleScraper(
	moviemanager.scraper.interfaces.SubtitleProvider,
):
	"""Client for searching and downloading subtitles via OpenSubtitles API."""

	# capabilities advertised by this scraper
	capabilities = {
		moviemanager.scraper.interfaces.ProviderCapability.SUBTITLES,
	}

	# settings keys required to instantiate this scraper
	requires_keys = ["opensubtitles_api_key"]

	#============================================
	def __init__(self, api_key: str):
		"""Initialize with an OpenSubtitles API key.

		Args:
			api_key: OpenSubtitles REST API key.
		"""
		self._api_key = api_key
		self._headers = {
			"Accept": "*/*",
			"Api-Key": api_key,
			"Content-Type": "application/json",
			"User-Agent": "MovieMediaManager v1.0",
		}
		# JWT token from login(), added to download requests
		self._jwt_token = ""
		# timestamp of last API request for rate-limit enforcement
		self._last_request_time = 0.0

	#============================================
	def _rate_limit_wait(self) -> None:
		"""Enforce minimum 1-second gap between API requests.

		OpenSubtitles rate-limits to 1 req/sec per IP for most
		endpoints. Adds a small random jitter on top.
		"""
		now = time.time()
		elapsed = now - self._last_request_time
		# wait at least 1 second plus small jitter
		min_gap = 1.0 + random.random() * 0.5
		if elapsed < min_gap:
			time.sleep(min_gap - elapsed)
		self._last_request_time = time.time()

	#============================================
	def login(self, username: str, password: str) -> bool:
		"""Authenticate with OpenSubtitles and store JWT token.

		The JWT is valid for 24 hours per API docs. It is required
		for download requests (otherwise limited to 5/day per IP).

		Args:
			username: OpenSubtitles account username.
			password: OpenSubtitles account password.

		Returns:
			True if login succeeded, False otherwise.
		"""
		# enforce 1 req/sec rate limit
		self._rate_limit_wait()
		payload = {
			"username": username,
			"password": password,
		}
		response = requests.post(
			f"{_API_BASE}/login",
			headers=self._headers,
			json=payload,
			timeout=30,
		)
		if response.status_code != 200:
			_log.warning(
				"OpenSubtitles login failed: %s %s",
				response.status_code, response.text[:200]
			)
			return False
		data = response.json()
		token = data.get("token", "")
		if not token:
			_log.warning("OpenSubtitles login response missing token")
			return False
		self._jwt_token = token
		_log.info("OpenSubtitles login successful")
		return True

	#============================================
	def search(self, imdb_id: str = "", languages: str = "en") -> list:
		"""Search for subtitles by IMDB ID.

		Args:
			imdb_id: IMDB identifier string (tt format).
			languages: Comma-separated language codes.

		Returns:
			list: List of subtitle result dicts with keys:
				file_id, language, release, download_count.
		"""
		# enforce 1 req/sec rate limit
		self._rate_limit_wait()
		params = {
			"imdb_id": imdb_id,
			"languages": languages,
		}
		response = requests.get(
			f"{_API_BASE}/subtitles",
			headers=self._headers,
			params=params,
			timeout=30,
		)
		response.raise_for_status()
		data = response.json()
		# parse results
		results = []
		for item in data.get("data", []):
			attributes = item.get("attributes", {})
			files = attributes.get("files", [])
			if not files:
				continue
			file_id = files[0].get("file_id", 0)
			result = {
				"file_id": file_id,
				"language": attributes.get("language", ""),
				"release": attributes.get("release", ""),
				"download_count": attributes.get("download_count", 0),
			}
			results.append(result)
		return results

	#============================================
	def search_subtitles(
		self, imdb_id: str, languages: list,
	) -> list:
		"""Search for subtitles by IMDB ID (SubtitleProvider ABC).

		Wraps search() converting the languages list to a
		comma-separated string.

		Args:
			imdb_id: IMDB identifier string (tt format).
			languages: List of language codes.

		Returns:
			list: List of subtitle result dicts.
		"""
		lang_str = ",".join(languages) if languages else "en"
		results = self.search(imdb_id=imdb_id, languages=lang_str)
		return results

	#============================================
	def download_subtitle(
		self, file_id: int, output_path: str,
	) -> str:
		"""Download a subtitle file by file ID (SubtitleProvider ABC).

		Wraps download() to match the ABC signature.

		Args:
			file_id: Subtitle file ID from search results.
			output_path: Destination file path.

		Returns:
			str: Path to the downloaded subtitle file.
		"""
		result = self.download(file_id, output_path)
		return result

	#============================================
	def download(self, file_id: int, output_path: str) -> str:
		"""Download a subtitle file by file ID.

		Sends JWT Authorization header if login() was called.

		Args:
			file_id: OpenSubtitles file ID from search results.
			output_path: Path to save the subtitle file.

		Returns:
			str: Path to the downloaded subtitle file.
		"""
		# enforce 1 req/sec rate limit
		self._rate_limit_wait()
		# build headers with JWT auth if available
		download_headers = dict(self._headers)
		if self._jwt_token:
			download_headers["Authorization"] = f"Bearer {self._jwt_token}"
		# request download link
		response = requests.post(
			f"{_API_BASE}/download",
			headers=download_headers,
			json={"file_id": file_id},
			timeout=30,
		)
		if response.status_code != 200:
			_log.warning(
				"OpenSubtitles download request failed: %s %s",
				response.status_code, response.text[:300],
			)
			response.raise_for_status()
		download_data = response.json()
		download_link = download_data.get("link", "")
		if not download_link:
			return ""
		# download the actual subtitle file
		time.sleep(random.random())
		sub_response = requests.get(download_link, timeout=30)
		sub_response.raise_for_status()
		with open(output_path, "wb") as f:
			f.write(sub_response.content)
		return output_path
