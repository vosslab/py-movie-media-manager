"""Smoke tests covering scan/scrape/rename pipeline and GUI batch mode."""

# Standard Library
import os
import unittest.mock

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.models.movie
import moviemanager.core.settings
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types
import moviemanager.ui.main_window
import moviemanager.ui.dialogs.movie_chooser


# ============================================
# helpers
# ============================================

#============================================
def _touch(path: str) -> None:
	"""Create an empty file, making parent directories as needed."""
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w") as f:
		f.write("")


#============================================
def _create_movie_dirs(tmp_path) -> str:
	"""Create two movie folders with .mkv files under tmp_path.

	Returns:
		Root directory path containing the movie folders.
	"""
	root = str(tmp_path / "movies")
	# The Dark Knight
	dk_dir = os.path.join(root, "The.Dark.Knight.2008.BluRay")
	dk_file = os.path.join(dk_dir, "The.Dark.Knight.2008.BluRay.x264.mkv")
	_touch(dk_file)
	# The Godfather
	gf_dir = os.path.join(root, "The.Godfather.1972.Remastered")
	gf_file = os.path.join(gf_dir, "The.Godfather.1972.Remastered.mkv")
	_touch(gf_file)
	return root


#============================================
def _build_dark_knight_metadata() -> moviemanager.scraper.types.MediaMetadata:
	"""Build MediaMetadata for The Dark Knight."""
	metadata = moviemanager.scraper.types.MediaMetadata(
		title="The Dark Knight",
		year="2008",
		imdb_id="tt0468569",
		tmdb_id=155,
		director="Christopher Nolan",
		certification="PG-13",
		rating=9.0,
		genres=["Action", "Crime", "Drama"],
		plot="Batman raises the stakes in his war on crime.",
	)
	return metadata


#============================================
def _build_godfather_metadata() -> moviemanager.scraper.types.MediaMetadata:
	"""Build MediaMetadata for The Godfather."""
	metadata = moviemanager.scraper.types.MediaMetadata(
		title="The Godfather",
		year="1972",
		imdb_id="tt0068646",
		tmdb_id=238,
		director="Francis Ford Coppola",
		certification="R",
		rating=9.2,
		genres=["Crime", "Drama"],
		plot="The aging patriarch of an organized crime dynasty.",
	)
	return metadata


#============================================
def _mock_search(title: str, year: str = "") -> list:
	"""Return SearchResult list matching by title keyword.

	Args:
		title: Movie title to search for.
		year: Optional year (unused, accepted for signature compat).

	Returns:
		List with one SearchResult matching the title, or empty.
	"""
	title_lower = title.lower()
	if "dark knight" in title_lower:
		result = moviemanager.scraper.types.SearchResult(
			title="The Dark Knight",
			year="2008",
			imdb_id="tt0468569",
			tmdb_id=155,
			overview="Batman raises the stakes.",
		)
		return [result]
	if "godfather" in title_lower:
		result = moviemanager.scraper.types.SearchResult(
			title="The Godfather",
			year="1972",
			imdb_id="tt0068646",
			tmdb_id=238,
			overview="The aging patriarch.",
		)
		return [result]
	return []


#============================================
def _mock_get_metadata(tmdb_id: int = 0, imdb_id: str = "") -> moviemanager.scraper.types.MediaMetadata:
	"""Return metadata matching by imdb_id.

	Args:
		tmdb_id: TMDB ID (unused, accepted for signature compat).
		imdb_id: IMDB ID to look up.

	Returns:
		MediaMetadata for the matching movie.
	"""
	if imdb_id == "tt0468569":
		return _build_dark_knight_metadata()
	if imdb_id == "tt0068646":
		return _build_godfather_metadata()
	# fallback empty metadata
	return moviemanager.scraper.types.MediaMetadata()


# ============================================
# API-level tests (no PySide6)
# ============================================

