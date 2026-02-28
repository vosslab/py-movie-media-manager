"""Tests for the IMDB scraper module."""

# Standard Library
import unittest.mock

# local repo modules
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.types


#============================================
def _make_mock_movie(movie_id: str, data: dict):
	"""Create a mock cinemagoer movie object.

	Args:
		movie_id: IMDB numeric movie ID string.
		data: Dictionary of movie attributes.

	Returns:
		Mock object mimicking a cinemagoer Movie.
	"""
	mock_movie = unittest.mock.MagicMock()
	mock_movie.movieID = movie_id
	mock_movie.get = lambda key, default=None: data.get(key, default)
	return mock_movie


#============================================
def _make_mock_person(person_id: str, name: str, role: str = ""):
	"""Create a mock cinemagoer person object.

	Args:
		person_id: IMDB numeric person ID string.
		name: Person name.
		role: Character or role name.

	Returns:
		Mock object mimicking a cinemagoer Person.
	"""
	mock_person = unittest.mock.MagicMock()
	mock_person.personID = person_id
	mock_person.get = lambda key, default=None: {
		"name": name,
	}.get(key, default)
	mock_person.currentRole = role
	return mock_person


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.imdb.Cinemagoer")
def test_search_returns_results(mock_cinemagoer_cls, mock_sleep):
	"""Verify search maps cinemagoer results to SearchResult list."""
	# set up mock cinemagoer instance
	mock_ia = unittest.mock.MagicMock()
	mock_cinemagoer_cls.return_value = mock_ia
	# create mock search results
	movie1 = _make_mock_movie("0133093", {"title": "The Matrix", "year": 1999})
	movie2 = _make_mock_movie("0234215", {"title": "The Matrix Reloaded", "year": 2003})
	mock_ia.search_movie.return_value = [movie1, movie2]
	# create scraper and search
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("The Matrix")
	# verify results
	assert len(results) == 2
	assert results[0].title == "The Matrix"
	assert results[0].imdb_id == "tt0133093"
	assert results[0].year == "1999"
	assert results[1].title == "The Matrix Reloaded"
	assert results[1].imdb_id == "tt0234215"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.imdb.Cinemagoer")
def test_search_empty(mock_cinemagoer_cls, mock_sleep):
	"""Verify search returns empty list when no results found."""
	mock_ia = unittest.mock.MagicMock()
	mock_cinemagoer_cls.return_value = mock_ia
	mock_ia.search_movie.return_value = []
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("xyznonexistent")
	assert results == []


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.imdb.Cinemagoer")
def test_get_metadata_rating(mock_cinemagoer_cls, mock_sleep):
	"""Verify rating and votes are extracted from movie data."""
	mock_ia = unittest.mock.MagicMock()
	mock_cinemagoer_cls.return_value = mock_ia
	# create a detailed mock movie
	movie_data = {
		"title": "The Matrix",
		"year": 1999,
		"rating": 8.7,
		"votes": 1900000,
		"top 250 rank": 0,
		"genres": ["Action", "Sci-Fi"],
		"certificates": [],
		"director": [],
		"writer": [],
		"cast": [],
		"plot outline": "A hacker discovers reality is a simulation.",
		"runtimes": ["136"],
		"countries": ["United States"],
	}
	mock_movie = _make_mock_movie("0133093", movie_data)
	mock_ia.get_movie.return_value = mock_movie
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0133093")
	assert metadata.rating == 8.7
	assert metadata.votes == 1900000
	assert metadata.title == "The Matrix"
	assert metadata.runtime == 136


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.imdb.Cinemagoer")
def test_get_metadata_actors(mock_cinemagoer_cls, mock_sleep):
	"""Verify actors are mapped to CastMember dataclasses."""
	mock_ia = unittest.mock.MagicMock()
	mock_cinemagoer_cls.return_value = mock_ia
	# create mock cast members
	actor1 = _make_mock_person("0000206", "Keanu Reeves", "Neo")
	actor2 = _make_mock_person("0000401", "Laurence Fishburne", "Morpheus")
	movie_data = {
		"title": "The Matrix",
		"year": 1999,
		"rating": 8.7,
		"votes": 1900000,
		"top 250 rank": 0,
		"genres": [],
		"certificates": [],
		"director": [],
		"writer": [],
		"cast": [actor1, actor2],
		"plot outline": "",
		"runtimes": ["136"],
		"countries": [],
	}
	mock_movie = _make_mock_movie("0133093", movie_data)
	mock_ia.get_movie.return_value = mock_movie
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0133093")
	assert len(metadata.actors) == 2
	assert metadata.actors[0].name == "Keanu Reeves"
	assert metadata.actors[0].role == "Neo"
	assert metadata.actors[0].department == "Acting"
	assert metadata.actors[1].name == "Laurence Fishburne"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.imdb.Cinemagoer")
def test_get_metadata_top250(mock_cinemagoer_cls, mock_sleep):
	"""Verify top250 rank is extracted from movie data."""
	mock_ia = unittest.mock.MagicMock()
	mock_cinemagoer_cls.return_value = mock_ia
	movie_data = {
		"title": "The Shawshank Redemption",
		"year": 1994,
		"rating": 9.3,
		"votes": 2700000,
		"top 250 rank": 1,
		"genres": ["Drama"],
		"certificates": ["United States:R"],
		"director": [],
		"writer": [],
		"cast": [],
		"plot outline": "",
		"runtimes": ["142"],
		"countries": ["United States"],
	}
	mock_movie = _make_mock_movie("0111161", movie_data)
	mock_ia.get_movie.return_value = mock_movie
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt0111161")
	assert metadata.top250 == 1
	assert metadata.certification == "R"


#============================================
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.imdb_scraper.imdb.Cinemagoer")
def test_imdb_id_formatting(mock_cinemagoer_cls, mock_sleep):
	"""Verify tt prefix is stripped for API call and formatted on output."""
	mock_ia = unittest.mock.MagicMock()
	mock_cinemagoer_cls.return_value = mock_ia
	movie_data = {
		"title": "Test Movie",
		"year": 2020,
		"rating": 5.0,
		"votes": 100,
		"top 250 rank": 0,
		"genres": [],
		"certificates": [],
		"director": [],
		"writer": [],
		"cast": [],
		"plot outline": "",
		"runtimes": ["90"],
		"countries": [],
	}
	mock_movie = _make_mock_movie("1234567", movie_data)
	mock_ia.get_movie.return_value = mock_movie
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	metadata = scraper.get_metadata(imdb_id="tt1234567")
	# verify the numeric id was passed to get_movie (tt stripped)
	mock_ia.get_movie.assert_called_once_with("1234567")
	# verify output has tt prefix
	assert metadata.imdb_id == "tt1234567"
