"""Subtitle download service using OpenSubtitles API."""

# Standard Library
import os
import time
import logging
import threading

# PIP3 modules
import requests

# local repo modules
import moviemanager.api.download_errors
import moviemanager.core.settings
import moviemanager.scraper.subtitle_scraper


# module logger
_LOG = logging.getLogger(__name__)

# JWT token max age in seconds (23 hours, 1h safety margin on 24h)
_TOKEN_MAX_AGE_SECS = 23 * 3600


#============================================
class SubtitleService:
	"""Download subtitles from OpenSubtitles with JWT auth lifecycle.

	Manages a thread-safe cached SubtitleScraper instance that
	authenticates once and is reused across all subtitle download
	threads. The JWT token is valid for 24 hours per API docs.
	"""

	#============================================
	def __init__(
		self,
		settings: moviemanager.core.settings.Settings,
		provider=None,
	):
		"""Initialize the subtitle service.

		Args:
			settings: Application settings with OpenSubtitles credentials.
			provider: Optional pre-configured SubtitleProvider instance.
				If given, used directly (skipping internal scraper creation).
		"""
		self._settings = settings
		self._external_provider = provider
		# cached subtitle scraper with JWT token (valid 24h)
		self._subtitle_scraper = None
		self._subtitle_scraper_lock = threading.Lock()
		# timestamp of last successful login (for staleness check)
		self._login_time = 0.0
		# whether external provider has been logged in
		self._external_logged_in = False
		# set True when API returns 406 (quota exhausted for session)
		self._quota_exhausted = False

	#============================================
	def _ensure_provider_logged_in(self, provider) -> None:
		"""Authenticate an external provider if not already done.

		OpenSubtitles requires JWT auth for downloads. Providers
		from the registry pipeline are created with only an API key,
		so login must happen before the first download.

		Args:
			provider: SubtitleScraper instance to authenticate.

		Raises:
			DownloadError: If credentials are missing or login fails.
		"""
		if self._external_logged_in:
			# check token freshness
			token_age = time.time() - self._login_time
			if token_age < _TOKEN_MAX_AGE_SECS:
				return
			_LOG.info(
				"OpenSubtitles JWT token expired (%.0fh old),"
				" re-authenticating",
				token_age / 3600,
			)
			self._external_logged_in = False
		_Cat = moviemanager.api.download_errors.DownloadCategory
		_Err = moviemanager.api.download_errors.DownloadError
		# check for login method (duck typing)
		if not hasattr(provider, "login"):
			return
		osub_user = self._settings.opensubtitles_username
		osub_pass = self._settings.opensubtitles_password
		if not osub_user or not osub_pass:
			raise _Err(
				_Cat.auth_failed,
				"OpenSubtitles username/password required "
				"for downloads. "
				"Set them in Settings > API Keys."
			)
		login_ok = provider.login(osub_user, osub_pass)
		if not login_ok:
			raise _Err(
				_Cat.auth_failed,
				"OpenSubtitles login failed. "
				"Check username/password in Settings > API Keys."
			)
		self._external_logged_in = True
		self._login_time = time.time()

	#============================================
	def _get_subtitle_scraper(self):
		"""Return a cached, authenticated SubtitleScraper.

		If an external provider was injected at init time, returns
		it directly. Otherwise, thread-safe: uses a lock so only
		the first thread logs in, and all others wait and reuse
		the cached instance. JWT token is valid 24 hours per API docs.

		Returns:
			Authenticated SubtitleScraper instance.

		Raises:
			DownloadError: If credentials are missing or login fails.
		"""
		_Cat = moviemanager.api.download_errors.DownloadCategory
		_Err = moviemanager.api.download_errors.DownloadError
		# use injected provider if available (still needs login)
		if self._external_provider is not None:
			self._ensure_provider_logged_in(self._external_provider)
			return self._external_provider
		# fast path: already cached and token is fresh
		if self._subtitle_scraper is not None:
			token_age = time.time() - self._login_time
			if token_age < _TOKEN_MAX_AGE_SECS:
				return self._subtitle_scraper
			# token is stale, invalidate cache
			_LOG.info(
				"OpenSubtitles JWT token expired (%.0fh old),"
				" re-authenticating",
				token_age / 3600,
			)
			self._subtitle_scraper = None
		# serialize login so only one thread authenticates
		with self._subtitle_scraper_lock:
			# re-check after acquiring lock (another thread may have logged in)
			if self._subtitle_scraper is not None:
				return self._subtitle_scraper
			# validate credentials
			api_key = self._settings.opensubtitles_api_key
			if not api_key:
				raise _Err(
					_Cat.no_api_key,
					"OpenSubtitles API key is not configured. "
					"Set it in Settings > API Keys."
				)
			osub_user = self._settings.opensubtitles_username
			osub_pass = self._settings.opensubtitles_password
			if not osub_user or not osub_pass:
				raise _Err(
					_Cat.auth_failed,
					"OpenSubtitles username/password required "
					"for downloads. "
					"Set them in Settings > API Keys."
				)
			scraper = (
				moviemanager.scraper.subtitle_scraper.SubtitleScraper(
					api_key
				)
			)
			login_ok = scraper.login(osub_user, osub_pass)
			if not login_ok:
				raise _Err(
					_Cat.auth_failed,
					"OpenSubtitles login failed. "
					"Check username/password in Settings > API Keys."
				)
			# cache for reuse across all subtitle download threads
			self._subtitle_scraper = scraper
			self._login_time = time.time()
			return scraper

	#============================================
	def download_subtitles(
		self, movie, languages: str = "en",
	) -> list:
		"""Download subtitles for a movie from OpenSubtitles.

		Args:
			movie: Movie instance with imdb_id set.
			languages: Comma-separated language codes.

		Returns:
			list: Paths of downloaded subtitle files.

		Raises:
			DownloadError: With category describing the failure reason.
		"""
		_Cat = moviemanager.api.download_errors.DownloadCategory
		_Err = moviemanager.api.download_errors.DownloadError
		if self._quota_exhausted:
			raise _Err(
				_Cat.quota_exceeded,
				"OpenSubtitles daily download quota exhausted."
				" Restart the application after midnight UTC.",
			)
		if not movie.imdb_id:
			raise _Err(_Cat.no_imdb_id, "No IMDB ID for this movie")
		if not movie.path:
			raise _Err(_Cat.no_path, "Movie has no folder path")
		scraper = self._get_subtitle_scraper()
		try:
			results = scraper.search(
				imdb_id=movie.imdb_id, languages=languages
			)
		except requests.exceptions.Timeout:
			raise _Err(_Cat.timeout, "OpenSubtitles API timed out")
		except requests.exceptions.ConnectionError as exc:
			raise _Err(_Cat.network_error, str(exc)[:200])
		except requests.exceptions.RequestException as exc:
			raise _Err(_Cat.api_error, str(exc)[:200])
		if not results:
			raise _Err(_Cat.no_results, "No subtitles found")
		# group by language, take best per language (highest download count)
		downloaded = []
		by_lang = {}
		for r in results:
			lang = r.get("language", "en")
			if lang not in by_lang:
				by_lang[lang] = r
			elif (r.get("download_count", 0)
					> by_lang[lang].get("download_count", 0)):
				by_lang[lang] = r
		for lang, best in by_lang.items():
			file_id = best.get("file_id", 0)
			if not file_id:
				continue
			# name subtitle file with language code
			srt_filename = f"subtitles.{lang}.srt"
			srt_path = os.path.join(movie.path, srt_filename)
			# skip if already exists
			if os.path.exists(srt_path):
				downloaded.append(srt_path)
				continue
			try:
				result_path = scraper.download(file_id, srt_path)
			except requests.exceptions.HTTPError as exc:
				status = getattr(
					exc.response, "status_code", None
				)
				if status == 401:
					# token may have expired, invalidate and retry once
					_LOG.info(
						"OpenSubtitles 401 on download,"
						" re-authenticating and retrying"
					)
					self._subtitle_scraper = None
					try:
						scraper = self._get_subtitle_scraper()
						result_path = scraper.download(
							file_id, srt_path
						)
						if result_path:
							downloaded.append(result_path)
						continue
					except Exception:
						pass
					raise _Err(
						_Cat.auth_failed,
						"OpenSubtitles download auth failed (401). "
						"Check username/password in "
						"Settings > API Keys."
					)
				if status == 406:
					# 406 = quota exhausted per OpenSubtitles API
					self._quota_exhausted = True
					body = ""
					if exc.response is not None:
						body = exc.response.text[:300]
					_LOG.warning(
						"OpenSubtitles download quota exhausted: %s",
						body,
					)
					raise _Err(
						_Cat.quota_exceeded,
						"OpenSubtitles daily download quota"
						" exhausted (20/day for free accounts)."
						" Resets at midnight UTC.",
					)
				# include API response body for diagnostics
				body = ""
				if exc.response is not None:
					body = exc.response.text[:200]
				msg = f"{status}: {body}" if body else str(exc)[:200]
				raise _Err(_Cat.download_failed, msg)
			except requests.exceptions.Timeout:
				raise _Err(
					_Cat.timeout,
					"OpenSubtitles download timed out",
				)
			except requests.exceptions.ConnectionError as exc:
				raise _Err(_Cat.network_error, str(exc)[:200])
			except requests.exceptions.RequestException as exc:
				raise _Err(
					_Cat.download_failed, str(exc)[:200]
				)
			if result_path:
				downloaded.append(result_path)
		return downloaded