#============================================
class TestScanFindsMovies:
	"""Test that scan_directory discovers movie folders."""

	def test_scan_finds_both_movies(self, tmp_path):
		"""Scan should find two movies with correct titles and years."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		assert len(movies) == 2
		# collect titles and years
		titles = sorted(m.title for m in movies)
		years = sorted(m.year for m in movies)
		assert titles == ["The Dark Knight", "The Godfather"]
		assert years == ["1972", "2008"]


#============================================
class TestScrapeMovies:
	"""Test scraping with mocked IMDB scraper."""

	def test_scrape_dark_knight(self, tmp_path):
		"""Scrape Dark Knight should populate metadata and write NFO."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# find the Dark Knight movie
		dk = [m for m in movies if "Dark Knight" in m.title][0]
		# mock the scraper methods
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"get_metadata", side_effect=_mock_get_metadata,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			api.scrape_movie(dk, imdb_id="tt0468569")
		# verify metadata was applied
		assert dk.title == "The Dark Knight"
		assert dk.year == "2008"
		assert dk.director == "Christopher Nolan"
		assert dk.certification == "PG-13"
		assert dk.rating == 9.0
		assert dk.scraped is True
		# verify NFO was written
		assert dk.nfo_path
		assert os.path.isfile(dk.nfo_path)

	def test_scrape_godfather(self, tmp_path):
		"""Scrape Godfather should populate metadata and write NFO."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# find the Godfather movie
		gf = [m for m in movies if "Godfather" in m.title][0]
		# mock the scraper methods
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"get_metadata", side_effect=_mock_get_metadata,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			api.scrape_movie(gf, imdb_id="tt0068646")
		# verify metadata
		assert gf.title == "The Godfather"
		assert gf.year == "1972"
		assert gf.director == "Francis Ford Coppola"
		assert gf.certification == "R"
		assert gf.rating == 9.2
		assert gf.scraped is True
		assert gf.nfo_path
		assert os.path.isfile(gf.nfo_path)


#============================================
class TestRenameAfterScrape:
	"""Test rename pipeline after scraping."""

	def test_rename_after_scrape(self, tmp_path):
		"""Scrape both movies then rename, verifying final paths."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# mock and scrape both
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"get_metadata", side_effect=_mock_get_metadata,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			for m in movies:
				imdb_id = "tt0468569" if "Dark Knight" in m.title else "tt0068646"
				api.scrape_movie(m, imdb_id=imdb_id)
		# rename both movies (not dry run)
		for m in movies:
			api.rename_movie(m, dry_run=False)
		# verify final directory names
		dk = [m for m in movies if "Dark Knight" in m.title][0]
		gf = [m for m in movies if "Godfather" in m.title][0]
		assert os.path.basename(dk.path) == "The_Dark_Knight-2008"
		assert os.path.basename(gf.path) == "The_Godfather-1972"
		# verify video files exist in new locations
		assert dk.video_file is not None
		assert os.path.isfile(dk.video_file.path)
		assert gf.video_file is not None
		assert os.path.isfile(gf.video_file.path)


#============================================
class TestFullPipeline:
	"""End-to-end: scan, scrape, rename, verify."""

	def test_full_pipeline(self, tmp_path):
		"""Full pipeline: scan, scrape all, rename all, verify state."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		# step 1: scan
		movies = api.scan_directory(root)
		assert len(movies) == 2
		assert api.get_movie_count() == 2
		assert api.get_scraped_count() == 0
		# step 2: scrape all
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"get_metadata", side_effect=_mock_get_metadata,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			for m in movies:
				imdb_id = "tt0468569" if "Dark Knight" in m.title else "tt0068646"
				api.scrape_movie(m, imdb_id=imdb_id)
		assert api.get_scraped_count() == 2
		# step 3: rename all
		for m in movies:
			pairs = api.rename_movie(m, dry_run=False)
			assert len(pairs) >= 1
		# step 4: verify final state
		dk = [m for m in movies if "Dark Knight" in m.title][0]
		gf = [m for m in movies if "Godfather" in m.title][0]
		# directories renamed correctly
		assert "The_Dark_Knight-2008" in dk.path
		assert "The_Godfather-1972" in gf.path
		# NFO files exist in new locations
		assert os.path.isfile(dk.nfo_path)
		assert os.path.isfile(gf.nfo_path)
		# video files exist
		assert os.path.isfile(dk.video_file.path)
		assert os.path.isfile(gf.video_file.path)


# ============================================
# GUI-level tests (pytest-qt)
# ============================================

#============================================
class TestMainWindowScan:
	"""Test MainWindow scan with mocked settings."""

	def test_main_window_scan(self, qtbot, tmp_path, monkeypatch):
		"""MainWindow should scan and display 2 movies."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		# patch save_settings for entire test lifetime (including teardown)
		monkeypatch.setattr(
			moviemanager.core.settings, "save_settings", lambda *a, **kw: None,
		)
		window = moviemanager.ui.main_window.MainWindow(
			settings, directory=root,
		)
		qtbot.addWidget(window)
		# wait for the scan worker to complete
		qtbot.waitUntil(
			lambda: window._movie_panel._table_model.rowCount() == 2,
			timeout=5000,
		)
		# verify 2 movies in the table
		assert window._movie_panel._table_model.rowCount() == 2


