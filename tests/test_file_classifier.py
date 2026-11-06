"""Tests for moviemanager.core.file.classifier file type detection."""

import pytest

import moviemanager.core.constants
import moviemanager.core.file.classifier


# parametrized test cases for classify_file
CLASSIFY_CASES = [
	("movie.mkv", moviemanager.core.constants.MediaFileType.VIDEO),
	("movie.avi", moviemanager.core.constants.MediaFileType.VIDEO),
	("movie.mp4", moviemanager.core.constants.MediaFileType.VIDEO),
	("trailer.mp4", moviemanager.core.constants.MediaFileType.TRAILER),
	("Movie-trailer.mkv", moviemanager.core.constants.MediaFileType.TRAILER),
	("sample.avi", moviemanager.core.constants.MediaFileType.SAMPLE),
	("movie.srt", moviemanager.core.constants.MediaFileType.SUBTITLE),
	("movie.sub", moviemanager.core.constants.MediaFileType.SUBTITLE),
	("movie.ass", moviemanager.core.constants.MediaFileType.SUBTITLE),
	("movie.nfo", moviemanager.core.constants.MediaFileType.NFO),
	("movie.mp3", moviemanager.core.constants.MediaFileType.AUDIO),
	("poster.jpg", moviemanager.core.constants.MediaFileType.POSTER),
	("fanart.jpg", moviemanager.core.constants.MediaFileType.FANART),
	("banner.png", moviemanager.core.constants.MediaFileType.BANNER),
	("clearart.png", moviemanager.core.constants.MediaFileType.CLEARART),
	("logo.png", moviemanager.core.constants.MediaFileType.LOGO),
	("disc.png", moviemanager.core.constants.MediaFileType.DISCART),
	("thumb.jpg", moviemanager.core.constants.MediaFileType.THUMB),
	("random.jpg", moviemanager.core.constants.MediaFileType.GRAPHIC),
	("readme.txt", moviemanager.core.constants.MediaFileType.TEXT),
	("unknown.xyz", moviemanager.core.constants.MediaFileType.UNKNOWN),
]


#============================================
@pytest.mark.parametrize("filename, expected", CLASSIFY_CASES)
def test_classify_file(filename: str, expected: object) -> None:
	"""Verify classify_file returns the correct MediaFileType."""
	result = moviemanager.core.file.classifier.classify_file(filename)
	assert result == expected
