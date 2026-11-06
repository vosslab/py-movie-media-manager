"""Run representative GUI workflows outside pytest's fast lane."""

# Standard Library
import os
import pathlib
import sys
import tempfile
import time
import unittest.mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.models.movie
import moviemanager.core.settings
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types
import moviemanager.ui.dialogs.movie_chooser
import moviemanager.ui.main_window
import moviemanager.ui.task_api


#============================================
def create_movie_dirs(temp_dir: pathlib.Path) -> str:
	"""Create two minimal movie folders and return their common directory."""
	movies_dir = temp_dir / "movies"
	for name in ("The.Dark.Knight.2008.BluRay", "The.Godfather.1972.Remastered"):
		movie_dir = movies_dir / name
		movie_dir.mkdir(parents=True)
		(movie_dir / f"{name}.mkv").touch()
	return str(movies_dir)


#============================================
def mock_search(title: str, year: str = "") -> list:
	"""Return the fixed local search result used by chooser workflows."""
	result = moviemanager.scraper.types.SearchResult(
		title=title,
		year=year,
		imdb_id="tt0468569",
	)
	return [result]


#============================================
def create_scraped_movie(path: str) -> moviemanager.core.models.movie.Movie:
	"""Create a matched movie with metadata for prematch workflows."""
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
def wait_for_rows(
	app: PySide6.QtWidgets.QApplication,
	window: moviemanager.ui.main_window.MainWindow,
) -> None:
	"""Process events until the initial scan has populated two table rows."""
	deadline = time.monotonic() + 5
	while window._movie_panel._table_model.rowCount() != 2:
		if time.monotonic() >= deadline:
			raise RuntimeError("Main window scan did not complete within five seconds.")
		app.processEvents()
		time.sleep(0.01)


#============================================
def verify_last_directory(
	app: PySide6.QtWidgets.QApplication,
	movies_dir: str,
) -> None:
	"""Confirm startup scans the saved directory without prompting."""
	settings = moviemanager.core.settings.Settings(last_directory=movies_dir)
	question_called = False

	def question_stub(*args: object, **kwargs: object) -> object:
		"""Track prompts while allowing closeEvent to finish."""
		nonlocal question_called
		question_called = True
		return PySide6.QtWidgets.QMessageBox.StandardButton.Yes

	with unittest.mock.patch.object(
		moviemanager.core.settings, "save_settings",
	), unittest.mock.patch.object(
		PySide6.QtWidgets.QMessageBox, "question", side_effect=question_stub,
	):
		window = moviemanager.ui.main_window.MainWindow(settings, directory="")
		wait_for_rows(app, window)
		if question_called:
			raise RuntimeError("Opening the saved directory prompted the user.")
		window.close()


#============================================
def verify_chooser_modes(
	movies: list[moviemanager.core.models.movie.Movie],
	api: moviemanager.api.movie_api.MovieAPI,
) -> None:
	"""Confirm single, batch, pending, and prematch chooser contracts."""
	task_api = moviemanager.ui.task_api.TaskAPI()
	batch_dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
		movies[0], api, movie_list=movies, task_api=task_api,
	)
	if not batch_dialog._nav.batch_mode:
		raise RuntimeError("Chooser did not enable batch mode.")
	if batch_dialog._abort_btn.text() != "Stop Batch":
		raise RuntimeError("Batch chooser did not show Stop Batch.")
	if batch_dialog._ok_btn.text() != "Accept Match":
		raise RuntimeError("Batch chooser did not show Accept Match.")
	if batch_dialog._progress_bar.value() != 0:
		raise RuntimeError("Batch chooser progress did not start at zero.")
	batch_dialog._nav.mark_result("fake/path", "pending")
	batch_dialog._load_movie(movies[0])
	if "0 matched" not in batch_dialog._match_count_label.text():
		raise RuntimeError("Pending batch result counted as a matched movie.")
	batch_dialog.done(0)

	single_dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
		movies[0], api, task_api=task_api,
	)
	if single_dialog._nav.batch_mode or hasattr(single_dialog, "_abort_btn"):
		raise RuntimeError("Single chooser exposed batch controls.")
	if single_dialog._ok_btn.text() != "Accept Match":
		raise RuntimeError("Single chooser did not show Accept Match.")
	single_dialog.done(0)


