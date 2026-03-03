"""Dialog for solving IMDB AWS WAF challenges via embedded browser."""

# Standard Library
import logging

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets
import PySide6.QtWebEngineCore
import PySide6.QtWebEngineWidgets


# module logger
_LOG = logging.getLogger(__name__)


#============================================
class ImdbChallengeDialog(PySide6.QtWidgets.QDialog):
	"""Embedded browser dialog for completing IMDB WAF challenges.

	Loads an IMDB URL in QWebEngineView so the user can solve
	any CAPTCHA or JavaScript challenge. After completion, cookies
	from the browser session are extracted for use by the scraper.
	"""

	#============================================
	def __init__(
		self, url: str, parent=None,
		seed_cookies: list = None, profile=None,
	):
		"""Initialize the challenge dialog.

		Args:
			url: IMDB URL to load (usually a title page).
			parent: Parent QWidget.
			seed_cookies: Optional list of cookie dicts to inject before loading.
			profile: Optional QWebEngineProfile to share with browser transport.
				When provided, cookies persist across transport and dialog sessions.
		"""
		super().__init__(parent)
		self.setWindowTitle("IMDB Challenge - Complete to Continue")
		self.resize(900, 700)
		self._url = url
		self._cookies = []
		# use shared profile when provided, otherwise create isolated one
		if profile is not None:
			self._profile = profile
		else:
			self._profile = PySide6.QtWebEngineCore.QWebEngineProfile(
				"imdb_challenge", self
			)
		self._page = PySide6.QtWebEngineCore.QWebEnginePage(
			self._profile, self
		)
		self._web_view = PySide6.QtWebEngineWidgets.QWebEngineView(self)
		self._web_view.setPage(self._page)
		# connect cookie signal to collect cookies as they arrive
		cookie_store = self._profile.cookieStore()
		cookie_store.cookieAdded.connect(self._on_cookie_added)
		# inject seed cookies before loading
		if seed_cookies:
			self._inject_seed_cookies(seed_cookies)
		# build the layout
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# instruction label
		label = PySide6.QtWidgets.QLabel(
			"Complete the challenge below, then click Done."
		)
		layout.addWidget(label)
		# web view fills most of the dialog
		layout.addWidget(self._web_view)
		# button row at the bottom
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(cancel_btn)
		done_btn = PySide6.QtWidgets.QPushButton("Done")
		done_btn.clicked.connect(self._on_done)
		btn_layout.addWidget(done_btn)
		layout.addLayout(btn_layout)
		# load the IMDB URL
		self._page.load(PySide6.QtCore.QUrl(url))

	#============================================
	def _inject_seed_cookies(self, cookies: list) -> None:
		"""Inject seed cookies into the web engine profile.

		Args:
			cookies: List of cookie dicts with name, value, domain keys.
		"""
		cookie_store = self._profile.cookieStore()
		for cookie_dict in cookies:
			name = cookie_dict.get("name", "")
			value = cookie_dict.get("value", "")
			domain = cookie_dict.get("domain", "")
			if not name or not value:
				continue
			cookie = PySide6.QtCore.QByteArray(
				f"{name}={value}".encode()
			)
			# parse the raw cookie bytes into a QNetworkCookie
			parsed = PySide6.QtNetwork.QNetworkCookie.parseCookies(cookie)
			if parsed:
				qt_cookie = parsed[0]
				qt_cookie.setDomain(domain)
				cookie_store.setCookie(qt_cookie)

	#============================================
	def _on_cookie_added(self, cookie) -> None:
		"""Collect cookies as the browser receives them.

		Args:
			cookie: QNetworkCookie instance from the web engine.
		"""
		domain = cookie.domain()
		# only collect IMDB-related cookies
		if "imdb.com" not in domain:
			return
		cookie_dict = {
			"name": bytes(cookie.name()).decode("utf-8", errors="replace"),
			"value": bytes(cookie.value()).decode("utf-8", errors="replace"),
			"domain": domain,
			"path": cookie.path(),
			"secure": cookie.isSecure(),
		}
		self._cookies.append(cookie_dict)

	#============================================
	def _on_done(self) -> None:
		"""Handle the Done button click."""
		_LOG.info(
			"WAF challenge dialog done, collected %d cookies",
			len(self._cookies),
		)
		self.accept()

	#============================================
	def get_cookies(self) -> list:
		"""Return collected IMDB cookies from the browser session.

		Returns:
			list: List of cookie dicts with name, value, domain, path, secure.
		"""
		# deduplicate by name+domain, keeping the latest value
		seen = {}
		for cookie in self._cookies:
			key = (cookie["name"], cookie["domain"])
			seen[key] = cookie
		result = list(seen.values())
		return result
