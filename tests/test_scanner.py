"""Tests for the movie directory scanner."""

# local repo modules
import moviemanager.core.movie.scan_service
import moviemanager.core.models.movie
import moviemanager.core.nfo.writer


#============================================
def _touch(path: str) -> None:
	"""Create an empty file at the given path.

	Args:
		path: Full file path to create.
	"""
	with open(path, "w"):
		pass


#============================================
def test_scan_single_movie(tmp_path):
	"""Scan a directory with one mkv file and verify title/year parsing."""
	movie_dir = tmp_path / "The Matrix (1999)"
	movie_dir.mkdir()
	_touch(str(movie_dir / "The.Matrix.1999.BluRay.mkv"))

	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert len(results) == 1
	movie = results[0]
	assert movie.title == "The Matrix"
	assert movie.year == "1999"
	assert movie.multi_movie_dir is False
	# verify the media file was created
	assert len(movie.media_files) == 1
	assert movie.media_files[0].filename == "The.Matrix.1999.BluRay.mkv"


#============================================
def test_scan_with_nfo(tmp_path):
	"""Scan a directory with mkv + nfo and verify NFO metadata is loaded."""
	movie_dir = tmp_path / "Inception"
	movie_dir.mkdir()
	_touch(str(movie_dir / "Inception.mkv"))

	# write an NFO file using the writer
	nfo_path = str(movie_dir / "Inception.nfo")
	test_movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
		director="Christopher Nolan",
	)
	moviemanager.core.nfo.writer.write_nfo(test_movie, nfo_path)

	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert len(results) == 1
	movie = results[0]
	assert movie.title == "Inception"
	assert movie.year == "2010"
	assert movie.director == "Christopher Nolan"
	assert movie.nfo_path == nfo_path


#============================================
def test_scan_multi_movie_dir(tmp_path):
	"""Scan a directory with multiple mkv files and verify multi_movie_dir."""
	movie_dir = tmp_path / "Collection"
	movie_dir.mkdir()
	_touch(str(movie_dir / "MovieA.2001.mkv"))
	_touch(str(movie_dir / "MovieB.2002.mkv"))

	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert len(results) == 2
	for movie in results:
		assert movie.multi_movie_dir is True


#============================================
def test_scan_skips_hidden_dirs(tmp_path):
	"""Hidden directories starting with dot should be skipped."""
	hidden_dir = tmp_path / ".hidden"
	hidden_dir.mkdir()
	_touch(str(hidden_dir / "secret.mkv"))

	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert len(results) == 0


#============================================
def test_scan_skips_recycle_bin(tmp_path):
	"""$RECYCLE.BIN directory should be skipped."""
	recycle_dir = tmp_path / "$RECYCLE.BIN"
	recycle_dir.mkdir()
	_touch(str(recycle_dir / "deleted.mkv"))

	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert len(results) == 0


#============================================
def test_scan_nested_dirs(tmp_path):
	"""Scan nested structure with movies at different levels."""
	# top-level movie
	top_dir = tmp_path / "TopMovie"
	top_dir.mkdir()
	_touch(str(top_dir / "Top.Movie.2020.mkv"))

	# nested movie
	nested_dir = tmp_path / "Genre" / "SubMovie"
	nested_dir.mkdir(parents=True)
	_touch(str(nested_dir / "Sub.Movie.2021.mkv"))

	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert len(results) == 2
	titles = {m.title for m in results}
	assert "Top Movie" in titles
	assert "Sub Movie" in titles


#============================================
def test_scan_empty_dir(tmp_path):
	"""Empty directory returns an empty list."""
	results = moviemanager.core.movie.scan_service.scan_directory(str(tmp_path))

	assert results == []


#============================================
def test_detect_artwork(tmp_path):
	"""Detect poster.jpg and fanart.jpg in a directory."""
	_touch(str(tmp_path / "poster.jpg"))
	_touch(str(tmp_path / "fanart.jpg"))

	artwork = moviemanager.core.movie.scan_service.detect_artwork_files(
		str(tmp_path)
	)

	assert "poster" in artwork
	assert artwork["poster"] == str(tmp_path / "poster.jpg")
	assert "fanart" in artwork
	assert artwork["fanart"] == str(tmp_path / "fanart.jpg")
