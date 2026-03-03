"""Tests for moviemanager.ui.format_movie formatting functions."""

# Standard Library
import sys
import dataclasses

# local repo modules
import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)

import moviemanager.ui.format_movie


#============================================
@dataclasses.dataclass
class FakeMovie:
	"""Minimal movie stub for testing format functions."""
	title: str = ""
	year: str = ""
	rating: float = 0.0
	director: str = ""
	certification: str = ""
	genres: list = dataclasses.field(default_factory=list)
	runtime: int = 0
	imdb_id: str = ""
	tmdb_id: int = 0
	plot: str = ""


#============================================
def test_format_rating_with_value():
	"""Rating formats as value/10."""
	result = moviemanager.ui.format_movie.format_rating(7.3)
	assert result == "7.3/10"


#============================================
def test_format_rating_zero():
	"""Zero rating returns empty string."""
	result = moviemanager.ui.format_movie.format_rating(0.0)
	assert result == ""


#============================================
def test_format_genres_multiple():
	"""Multiple genres join with comma-space."""
	result = moviemanager.ui.format_movie.format_genres(
		["Action", "Drama", "Thriller"]
	)
	assert result == "Action, Drama, Thriller"


#============================================
def test_format_genres_empty():
	"""Empty genre list returns empty string."""
	result = moviemanager.ui.format_movie.format_genres([])
	assert result == ""


#============================================
def test_format_runtime_with_value():
	"""Runtime formats as minutes."""
	result = moviemanager.ui.format_movie.format_runtime(142)
	assert result == "142 min"


#============================================
def test_format_runtime_zero():
	"""Zero runtime returns empty string."""
	result = moviemanager.ui.format_movie.format_runtime(0)
	assert result == ""


#============================================
def test_format_ids_both():
	"""Both IMDB and TMDB IDs are shown."""
	result = moviemanager.ui.format_movie.format_ids("tt1234567", 155)
	assert result == "IMDB: tt1234567  TMDB: 155"


#============================================
def test_format_ids_imdb_only():
	"""Only IMDB ID when TMDB is zero."""
	result = moviemanager.ui.format_movie.format_ids("tt0000001", 0)
	assert result == "IMDB: tt0000001"


#============================================
def test_format_ids_tmdb_only():
	"""Only TMDB ID when IMDB is empty."""
	result = moviemanager.ui.format_movie.format_ids("", 42)
	assert result == "TMDB: 42"


#============================================
def test_format_ids_none():
	"""No IDs returns empty string."""
	result = moviemanager.ui.format_movie.format_ids("", 0)
	assert result == ""


#============================================
def test_format_movie_fields_full():
	"""All fields populate correctly from a fully-set movie."""
	movie = FakeMovie(
		title="The Dark Knight",
		year="2008",
		rating=9.0,
		director="Christopher Nolan",
		certification="PG-13",
		genres=["Action", "Crime", "Drama"],
		runtime=152,
		imdb_id="tt0468569",
		tmdb_id=155,
		plot="Batman raises the stakes in his war on crime.",
	)
	fields = moviemanager.ui.format_movie.format_movie_fields(movie)
	assert fields["title"] == "The Dark Knight"
	assert fields["year"] == "2008"
	assert fields["rating"] == "9.0/10"
	assert fields["director"] == "Christopher Nolan"
	assert fields["certification"] == "PG-13"
	assert fields["genres"] == "Action, Crime, Drama"
	assert fields["runtime"] == "152 min"
	assert fields["ids"] == "IMDB: tt0468569  TMDB: 155"
	assert fields["plot"] == "Batman raises the stakes in his war on crime."


#============================================
def test_format_movie_fields_empty():
	"""Empty movie returns all empty strings."""
	movie = FakeMovie()
	fields = moviemanager.ui.format_movie.format_movie_fields(movie)
	assert fields["title"] == ""
	assert fields["year"] == ""
	assert fields["rating"] == ""
	assert fields["director"] == ""
	assert fields["certification"] == ""
	assert fields["genres"] == ""
	assert fields["runtime"] == ""
	assert fields["ids"] == ""
	assert fields["plot"] == ""


#============================================
def test_format_movie_fields_partial_ids():
	"""Partial IDs show only available identifiers."""
	movie = FakeMovie(
		title="Test Movie",
		imdb_id="tt9999999",
		tmdb_id=0,
	)
	fields = moviemanager.ui.format_movie.format_movie_fields(movie)
	assert fields["ids"] == "IMDB: tt9999999"
