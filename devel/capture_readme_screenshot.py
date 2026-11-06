#!/usr/bin/env python3
"""Open a sample GUI view for capture; match/edit views fetch live IMDb artwork."""

# Standard Library
import pathlib
import argparse
import sys
import tempfile
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.core.settings
import moviemanager.core.movie.rename_service
import moviemanager.ui.dialogs.movie_chooser
import moviemanager.ui.dialogs.movie_editor
import moviemanager.ui.dialogs.rename_preview
import moviemanager.ui.main_window
import moviemanager.ui.theme
import moviemanager.ui.workers


SAMPLE_MOVIES = [
	("Arrival", "2016", "tt2543164", "Denis Villeneuve", "PG-13", "8.0", "116", "Science Fiction"),
	("Blade Runner 2049", "2017", "tt1856101", "Denis Villeneuve", "R", "8.0", "164", "Drama, Science Fiction, Thriller"),
	("The Iron Giant", "1999", "tt0129167", "Brad Bird", "PG", "8.1", "86", "Animation, Family, Science Fiction"),
	("Mad Max Fury Road", "2015", "tt1392190", "George Miller", "R", "8.1", "120", "Action, Adventure, Science Fiction"),
	("Moon", "2009", "tt1182345", "Duncan Jones", "R", "7.8", "97", "Drama, Mystery, Science Fiction"),
	("Spirited Away", "2001", "tt0245429", "Hayao Miyazaki", "PG", "8.6", "125", "Animation, Adventure, Family"),
]

UNMATCHED_MOVIES = [
	("After Yang", "2021"),
	("Columbus", "2017"),
	("The Farewell", "2019"),
	("Past Lives", "2023"),
]


#============================================
def _write_nfo(movie_dir: pathlib.Path, movie: tuple) -> None:
	"""Write local Kodi metadata for one matched demonstration movie."""
	title, year, imdb_id, director, certification, rating, runtime, genres = movie
	genre_lines = []
	for genre in genres.split(", "):
		genre_lines.append(f"  <genre>{genre}</genre>")
	lines = [
		"<?xml version='1.0' encoding='UTF-8'?>",
		"<movie>",
		f"  <title>{title}</title>",
		f"  <year>{year}</year>",
		f"  <id>{imdb_id}</id>",
		"  <plot>A linguist works with visiting aliens to communicate across time.</plot>",
		f"  <runtime>{runtime}</runtime>",
		f"  <mpaa>{certification}</mpaa>",
		f"  <rating>{rating}</rating>",
		f"  <director>{director}</director>",
	]
	lines.extend(genre_lines)
	lines.extend([
		"  <parental_guide><advisory category='Violence &amp; Gore'>Mild</advisory></parental_guide>",
		"</movie>",
	])
	nfo_text = "\n".join(lines) + "\n"
	video_name = f"{title.replace(' ', '.')}.{year}.mkv"
	(movie_dir / video_name).touch()
	(movie_dir / (video_name[:-4] + ".nfo")).write_text(nfo_text)


#============================================
def _create_sample_library(temp_dir: pathlib.Path) -> pathlib.Path:
	"""Create a ten-movie local library with matched and unmatched rows."""
	library_dir = temp_dir / "Sample Library" / "Media" / "Movies"
	for movie in SAMPLE_MOVIES:
		title = movie[0]
		year = movie[1]
		movie_dir = library_dir / f"{title}-{year}"
		movie_dir.mkdir(parents=True)
		_write_nfo(movie_dir, movie)
	for title, year in UNMATCHED_MOVIES:
		movie_dir = library_dir / f"{title}-{year}"
		movie_dir.mkdir(parents=True)
		video_name = f"{title.replace(' ', '.')}.{year}.mkv"
		(movie_dir / video_name).touch()
	return library_dir


#============================================
def _select_arrival(window: object) -> None:
	"""Set the populated Arrival row as the visible detail-panel example."""
	panel = window._movie_panel
	model = panel._table_model
	for row in range(model.rowCount()):
		movie = model.get_movie(row)
		if movie.title == "Arrival":
			index = model.index(row, 1)
			panel._table_view.setCurrentIndex(index)
			panel._table_view.selectRow(row)
			panel._table_view.scrollTo(index)
			return
	raise RuntimeError("Arrival was not available in the scanned sample library.")


