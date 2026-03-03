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
import PySide6.QtWidgets
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
	# signal to navigate away from the current page (timeout cleanup)
	_stop_requested = PySide6.QtCore.Signal()
	# signal emitted when page fetch is complete (success or failure)
	_fetch_done = PySide6.QtCore.Signal()
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
		# flag to ignore loadFinished from about:blank navigation
		self._navigating_away = False
		# lock to serialize concurrent fetch_html calls from workers
		self._lock = threading.Lock()
		# connect internal signal so worker threads can request loads
		self._load_requested.connect(self._do_load)
		# connect stop signal so worker threads can cancel on timeout
		self._stop_requested.connect(self._do_navigate_away)
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

		Detects the calling thread and uses the appropriate strategy:
		main thread uses QEventLoop, worker threads use threading.Event.
		A threading.Lock serializes concurrent calls from multiple workers.

		Args:
			url: Full URL to load (e.g. https://www.imdb.com/title/tt0109445/).
			timeout_sec: Maximum seconds to wait for page load.

		Returns:
			str: Page HTML content.

		Raises:
			ConnectionError: If page load fails or times out.
		"""
		# detect whether caller is on the Qt main thread
		app = PySide6.QtWidgets.QApplication.instance()
		on_main = (
			app is not None
			and PySide6.QtCore.QThread.currentThread() == app.thread()
		)
		if on_main:
			return self._fetch_html_main_thread(url, timeout_sec)
		return self._fetch_html_worker_thread(url, timeout_sec)

	#============================================
	def _fetch_html_main_thread(
		self, url: str, timeout_sec: int
	) -> str:
		"""Fetch HTML when called from the Qt main thread.

		Uses a local QEventLoop so the main thread stays responsive
		while waiting for the page to load.

		Args:
			url: URL to load.
			timeout_sec: Maximum wait time in seconds.

		Returns:
			str: Page HTML content.

		Raises:
			ConnectionError: If page load fails or times out.
		"""
		with self._lock:
			self._result_html = ""
			self._load_ok = False
			self._navigating_away = False
			# load directly since we are on the main thread
			self._do_load(url)
			# spin a local event loop until page finishes or timeout
			loop = PySide6.QtCore.QEventLoop()
			timer = PySide6.QtCore.QTimer()
			timer.setSingleShot(True)
			timer.timeout.connect(loop.quit)
			self._fetch_done.connect(loop.quit)
			timer.start(timeout_sec * 1000)
			loop.exec()
			# disconnect to avoid stacking connections on repeated calls
			self._fetch_done.disconnect(loop.quit)
			timer.stop()
			if not self._load_ok:
				# navigate away to stop IMDB scripts that crash Chromium
				self._do_navigate_away()
				raise ConnectionError(
					f"IMDB page load failed: {url}"
				)
			if not self._result_html:
				# navigate away to stop IMDB scripts that crash Chromium
				self._do_navigate_away()
				raise ConnectionError(
					f"IMDB page load timed out after {timeout_sec}s: {url}"
				)
			html = self._result_html
			return html

	#============================================
	def _fetch_html_worker_thread(
		self, url: str, timeout_sec: int
	) -> str:
		"""Fetch HTML when called from a worker thread.

		Uses a threading.Event bridged to the main thread via signal.

		Args:
			url: URL to load.
			timeout_sec: Maximum wait time in seconds.

		Returns:
			str: Page HTML content.

		Raises:
			ConnectionError: If page load fails or times out.
		"""
		with self._lock:
			self._event.clear()
			self._result_html = ""
			self._load_ok = False
			self._navigating_away = False
			# emit signal to trigger load on the main thread
			self._load_requested.emit(url)
			# block calling thread until load completes or times out
			finished = self._event.wait(timeout=timeout_sec)
			if not finished:
				# signal main thread to navigate away and stop IMDB scripts
				self._stop_requested.emit()
				raise ConnectionError(
					f"IMDB page load timed out after {timeout_sec}s: {url}"
				)
			if not self._load_ok:
				# signal main thread to navigate away and stop IMDB scripts
				self._stop_requested.emit()
				raise ConnectionError(
					f"IMDB page load failed: {url}"
				)
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
	def _do_navigate_away(self) -> None:
		"""Navigate to about:blank to stop IMDB scripts. Runs on Qt main thread.

		Called after a timeout to prevent ad/tracker scripts from crashing
		the Chromium renderer process.
		"""
		_LOG.info("Transport navigating away after timeout")
		self._navigating_away = True
		self._page.setUrl(PySide6.QtCore.QUrl("about:blank"))

	#============================================
	def _on_load_finished(self, ok: bool) -> None:
		"""Handle page load completion. Runs on the Qt main thread.

		Args:
			ok: True if the page loaded successfully.
		"""
		# ignore the loadFinished from navigating to about:blank
		if self._navigating_away:
			self._navigating_away = False
			return
		if not ok:
			_LOG.warning("Transport page load failed")
			self._load_ok = False
			self._event.set()
			self._fetch_done.emit()
			return
		# extract HTML content from the loaded page
		self._load_ok = True
		self._page.toHtml(self._on_html_received)

	#============================================
	def _on_html_received(self, html: str) -> None:
		"""Store the received HTML and unblock the waiting thread.

		Navigates the page to about:blank after extracting HTML to
		stop IMDB ad/tracker scripts that would otherwise crash the
		Chromium renderer process.

		Args:
			html: Full page HTML content.
		"""
		self._result_html = html
		# check for CAPTCHA indicators (not just JS challenge)
		if "captcha" in html.lower() and "aws-waf" in html.lower():
			page_url = self._page.url().toString()
			_LOG.warning("CAPTCHA detected at %s", page_url)
			self.challenge_needed.emit(page_url)
		# navigate away to stop ad/tracker scripts that crash Chromium
		self._navigating_away = True
		self._page.setUrl(PySide6.QtCore.QUrl("about:blank"))
		# unblock the waiting thread (worker path) and signal done (main path)
		self._event.set()
		self._fetch_done.emit()
