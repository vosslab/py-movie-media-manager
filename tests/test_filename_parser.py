"""Tests for moviemanager.core.utils filename parsing functions."""

import pytest

import moviemanager.core.utils


# parametrized test cases: (filename, expected_title, expected_year)
TITLE_YEAR_CASES = [
	("The.Dark.Knight.2008.BluRay.x264.mkv", "The Dark Knight", "2008"),
	("Inception (2010) 1080p.mkv", "Inception", "2010"),
	("The Matrix 1999 DVDRip XviD.avi", "The Matrix", "1999"),
	("Pulp.Fiction.1994.REMASTERED.1080p.BluRay.x264.mkv", "Pulp Fiction", "1994"),
	("Movie Title.mkv", "Movie Title", ""),
	("2001.A.Space.Odyssey.1968.720p.mkv", "2001 A Space Odyssey", "1968"),
	("Se7en.1995.BluRay.mkv", "Se7en", "1995"),
	("Wall-E.2008.1080p.mkv", "Wall-E", "2008"),
	("12.Angry.Men.1957.DVDRip.mkv", "12 Angry Men", "1957"),
	("The.Godfather.Part.II.1974.BluRay.x264.mkv", "The Godfather Part II", "1974"),
]


#============================================
@pytest.mark.parametrize(
	"filename, expected_title, expected_year",
	TITLE_YEAR_CASES,
)
def test_parse_title_year(
	filename: str,
	expected_title: str,
	expected_year: str,
) -> None:
	"""Verify title and year extraction from media filenames."""
	title, year = moviemanager.core.utils.parse_title_year(filename)
	assert title == expected_title
	assert year == expected_year


# test cases for is_video_file: (path, expected_result)
VIDEO_FILE_CASES = [
	("movie.mkv", True),
	("movie.avi", True),
	("movie.mp4", True),
	("movie.MKV", True),
	("movie.srt", False),
	("movie.txt", False),
	("movie.jpg", False),
	("/path/to/video.webm", True),
	("noextension", False),
]


#============================================
@pytest.mark.parametrize("path, expected", VIDEO_FILE_CASES)
def test_is_video_file(path: str, expected: bool) -> None:
	"""Verify video file extension detection."""
	result = moviemanager.core.utils.is_video_file(path)
	assert result == expected


# test cases for clean_filename: (input_name, expected_output)
CLEAN_FILENAME_CASES = [
	("normal_filename", "normal_filename"),
	('bad:file/name\\test', "badfilenametest"),
	("multiple   spaces", "multiple spaces"),
	("  leading_trailing  ", "leading_trailing"),
	("...dotted...", "dotted"),
	('quotes"and<angles>', "quotesandangles"),
	("pipe|star*question?", "pipestarquestion"),
]


#============================================
@pytest.mark.parametrize("input_name, expected", CLEAN_FILENAME_CASES)
def test_clean_filename(input_name: str, expected: str) -> None:
	"""Verify unsafe characters are removed from filenames."""
	result = moviemanager.core.utils.clean_filename(input_name)
	assert result == expected