#============================================
class TestMainWindowLastDirectory:
	"""Test startup behavior for last opened directory."""

	def test_main_window_auto_opens_last_directory(
		self, qtbot, tmp_path, monkeypatch
	):
		"""MainWindow should auto-open last_directory without prompt."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		settings.last_directory = root
		# patch save_settings for entire test lifetime (including teardown)
		monkeypatch.setattr(
			moviemanager.core.settings, "save_settings", lambda *a, **kw: None,
		)
		question_called = {"called": False}

		def _question_stub(*args, **kwargs):
			question_called["called"] = True
			return PySide6.QtWidgets.QMessageBox.StandardButton.No

		monkeypatch.setattr(
			PySide6.QtWidgets.QMessageBox, "question", _question_stub,
		)
		window = moviemanager.ui.main_window.MainWindow(settings, directory="")
		qtbot.addWidget(window)
		# wait for startup scan to complete
		qtbot.waitUntil(
			lambda: window._movie_panel._table_model.rowCount() == 2,
			timeout=5000,
		)
		assert window._movie_panel._table_model.rowCount() == 2
		assert question_called["called"] is False


#============================================
class TestChooserDialogBatchMode:
	"""Test MovieChooserDialog batch mode detection."""

	def test_chooser_dialog_batch_mode(self, qtbot, tmp_path):
		"""Dialog with movie_list should activate batch mode."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		assert len(movies) == 2
		# mock search to avoid network calls
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movies[0], api, None,
				movie_list=movies,
			)
			qtbot.addWidget(dialog)
			# verify batch mode is active
			assert dialog._batch_mode is True
			# verify Stop Batch button exists
			assert hasattr(dialog, "_abort_btn")
			assert dialog._abort_btn.text() == "Stop Batch"
			# verify progress bar exists
			assert hasattr(dialog, "_progress_bar")
			# verify Accept Match button text
			assert dialog._ok_btn.text() == "Accept Match"

	def test_chooser_dialog_single_mode(self, qtbot, tmp_path):
		"""Dialog without movie_list should be in single mode."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# mock search to avoid network calls
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movies[0], api, None,
			)
			qtbot.addWidget(dialog)
			# verify single mode
			assert dialog._batch_mode is False
			# verify no Stop Batch button in single mode
			assert not hasattr(dialog, "_abort_btn")
			# verify Accept Match button text
			assert dialog._ok_btn.text() == "Accept Match"


#============================================
def _make_scraped_movie(path: str) -> moviemanager.core.models.movie.Movie:
	"""Create a Movie instance with scraped metadata for testing.

	Args:
		path: Directory path for the movie.

	Returns:
		Movie with populated metadata and scraped=True.
	"""
	movie = moviemanager.core.models.movie.Movie(
		title="The Dark Knight",
		year="2008",
		imdb_id="tt0468569",
		tmdb_id=155,
		director="Christopher Nolan",
		certification="PG-13",
		rating=9.0,
		runtime=152,
		genres=["Action", "Crime", "Drama"],
		plot="Batman raises the stakes in his war on crime.",
		path=path,
		scraped=True,
	)
	return movie


#============================================
class TestChooserDialogPrematchMode:
	"""Test MovieChooserDialog prematch view for already-matched movies."""

	def test_prematch_view_shown_for_scraped_movie(self, qtbot, tmp_path):
		"""Scraped movie should show prematch view with card layout."""
		dk_dir = str(tmp_path / "The.Dark.Knight.2008")
		os.makedirs(dk_dir, exist_ok=True)
		movie = _make_scraped_movie(dk_dir)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
			movie, api, None,
		)
		qtbot.addWidget(dialog)
		# verify prematch mode is active
		assert dialog._in_prematch_mode is True
		# use isHidden() since dialog is not shown (isVisible requires parent)
		assert not dialog._prematch_widget.isHidden()
		# verify metadata fields are populated
		assert dialog._prematch_title.text() == "The Dark Knight"
		assert dialog._prematch_year_label.text() == "2008"
		assert dialog._prematch_rating_label.text() == "9.0/10"
		assert dialog._prematch_director_label.text() == "Christopher Nolan"
		assert dialog._prematch_cert_label.text() == "PG-13"
		assert "Action" in dialog._prematch_genres_label.text()
		assert dialog._prematch_runtime_label.text() == "152 min"
		assert "tt0468569" in dialog._prematch_ids_label.text()
		# verify Keep Match button text
		assert dialog._ok_btn.text() == "Keep Match"

	def test_prematch_keep_match_single_mode(self, qtbot, tmp_path):
		"""Keep Match in single mode should accept the dialog."""
		dk_dir = str(tmp_path / "The.Dark.Knight.2008")
		os.makedirs(dk_dir, exist_ok=True)
		movie = _make_scraped_movie(dk_dir)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
			movie, api, None,
		)
		qtbot.addWidget(dialog)
		# verify prematch mode
		assert dialog._in_prematch_mode is True
		# click Keep Match (the OK button in prematch mode)
		with unittest.mock.patch.object(dialog, "accept") as mock_accept:
			dialog._on_ok_clicked()
			mock_accept.assert_called_once()

	def test_rematch_switches_to_search(self, qtbot, tmp_path):
		"""Find Different Match should switch to search UI."""
		dk_dir = str(tmp_path / "The.Dark.Knight.2008")
		os.makedirs(dk_dir, exist_ok=True)
		movie = _make_scraped_movie(dk_dir)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		# mock search to avoid network calls
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movie, api, None,
			)
			qtbot.addWidget(dialog)
			# click Find Different Match
			dialog._switch_to_search_mode()
			# verify search mode is active
			assert dialog._in_prematch_mode is False
			assert dialog._had_prematch is True
			# verify search UI is shown and prematch is hidden
			assert not dialog._search_widget.isHidden()
			assert dialog._prematch_widget.isHidden()
			# verify Keep Original Match button is shown
			assert not dialog._keep_original_btn.isHidden()
			assert dialog._ok_btn.text() == "Accept Match"

	def test_return_to_prematch(self, qtbot, tmp_path):
		"""Keep Original Match should restore prematch view."""
		dk_dir = str(tmp_path / "The.Dark.Knight.2008")
		os.makedirs(dk_dir, exist_ok=True)
		movie = _make_scraped_movie(dk_dir)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		# mock search to avoid network calls
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movie, api, None,
			)
			qtbot.addWidget(dialog)
			# switch to search mode first
			dialog._switch_to_search_mode()
			assert dialog._in_prematch_mode is False
			# click Keep Original Match
			dialog._return_to_prematch()
			# verify prematch mode is restored
			assert dialog._in_prematch_mode is True
			assert dialog._had_prematch is False
			assert not dialog._prematch_widget.isHidden()
			assert dialog._keep_original_btn.isHidden()
			assert dialog._ok_btn.text() == "Keep Match"


#============================================
class TestChooserDialogBatchBugFixes:
	"""Test batch mode bug fixes for pending count and progress bar."""

	def test_batch_results_pending_not_counted(self, qtbot, tmp_path):
		"""Pending scrapes should not count as matched."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# mock search to avoid network calls
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movies[0], api, None,
				movie_list=movies,
			)
			qtbot.addWidget(dialog)
			# simulate pending scrape result
			dialog._batch_results["fake/path"] = "pending"
			# reload to trigger count update
			dialog._load_movie(movies[0])
			# verify pending is not counted as matched
			assert "0 matched" in dialog._match_count_label.text()

	def test_progress_bar_starts_at_zero(self, qtbot, tmp_path):
		"""Progress bar should start at 0 for the first movie."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# mock search to avoid network calls
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
				movies[0], api, None,
				movie_list=movies,
			)
			qtbot.addWidget(dialog)
			# progress bar should be 0 (no movies completed yet)
			assert dialog._progress_bar.value() == 0