#============================================
def verify_prematch(
	api: moviemanager.api.movie_api.MovieAPI,
	movies_dir: str,
) -> None:
	"""Confirm displayed metadata and actions for an existing match."""
	task_api = moviemanager.ui.task_api.TaskAPI()
	movie = create_scraped_movie(movies_dir)
	dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
		movie, api, task_api=task_api,
	)
	preview = dialog._prematch_widget
	if not dialog._in_prematch_mode or preview.isHidden():
		raise RuntimeError("Matched movie did not open in prematch mode.")
	if preview._title_label.text() != "The Dark Knight":
		raise RuntimeError("Prematch title was not displayed.")
	if preview._year_label.text() != "2008" or preview._rating_label.text() != "9.0/10":
		raise RuntimeError("Prematch year or rating was not displayed.")
	if preview._director_label.text() != "Christopher Nolan":
		raise RuntimeError("Prematch director was not displayed.")
	if preview._cert_label.text() != "PG-13" or preview._runtime_label.text() != "152 min":
		raise RuntimeError("Prematch certification or runtime was not displayed.")
	if "Action" not in preview._genres_label.text() or "tt0468569" not in preview._ids_label.text():
		raise RuntimeError("Prematch genres or IDs were not displayed.")
	if dialog._ok_btn.text() != "Keep Match":
		raise RuntimeError("Prematch did not show Keep Match.")
	with unittest.mock.patch.object(dialog, "accept") as accept:
		dialog._on_ok_clicked()
		if accept.call_count != 1:
			raise RuntimeError("Keep Match did not accept the chooser.")
	dialog._switch_to_search_mode()
	if dialog._in_prematch_mode or not dialog._had_prematch:
		raise RuntimeError("Chooser did not switch from prematch to search mode.")
	if dialog._search_pane.isHidden() or not preview.isHidden():
		raise RuntimeError("Search and prematch visibility did not switch.")
	if dialog._keep_original_btn.isHidden() or dialog._ok_btn.text() != "Accept Match":
		raise RuntimeError("Search mode did not offer the original match.")
	dialog._return_to_prematch()
	if not dialog._in_prematch_mode or dialog._had_prematch:
		raise RuntimeError("Chooser did not restore prematch state.")
	if preview.isHidden() or not dialog._keep_original_btn.isHidden():
		raise RuntimeError("Restored prematch controls were incorrect.")
	dialog.done(0)


#============================================
def main() -> None:
	"""Exercise main-window and chooser workflows offscreen."""
	app = PySide6.QtWidgets.QApplication.instance()
	if app is None:
		app = PySide6.QtWidgets.QApplication([])
	with tempfile.TemporaryDirectory() as temp_dir:
		movies_dir = create_movie_dirs(pathlib.Path(temp_dir))
		settings = moviemanager.core.settings.Settings()
		with unittest.mock.patch.object(
			moviemanager.core.settings, "save_settings",
		), unittest.mock.patch.object(
			PySide6.QtWidgets.QMessageBox, "question",
			return_value=PySide6.QtWidgets.QMessageBox.StandardButton.Yes,
		):
			window = moviemanager.ui.main_window.MainWindow(settings, directory=movies_dir)
			wait_for_rows(app, window)
			if window._movie_panel._table_model.rowCount() != 2:
				raise RuntimeError("Main window did not display both scanned movies.")
			window.close()
		verify_last_directory(app, movies_dir)
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(movies_dir)
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=mock_search,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		):
			verify_chooser_modes(movies, api)
			verify_prematch(api, movies_dir)
		app.processEvents()


#============================================
if __name__ == "__main__":
	main()
