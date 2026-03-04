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
def test_classify_file(filename: str, expected) -> None:
	"""Verify classify_file returns the correct MediaFileType."""
	result = moviemanager.core.file.classifier.classify_file(filename)
	assert result == expected


# parametrized test cases for is_video_file
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
@pytest.mark.parametrize("filename, expected", VIDEO_FILE_CASES)
def test_is_video_file(filename: str, expected: bool) -> None:
	"""Verify video file extension detection."""
	result = moviemanager.core.file.classifier.is_video_file(filename)
	assert result == expected


# parametrized test cases for is_subtitle_file
SUBTITLE_FILE_CASES = [
	("movie.srt", True),
	("movie.sub", True),
	("movie.ass", True),
	("movie.vtt", True),
	("movie.SRT", True),
	("movie.mkv", False),
	("movie.txt", False),
]


#============================================
@pytest.mark.parametrize("filename, expected", SUBTITLE_FILE_CASES)
def test_is_subtitle_file(filename: str, expected: bool) -> None:
	"""Verify subtitle file extension detection."""
	result = moviemanager.core.file.classifier.is_subtitle_file(filename)
	assert result == expected


# parametrized test cases for is_artwork_file
ARTWORK_FILE_CASES = [
	("poster.jpg", True),
	("fanart.png", True),
	("random.jpg", True),
	("photo.jpeg", True),
	("image.webp", True),
	("movie.mkv", False),
	("movie.txt", False),
]


#============================================
@pytest.mark.parametrize("filename, expected", ARTWORK_FILE_CASES)
def test_is_artwork_file(filename: str, expected: bool) -> None:
	"""Verify artwork/image file extension detection."""
	result = moviemanager.core.file.classifier.is_artwork_file(filename)
	assert result == expected


# parametrized test cases for is_trailer_file
TRAILER_FILE_CASES = [
	("trailer.mp4", True),
	("Movie-trailer.mkv", True),
	("movie_trailer.avi", True),
	("movie.mkv", False),
	("trailer.srt", False),
	("trailer.jpg", False),
]


#============================================
@pytest.mark.parametrize("filename, expected", TRAILER_FILE_CASES)
def test_is_trailer_file(filename: str, expected: bool) -> None:
	"""Verify trailer file detection."""
	result = moviemanager.core.file.classifier.is_trailer_file(filename)
	assert result == expected


# parametrized test cases for is_nfo_file
NFO_FILE_CASES = [
	("movie.nfo", True),
	("movie.NFO", True),
	("info.nfo", True),
	("movie.txt", False),
	("movie.mkv", False),
]


#============================================
@pytest.mark.parametrize("filename, expected", NFO_FILE_CASES)
def test_is_nfo_file(filename: str, expected: bool) -> None:
	"""Verify NFO file extension detection."""
	result = moviemanager.core.file.classifier.is_nfo_file(filename)
	assert result == expected
