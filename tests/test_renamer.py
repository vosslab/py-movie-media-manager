"""Tests for movie file renaming and template expansion."""

# Standard Library
import os

# local repo modules
import moviemanager.core.constants
import moviemanager.core.models.media_file
import moviemanager.core.models.movie
import moviemanager.core.movie.renamer


#============================================
def _make_movie(tmp_path: str, title: str = "Inception", year: str = "2010",
		video_name: str = "inception.mkv", nfo_name: str = "inception.nfo",
		artwork: list = None) -> moviemanager.core.models.movie.Movie:
	"""Create a Movie with real files in a temporary directory.

	Args:
		tmp_path: base temporary directory path.
		title: movie title.
		year: release year string.
		video_name: filename for the video file.
		nfo_name: filename for the NFO file.
		artwork: optional list of artwork filenames to create.

	Returns:
		Movie dataclass with paths pointing to created files.
	"""
	# create the movie subdirectory
	movie_dir = os.path.join(str(tmp_path), "inception_old")
	os.makedirs(movie_dir, exist_ok=True)

	# create video file
	video_path = os.path.join(movie_dir, video_name)
	with open(video_path, "w") as fh:
		fh.write("fake video data")

	# create NFO file
	nfo_path = os.path.join(movie_dir, nfo_name)
	with open(nfo_path, "w") as fh:
		fh.write("<movie><title>Inception</title></movie>")

	# create artwork files if requested
	if artwork:
		for art_name in artwork:
			art_path = os.path.join(movie_dir, art_name)
			with open(art_path, "w") as fh:
				fh.write("fake image data")

	# build media file for video
	video_mf = moviemanager.core.models.media_file.MediaFile(
		path=video_path,
		filename=video_name,
		file_type=moviemanager.core.constants.MediaFileType.VIDEO,
	)

	# build movie object
	movie = moviemanager.core.models.movie.Movie(
		title=title,
		year=year,
		path=movie_dir,
		nfo_path=nfo_path,
		media_files=[video_mf],
	)
	return movie


#============================================
def test_expand_template_basic():
	"""Template with title and year expands correctly."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
	)
	result = moviemanager.core.movie.renamer.expand_template(
		"{title} ({year})", movie
	)
	assert result == "Inception (2010)"


#============================================
def test_expand_template_missing_year():
	"""Template with missing year removes empty parentheses."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="",
	)
	result = moviemanager.core.movie.renamer.expand_template(
		"{title} ({year})", movie
	)
	assert result == "Inception"


#============================================
def test_expand_template_first_letter():
	"""Template with first_letter produces correct prefix."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
	)
	# note: clean_filename strips slashes, so use a dash separator
	result = moviemanager.core.movie.renamer.expand_template(
		"{first_letter} - {title}", movie
	)
	assert result == "I - Inception"


#============================================
def test_expand_template_special_chars():
	"""Title with colons and slashes gets cleaned."""
	movie = moviemanager.core.models.movie.Movie(
		title='Mission: Impossible / Rogue Nation',
		year="2015",
	)
	result = moviemanager.core.movie.renamer.expand_template(
		"{title} ({year})", movie
	)
	# colons and slashes should be removed by clean_filename
	assert ":" not in result
	assert "/" not in result
	assert "2015" in result
	assert "Mission" in result


#============================================
def test_rename_dry_run(tmp_path):
	"""Dry run returns rename pairs without moving files."""
	movie = _make_movie(tmp_path)
	pairs = moviemanager.core.movie.renamer.rename_movie(
		movie,
		path_template="{title} ({year})",
		file_template="{title} ({year})",
		dry_run=True,
	)
	# should have pairs for video and NFO
	assert len(pairs) >= 2
	# source files should still exist (not moved)
	for source, _dest in pairs:
		assert os.path.isfile(source)


#============================================
def test_rename_live(tmp_path):
	"""Live rename moves video, NFO, and artwork files."""
	movie = _make_movie(tmp_path, artwork=["poster.jpg"])
	# record original paths
	original_video = movie.media_files[0].path
	original_nfo = movie.nfo_path

	pairs = moviemanager.core.movie.renamer.rename_movie(
		movie,
		path_template="{title} ({year})",
		file_template="{title} ({year})",
		dry_run=False,
	)
	# should have pairs for video, NFO, and poster
	assert len(pairs) == 3
	# source files should be gone
	assert not os.path.isfile(original_video)
	assert not os.path.isfile(original_nfo)
	# destination files should exist
	for _source, dest in pairs:
		assert os.path.isfile(dest)
	# movie object paths should be updated
	assert "Inception (2010)" in movie.path
	assert movie.nfo_path.endswith(".nfo")


#============================================
def test_rename_with_artwork(tmp_path):
	"""Artwork files move along with video to the new directory."""
	artwork_names = ["poster.jpg", "fanart.jpg"]
	movie = _make_movie(tmp_path, artwork=artwork_names)

	pairs = moviemanager.core.movie.renamer.rename_movie(
		movie,
		path_template="{title} ({year})",
		file_template="{title} ({year})",
		dry_run=False,
	)
	# find artwork pairs by checking filenames
	art_pairs = [
		(s, d) for s, d in pairs
		if os.path.basename(d) in artwork_names
	]
	assert len(art_pairs) == 2
	# verify artwork files exist at destination
	for _source, dest in art_pairs:
		assert os.path.isfile(dest)
		# artwork keeps its original filename
		basename = os.path.basename(dest)
		assert basename in artwork_names
