"""Tests for template engine expand_template and build_file_template."""

# Standard Library
import dataclasses

# local repo modules
import moviemanager.core.constants
import moviemanager.core.models.media_file
import moviemanager.core.models.movie
import moviemanager.core.movie.template_engine


#============================================
def test_expand_template_title_year():
	"""Basic title and year substitution."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title} ({year})", movie
	)
	assert result == "Inception (2010)"


#============================================
def test_expand_template_missing_year_removes_parens():
	"""Empty year causes empty parentheses to be removed."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title} ({year})", movie
	)
	assert result == "Inception"


#============================================
def test_expand_template_missing_brackets():
	"""Empty tokens cause empty brackets to be removed."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title} [{year}]", movie
	)
	assert result == "Inception"


#============================================
def test_expand_template_first_letter():
	"""First letter token extracts uppercase initial."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{first_letter} - {title}", movie
	)
	assert result == "I - Inception"


#============================================
def test_expand_template_genre():
	"""Genre token uses first genre from list."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
		genres=["Sci-Fi", "Action"],
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{genre} - {title}", movie
	)
	assert result == "Sci-Fi - Inception"


#============================================
def test_expand_template_empty_genre():
	"""Empty genres list produces empty string for genre token."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title}-{genre}", movie
	)
	# genre is empty, so just title with trailing hyphen cleaned
	assert "Inception" in result


#============================================
def test_expand_template_director():
	"""Director token is substituted correctly."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
		director="Christopher Nolan",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title} - {director}", movie
	)
	assert result == "Inception - Christopher Nolan"


#============================================
def test_expand_template_special_chars_cleaned():
	"""Colons and slashes are removed by clean_filename."""
	movie = moviemanager.core.models.movie.Movie(
		title='Mission: Impossible / Rogue Nation',
		year="2015",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title} ({year})", movie
	)
	assert ":" not in result
	assert "/" not in result
	assert "2015" in result
	assert "Mission" in result


#============================================
def test_expand_template_shell_safe():
	"""Shell-safe mode replaces spaces and special chars."""
	movie = moviemanager.core.models.movie.Movie(
		title="Ocean's Eleven",
		year="2001",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title}-{year}", movie, spaces_to_underscores=True,
	)
	assert "'" not in result
	assert " " not in result
	assert "2001" in result


#============================================
def test_expand_template_collapses_spaces():
	"""Multiple spaces from empty tokens collapse to single space."""
	movie = moviemanager.core.models.movie.Movie(
		title="Inception",
		year="2010",
		certification="",
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title}  {certification}  {year}", movie
	)
	# double spaces should be collapsed
	assert "  " not in result


#============================================
def test_expand_template_with_media_tokens():
	"""Media tokens from video file are substituted."""
	video_mf = moviemanager.core.models.media_file.MediaFile(
		path="/tmp/test.mkv",
		filename="test.mkv",
		file_type=moviemanager.core.constants.MediaFileType.VIDEO,
		video_codec="x264",
		audio_codec="AAC",
		audio_channels="5.1",
	)
	movie = moviemanager.core.models.movie.Movie(
		title="Test",
		year="2020",
		media_files=[video_mf],
	)
	result = moviemanager.core.movie.template_engine.expand_template(
		"{title}-{year}-{vcodec}-{acodec}", movie
	)
	assert result == "Test-2020-x264-AAC"


#============================================
def test_build_file_template_defaults():
	"""Default settings produce title-year template."""
	settings = _make_settings()
	result = moviemanager.core.movie.template_engine.build_file_template(
		settings
	)
	assert result == "{title}-{year}"


#============================================
def test_build_file_template_with_resolution():
	"""Resolution checkbox appends resolution token."""
	settings = _make_settings(rename_resolution=True)
	result = moviemanager.core.movie.template_engine.build_file_template(
		settings
	)
	assert result == "{title}-{year}-{resolution}"


#============================================
def test_build_file_template_all_tokens():
	"""All media checkboxes append all tokens."""
	settings = _make_settings(
		rename_resolution=True,
		rename_vcodec=True,
		rename_acodec=True,
		rename_channels=True,
	)
	result = moviemanager.core.movie.template_engine.build_file_template(
		settings
	)
	expected = "{title}-{year}-{resolution}-{vcodec}-{acodec}-{channels}"
	assert result == expected


#============================================
def test_build_file_template_dot_separator():
	"""Dot separator joins tokens with dots."""
	settings = _make_settings(
		media_separator=".",
		rename_resolution=True,
	)
	result = moviemanager.core.movie.template_engine.build_file_template(
		settings
	)
	assert result == "{title}.{year}.{resolution}"


#============================================
@dataclasses.dataclass
class _MockSettings:
	"""Minimal settings mock for build_file_template tests."""
	media_separator: str = "-"
	rename_resolution: bool = False
	rename_vcodec: bool = False
	rename_acodec: bool = False
	rename_channels: bool = False


#============================================
def _make_settings(**kwargs) -> _MockSettings:
	"""Create a mock settings object with optional overrides.

	Args:
		**kwargs: fields to override on _MockSettings.

	Returns:
		_MockSettings instance.
	"""
	settings = _MockSettings(**kwargs)
	return settings
