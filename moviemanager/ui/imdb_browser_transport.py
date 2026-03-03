"""QWebEnginePage-based HTTP transport for IMDB pages.

Uses the Chromium engine to solve AWS WAF JavaScript challenges
automatically. The browser engine executes challenge scripts and
maintains immunity cookies, bypassing blocks that defeat curl_cffi.
"""

# Standard Library
import os
import logging
import threading

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWebEngineCore


# module logger
_LOG = logging.getLogger(__name__)

# User-Agent string that IMDB accepts (avoids QtWebEngine/HeadlessChrome bans)
_CUSTOM_USER_AGENT = (
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
	"AppleWebKit/537.36 (KHTML, like Gecko) "
	"Chrome/124.0.0.0 Safari/537.36"
)

# directory for persistent cookie storage
_PROFILE_STORAGE_DIR = os.path.join(
	os.path.expanduser("~"), ".cache", "movie_organizer", "webengine"
)


#============================================
class ImdbBrowserTransport(PySide6.QtCore.QObject):
	"""QWebEnginePage transport for loading IMDB pages through Chromium.

	The browser engine solves AWS WAF JavaScript challenges automatically.
	Cookies persist on disk so immunity tokens survive across sessions.

	Must be created on the Qt main thread. Worker threads call fetch_html()
	which bridges to the main thread via signals and threading.Event.
	"""

	# signal for requesting a page load from the main thread
	_load_requested = PySide6.QtCore.Signal(str)
	# signal emitted when a WAF CAPTCHA is detected (not just JS challenge)
	challenge_needed = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, parent=None):
		"""Initialize the transport with a persistent browser profile.

		Args:
			parent: Parent QObject (usually the main window or app).
		"""
		super().__init__(parent)
		# create persistent profile with disk-based cookie storage
		self._profile = PySide6.QtWebEngineCore.QWebEngineProfile(
			"imdb_transport", self
		)
		# set storage path so cookies survive between app launches
		self._profile.setPersistentStoragePath(_PROFILE_STORAGE_DIR)
		self._profile.setPersistentCookiesPolicy(
			PySide6.QtWebEngineCore.QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
		)
		# set custom User-Agent to avoid IMDB banning QtWebEngine/HeadlessChrome
		self._profile.setHttpUserAgent(_CUSTOM_USER_AGENT)
		# create the page that will load IMDB URLs
		self._page = PySide6.QtWebEngineCore.QWebEnginePage(
			self._profile, self
		)
		# internal state for thread bridging
		self._result_html = ""
		self._load_ok = False
		self._event = threading.Event()
		# connect internal signal so worker threads can request loads
		self._load_requested.connect(self._do_load)
		# connect page load completion
		self._page.loadFinished.connect(self._on_load_finished)

	#============================================
	def get_profile(self) -> PySide6.QtWebEngineCore.QWebEngineProfile:
		"""Return the persistent profile for shared use with challenge dialog.

		Returns:
			QWebEngineProfile: The persistent browser profile.
		"""
		return self._profile

	#============================================
	def fetch_html(self, url: str, timeout_sec: int = 30) -> str:
		"""Load a URL and return the page HTML. Thread-safe.

		Blocks the calling thread until the page finishes loading
		on the Qt main thread. The Chromium engine handles any WAF
		JavaScript challenge automatically during the load.

		Args:
			url: Full URL to load (e.g. https://www.imdb.com/title/tt0109445/).
			timeout_sec: Maximum seconds to wait for page load.

		Returns:
			str: Page HTML content.

		Raises:
			ConnectionError: If page load fails or times out.
		"""
		self._event.clear()
		self._result_html = ""
		self._load_ok = False
		# emit signal to trigger load on the main thread
		self._load_requested.emit(url)
		# block calling thread until load completes or times out
		finished = self._event.wait(timeout=timeout_sec)
		if not finished:
			raise ConnectionError(
				f"IMDB page load timed out after {timeout_sec}s: {url}"
			)
		if not self._load_ok:
			raise ConnectionError(f"IMDB page load failed: {url}")
		html = self._result_html
		return html

	#============================================
	def _do_load(self, url: str) -> None:
		"""Load a URL in the QWebEnginePage. Runs on the Qt main thread.

		Args:
			url: URL string to load.
		"""
		_LOG.info("Transport loading: %s", url)
		self._page.load(PySide6.QtCore.QUrl(url))

	#============================================
	def _on_load_finished(self, ok: bool) -> None:
		"""Handle page load completion. Runs on the Qt main thread.

		Args:
			ok: True if the page loaded successfully.
		"""
		if not ok:
			_LOG.warning("Transport page load failed")
			self._load_ok = False
			self._event.set()
			return
		# extract HTML content from the loaded page
		self._load_ok = True
		self._page.toHtml(self._on_html_received)

	#============================================
	def _on_html_received(self, html: str) -> None:
		"""Store the received HTML and unblock the waiting thread.

		Args:
			html: Full page HTML content.
		"""
		self._result_html = html
		# check for CAPTCHA indicators (not just JS challenge)
		if "captcha" in html.lower() and "aws-waf" in html.lower():
			page_url = self._page.url().toString()
			_LOG.warning("CAPTCHA detected at %s", page_url)
			self.challenge_needed.emit(page_url)
		self._event.set()
