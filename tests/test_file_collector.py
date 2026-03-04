"""Tests for moviemanager.core.file.collector directory file collection."""

# Standard Library
import os

import moviemanager.core.file.collector


#============================================
def _touch(path: str) -> None:
	"""Create an empty file at the given path.

	Args:
		path: Full file path to create.
	"""
	with open(path, "w"):
		pass


#============================================
def test_collect_artwork_files_with_filenames(tmp_path):
	"""Collect artwork using a filenames list (scanner use case)."""
	filenames = ["poster.jpg", "fanart.jpg", "movie.mkv"]
	artwork = moviemanager.core.file.collector.collect_artwork_files(
		str(tmp_path), filenames=filenames,
	)
	assert "poster" in artwork
	assert "fanart" in artwork
	assert artwork["poster"] == os.path.join(str(tmp_path), "poster.jpg")
	assert artwork["fanart"] == os.path.join(str(tmp_path), "fanart.jpg")


#============================================
def test_collect_artwork_files_from_disk(tmp_path):
	"""Collect artwork by scanning actual files on disk."""
	_touch(str(tmp_path / "poster.jpg"))
	_touch(str(tmp_path / "fanart.jpg"))

	artwork = moviemanager.core.file.collector.collect_artwork_files(
		str(tmp_path),
	)
	assert "poster" in artwork
	assert artwork["poster"] == str(tmp_path / "poster.jpg")
	assert "fanart" in artwork
	assert artwork["fanart"] == str(tmp_path / "fanart.jpg")


#============================================
def test_collect_artwork_files_empty_dir(tmp_path):
	"""Empty directory returns empty dict."""
	artwork = moviemanager.core.file.collector.collect_artwork_files(
		str(tmp_path),
	)
	assert artwork == {}


#============================================
def test_collect_artwork_file_paths_basic(tmp_path):
	"""Collect artwork paths from directory."""
	_touch(str(tmp_path / "poster.jpg"))
	_touch(str(tmp_path / "fanart.jpg"))
	_touch(str(tmp_path / "movie.mkv"))

	paths = moviemanager.core.file.collector.collect_artwork_file_paths(
		str(tmp_path),
	)
	# should find poster.jpg and fanart.jpg but not movie.mkv
	basenames = [os.path.basename(p) for p in paths]
	assert "poster.jpg" in basenames
	assert "fanart.jpg" in basenames
	assert "movie.mkv" not in basenames


#============================================
def test_collect_artwork_file_paths_with_prefix(tmp_path):
	"""Collect prefixed artwork like Movie.Name-poster.jpg."""
	_touch(str(tmp_path / "Movie.Name-poster.jpg"))
	_touch(str(tmp_path / "Movie.Name-fanart.jpg"))
	_touch(str(tmp_path / "poster.jpg"))

	paths = moviemanager.core.file.collector.collect_artwork_file_paths(
		str(tmp_path), video_basename="Movie.Name",
	)
	basenames = [os.path.basename(p) for p in paths]
	assert "poster.jpg" in basenames
	assert "Movie.Name-poster.jpg" in basenames
	assert "Movie.Name-fanart.jpg" in basenames


#============================================
def test_collect_subtitle_files(tmp_path):
	"""Collect subtitle files from a directory."""
	_touch(str(tmp_path / "movie.srt"))
	_touch(str(tmp_path / "movie.en.srt"))
	_touch(str(tmp_path / "movie.mkv"))

	subs = moviemanager.core.file.collector.collect_subtitle_files(
		str(tmp_path),
	)
	basenames = [os.path.basename(p) for p in subs]
	assert "movie.srt" in basenames
	assert "movie.en.srt" in basenames
	assert "movie.mkv" not in basenames


#============================================
def test_collect_subtitle_files_empty(tmp_path):
	"""Empty directory returns empty list."""
	subs = moviemanager.core.file.collector.collect_subtitle_files(
		str(tmp_path),
	)
	assert subs == []


#============================================
def test_collect_trailer_files(tmp_path):
	"""Collect trailer files from a directory."""
	_touch(str(tmp_path / "trailer.mp4"))
	_touch(str(tmp_path / "movie-trailer.mkv"))
	_touch(str(tmp_path / "movie.mkv"))

	trailers = moviemanager.core.file.collector.collect_trailer_files(
		str(tmp_path),
	)
	basenames = [os.path.basename(p) for p in trailers]
	assert "trailer.mp4" in basenames
	assert "movie-trailer.mkv" in basenames
	assert "movie.mkv" not in basenames


#============================================
def test_collect_nfo_files(tmp_path):
	"""Collect NFO files from a directory."""
	_touch(str(tmp_path / "movie.nfo"))
	_touch(str(tmp_path / "movie.mkv"))

	nfos = moviemanager.core.file.collector.collect_nfo_files(
		str(tmp_path),
	)
	basenames = [os.path.basename(p) for p in nfos]
	assert "movie.nfo" in basenames
	assert "movie.mkv" not in basenames


#============================================
def test_collect_all_movie_files(tmp_path):
	"""Collect all movie-related files from a directory."""
	_touch(str(tmp_path / "poster.jpg"))
	_touch(str(tmp_path / "movie.srt"))
	_touch(str(tmp_path / "trailer.mp4"))
	_touch(str(tmp_path / "movie.nfo"))
	_touch(str(tmp_path / "movie.mkv"))

	result = moviemanager.core.file.collector.collect_all_movie_files(
		str(tmp_path),
	)
	assert "poster" in result["artwork"]
	assert len(result["subtitles"]) == 1
	assert len(result["trailers"]) == 1
	assert len(result["nfo_files"]) == 1


#============================================
def test_collect_nonexistent_dir():
	"""Non-existent directory returns empty results."""
	subs = moviemanager.core.file.collector.collect_subtitle_files(
		"/nonexistent/path",
	)
	assert subs == []
	trailers = moviemanager.core.file.collector.collect_trailer_files(
		"/nonexistent/path",
	)
	assert trailers == []
	nfos = moviemanager.core.file.collector.collect_nfo_files(
		"/nonexistent/path",
	)
	assert nfos == []
