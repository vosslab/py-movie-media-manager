"""Unit tests for the IMDB browser transport with mocked Qt objects.

Tests verify the transport's thread-bridging pattern, timeout behavior,
profile configuration, and signal-based page loading without requiring
a running Qt application.
"""

# Standard Library
import os
import sys
import threading
import unittest.mock

# PIP3 modules
import pytest

# add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


#============================================
def test_transport_module_imports():
	"""Transport module can be imported without a Qt application."""
	import moviemanager.ui.imdb_browser_transport
	assert hasattr(
		moviemanager.ui.imdb_browser_transport,
		"ImdbBrowserTransport"
	)


#============================================
def test_custom_user_agent_defined():
	"""Custom User-Agent string is defined and not empty."""
	import moviemanager.ui.imdb_browser_transport
	ua = moviemanager.ui.imdb_browser_transport._CUSTOM_USER_AGENT
	assert ua
	# should not contain QtWebEngine or HeadlessChrome
	assert "QtWebEngine" not in ua
	assert "HeadlessChrome" not in ua
	# should look like a real Chrome browser
	assert "Chrome" in ua
	assert "Mozilla" in ua


#============================================
def test_profile_storage_dir_defined():
	"""Profile storage directory is under ~/.cache/movie_organizer/."""
	import moviemanager.ui.imdb_browser_transport
	path = moviemanager.ui.imdb_browser_transport._PROFILE_STORAGE_DIR
	assert "movie_organizer" in path
	assert "webengine" in path


#============================================
def test_transport_class_has_required_methods():
	"""ImdbBrowserTransport has all expected public methods."""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	assert hasattr(cls, "fetch_html")
	assert hasattr(cls, "get_profile")
	assert hasattr(cls, "challenge_needed")


#============================================
class FakeTransport:
	"""Minimal stand-in that mirrors ImdbBrowserTransport's internal state.

	Avoids QObject.__new__() restrictions by not inheriting from QObject.
	Uses real threading.Event and mocked Qt objects for testing internal
	methods like _on_html_received and _on_load_finished.
	"""

	def __init__(self):
		"""Set up fake transport with test doubles."""
		self._event = threading.Event()
		self._result_html = ""
		self._load_ok = False
		self._page = unittest.mock.Mock()
		self._load_requested = unittest.mock.Mock()
		self.challenge_needed = unittest.mock.Mock()
		# signal mock for fetch completion
		self._fetch_done = unittest.mock.Mock()
		# signal mock for stop/navigate-away requests
		self._stop_requested = unittest.mock.Mock()
		# flag to ignore loadFinished from about:blank navigation
		self._navigating_away = False
		# lock to serialize concurrent fetch_html calls
		self._lock = threading.Lock()
		# mock the page URL for CAPTCHA detection
		mock_url = unittest.mock.Mock()
		mock_url.toString.return_value = "https://www.imdb.com/title/tt0109445/"
		self._page.url.return_value = mock_url


#============================================
def _bind_fetch_methods(fake):
	"""Bind the real transport fetch methods onto a FakeTransport instance.

	This patches both fetch_html and its internal worker/main-thread helpers
	so that calls through fetch_html dispatch correctly on the fake.
	"""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	fake.fetch_html = cls.fetch_html.__get__(fake)
	fake._fetch_html_main_thread = cls._fetch_html_main_thread.__get__(fake)
	fake._fetch_html_worker_thread = cls._fetch_html_worker_thread.__get__(fake)


#============================================
def test_transport_fetch_html_timeout():
	"""Worker-thread fetch_html raises ConnectionError on timeout."""
	fake = FakeTransport()
	_bind_fetch_methods(fake)
	# use the worker-thread path directly to avoid QEventLoop issues
	# when a QApplication is running from other tests
	with pytest.raises(ConnectionError, match="timed out"):
		fake._fetch_html_worker_thread(
			"https://www.imdb.com/title/tt0109445/", timeout_sec=0,
		)


#============================================
def test_transport_fetch_html_load_failure():
	"""Worker-thread fetch_html raises ConnectionError when page load fails."""
	fake = FakeTransport()
	_bind_fetch_methods(fake)

	# make the mock signal's emit simulate a load failure
	def fake_emit(url):
		fake._load_ok = False
		fake._event.set()

	fake._load_requested.emit.side_effect = fake_emit
	# use the worker-thread path directly to avoid QEventLoop issues
	with pytest.raises(ConnectionError, match="load failed"):
		fake._fetch_html_worker_thread(
			"https://www.imdb.com/title/tt0109445/", timeout_sec=5,
		)


#============================================
def test_transport_on_html_received_sets_event():
	"""_on_html_received stores HTML and sets the threading event."""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	fake = FakeTransport()
	# bind the real _on_html_received method
	bound_handler = cls._on_html_received.__get__(fake)
	sample_html = "<html><body>Test page</body></html>"
	bound_handler(sample_html)
	assert fake._result_html == sample_html
	assert fake._event.is_set()


#============================================
def test_transport_on_load_finished_failure():
	"""_on_load_finished with ok=False sets event without HTML."""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	fake = FakeTransport()
	# bind the real _on_load_finished method
	bound_handler = cls._on_load_finished.__get__(fake)
	bound_handler(False)
	assert fake._event.is_set()
	assert fake._load_ok is False
	assert fake._result_html == ""


#============================================
def test_transport_on_load_finished_success():
	"""_on_load_finished with ok=True calls toHtml to extract content."""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	fake = FakeTransport()
	# add _on_html_received method that the real _on_load_finished references
	fake._on_html_received = unittest.mock.Mock()
	bound_handler = cls._on_load_finished.__get__(fake)
	bound_handler(True)
	assert fake._load_ok is True
	# page.toHtml should have been called with the callback
	fake._page.toHtml.assert_called_once()


#============================================
def test_transport_captcha_detection():
	"""_on_html_received emits challenge_needed when CAPTCHA detected."""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	fake = FakeTransport()
	bound_handler = cls._on_html_received.__get__(fake)
	# HTML containing captcha indicators
	captcha_html = (
		"<html><body>Please solve the aws-waf CAPTCHA below</body></html>"
	)
	bound_handler(captcha_html)
	# challenge_needed should have been emitted
	fake.challenge_needed.emit.assert_called_once()


#============================================
def test_transport_no_captcha_no_signal():
	"""_on_html_received does not emit challenge_needed for normal pages."""
	import moviemanager.ui.imdb_browser_transport
	cls = moviemanager.ui.imdb_browser_transport.ImdbBrowserTransport
	fake = FakeTransport()
	bound_handler = cls._on_html_received.__get__(fake)
	# normal HTML without captcha
	normal_html = "<html><body>Normal movie page</body></html>"
	bound_handler(normal_html)
	# challenge_needed should NOT have been emitted
	fake.challenge_needed.emit.assert_not_called()