#============================================
def _prepare_capture(window: object, view: str) -> None:
	"""Show one real workflow against the completed sample scan."""
	_select_arrival(window)
	window.resize(1440, 900)
	window.setWindowTitle("Movie Media Manager - Sample Library")
	window.show()
	movies = window._api.get_movies()
	arrival = next(movie for movie in movies if movie.title == "Arrival")
	if view == "main":
		print("README_DEMO_READY", flush=True)
		return
	if view == "rename":
		pairs = []
		for movie in movies:
			if movie.scraped:
				pairs.extend(moviemanager.core.movie.rename_service.rename_movie(
					movie, path_template="{title} ({year})",
					file_template="{title} ({year})", dry_run=True,
				))
		dialog = moviemanager.ui.dialogs.rename_preview.RenamePreviewDialog(pairs, window)
	elif view == "edit":
		results = window._api.search_movie(arrival.title, arrival.year)
		result = next(result for result in results if result.imdb_id == arrival.imdb_id)
		poster = moviemanager.ui.workers.download_image_bytes(result.poster_url)
		(pathlib.Path(arrival.path) / "poster.jpg").write_bytes(poster)
		dialog = moviemanager.ui.dialogs.movie_editor.MovieEditorDialog(arrival, window)
	else:
		moon = next(movie for movie in movies if movie.title == "Moon")
		dialog = moviemanager.ui.dialogs.movie_chooser.MovieChooserDialog(
			moon, window._api, window, movie_list=[moon, arrival],
		)
		dialog._switch_to_search_mode()
	size = (850, 900) if view == "edit" else (1100, 700)
	dialog.resize(*size)
	dialog.show()
	window._capture_dialog = dialog
	if view != "match":
		print("README_DEMO_READY", flush=True)
		return
	deadline = time.monotonic() + 45
	timer = PySide6.QtCore.QTimer(dialog)

	def wait_for_search() -> None:
		"""Wait for real search results and their selected poster to finish."""
		pane = dialog._search_pane
		if pane._results_table.rowCount() and pane._preview._poster_worker is None:
			timer.stop()
			print("README_DEMO_READY", flush=True)
		elif time.monotonic() >= deadline:
			timer.stop()
			print("README_DEMO_FAILED: live search did not settle", flush=True)
			PySide6.QtWidgets.QApplication.exit(1)

	timer.timeout.connect(wait_for_search)
	timer.start(250)


#============================================
def main() -> None:
	"""Run the real GUI against temporary local data until closed."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--view", choices=["main", "match", "rename", "edit"], default="main")
	args = parser.parse_args()
	app = PySide6.QtWidgets.QApplication(sys.argv[:1])
	app.setApplicationName("Movie Media Manager")
	settings = moviemanager.core.settings.Settings(theme="dark")
	moviemanager.ui.theme.apply_theme(app, settings.theme)
	with tempfile.TemporaryDirectory(prefix="movie_media_manager_readme_") as temp_name:
		temp_dir = pathlib.Path(temp_name)
		library_dir = _create_sample_library(temp_dir)
		# Keep temporary window and table preferences out of the user profile.
		settings_api = PySide6.QtCore.QSettings
		settings_api.setDefaultFormat(settings_api.Format.IniFormat)
		settings_api.setPath(
			settings_api.Format.IniFormat,
			settings_api.Scope.UserScope, temp_name,
		)
		# Keep the application's normal settings write in the same temporary tree.
		moviemanager.core.settings.DEFAULT_CONFIG_PATH = str(
			temp_dir / "movie_organizer.yaml"
		)
		window = moviemanager.ui.main_window.MainWindow(
			settings, directory=str(library_dir),
		)
		# Search results from a capture must not enter the user's persistent cache.
		window._api._cache._cache_dir = str(temp_dir / "api_cache")
		window._scan_ctrl.probe_completed.connect(
			lambda: _prepare_capture(window, args.view)
		)
		window._scan_ctrl.probe_error.connect(
			lambda _error: _prepare_capture(window, args.view)
		)
		window.show()
		exit_code = app.exec()
		window.close()
		raise SystemExit(exit_code)


#============================================
if __name__ == "__main__":
	main()
