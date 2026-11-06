"""Integration tests for metadata application and the scan/scrape/rename pipeline."""

# Standard Library
import os
import unittest.mock

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.models.movie
import moviemanager.core.settings
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types


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
def _create_movie_dirs(tmp_path: object) -> str:
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
class TestScrapeMovies:
	"""Protect metadata application and NFO creation through the public API."""

	def test_scrape_dark_knight(self, tmp_path: object) -> None:
		"""Scrape Dark Knight should populate metadata and write NFO."""
		root = _create_movie_dirs(tmp_path)
		settings = moviemanager.core.settings.Settings()
		api = moviemanager.api.movie_api.MovieAPI(settings)
		movies = api.scan_directory(root)
		# find the Dark Knight movie
		dk = [m for m in movies if "Dark Knight" in m.title][0]
		# mock the scraper methods and transport creation
		with unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"search", side_effect=_mock_search,
		), unittest.mock.patch.object(
			moviemanager.scraper.imdb_scraper.ImdbScraper,
			"get_metadata", side_effect=_mock_get_metadata,
		), unittest.mock.patch(
			"moviemanager.scraper.imdb_scraper.time.sleep",
		), unittest.mock.patch.object(
			moviemanager.api.movie_api.MovieAPI,
			"_ensure_imdb_transport",
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


#============================================
class TestFullPipeline:
	"""End-to-end: scan, scrape, rename, verify."""

	def test_full_pipeline(self, tmp_path: object) -> None:
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
		), unittest.mock.patch.object(
			moviemanager.api.movie_api.MovieAPI,
			"_ensure_imdb_transport",
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
