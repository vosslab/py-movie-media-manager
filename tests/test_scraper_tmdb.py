"""Tests for TMDB scraper wrapper using mocked API calls."""

# Standard Library
import types
import unittest.mock

# local repo modules
import moviemanager.scraper.tmdb_scraper
import moviemanager.scraper.types


#============================================
def _make_search_result(
	title: str = "Test Movie",
	original_title: str = "Test Movie Original",
	release_date: str = "2024-06-15",
	movie_id: int = 12345,
	overview: str = "A test movie.",
	poster_path: str = "/abc123.jpg",
	vote_average: float = 7.5,
) -> types.SimpleNamespace:
	"""Build a fake tmdbv3api search result object.

	Args:
		title: Movie title.
		original_title: Original language title.
		release_date: Release date string.
		movie_id: TMDB movie ID.
		overview: Plot overview text.
		poster_path: Poster image path.
		vote_average: Average vote score.

	Returns:
		SimpleNamespace mimicking a tmdbv3api result object.
	"""
	result = types.SimpleNamespace(
		title=title,
		original_title=original_title,
		release_date=release_date,
		id=movie_id,
		overview=overview,
		poster_path=poster_path,
		vote_average=vote_average,
	)
	return result


#============================================
def _make_detail_result() -> types.SimpleNamespace:
	"""Build a fake tmdbv3api movie detail object with credits and releases.

	Returns:
		SimpleNamespace mimicking a tmdbv3api detail response.
	"""
	crew_director = types.SimpleNamespace(
		name="Jane Director", job="Director", department="Directing"
	)
	crew_writer = types.SimpleNamespace(
		name="John Writer", job="Screenplay", department="Writing"
	)
	cast_member = types.SimpleNamespace(
		name="Alice Actor", character="Hero", id=999
	)
	credits = types.SimpleNamespace(
		crew=[crew_director, crew_writer],
		cast=[cast_member],
	)
	us_release = types.SimpleNamespace(
		iso_3166_1="US", certification="PG-13"
	)
	releases = types.SimpleNamespace(countries=[us_release])
	detail = types.SimpleNamespace(
		title="Test Movie",
		original_title="Test Movie Original",
		release_date="2024-06-15",
		overview="A test movie plot.",
		tagline="Testing is fun",
		runtime=120,
		vote_average=7.5,
		vote_count=1000,
		genres=[{"name": "Action"}, {"name": "Comedy"}],
		production_companies=[{"name": "Test Studio"}],
		production_countries=[{"name": "United States of America"}],
		spoken_languages=[{"english_name": "English"}],
		imdb_id="tt1234567",
		id=12345,
		poster_path="/poster123.jpg",
		backdrop_path="/backdrop123.jpg",
		credits=credits,
		releases=releases,
	)
	return detail


#============================================
def _make_images_result() -> types.SimpleNamespace:
	"""Build a fake tmdbv3api images response.

	Returns:
		SimpleNamespace mimicking a tmdbv3api images response.
	"""
	poster1 = types.SimpleNamespace(file_path="/poster_a.jpg")
	poster2 = types.SimpleNamespace(file_path="/poster_b.jpg")
	backdrop1 = types.SimpleNamespace(file_path="/back_a.jpg")
	result = types.SimpleNamespace(
		posters=[poster1, poster2],
		backdrops=[backdrop1],
	)
	return result


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_search_returns_results(mock_movie_cls, mock_tmdb_cls):
	"""Verify search maps tmdbv3api results to SearchResult dataclasses."""
	fake_result = _make_search_result()
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.search.return_value = [fake_result]
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	# override the movie instance with our mock
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep"):
		results = scraper.search("Test Movie")
	assert len(results) == 1
	first = results[0]
	assert isinstance(first, moviemanager.scraper.types.SearchResult)
	assert first.title == "Test Movie"
	assert first.year == "2024"
	assert first.tmdb_id == 12345
	assert first.poster_url == "https://image.tmdb.org/t/p/w500/abc123.jpg"
	assert first.score == 7.5


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_search_empty(mock_movie_cls, mock_tmdb_cls):
	"""Verify search returns empty list when no results found."""
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.search.return_value = []
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep"):
		results = scraper.search("Nonexistent Movie")
	assert results == []


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_get_metadata_basic(mock_movie_cls, mock_tmdb_cls):
	"""Verify get_metadata maps detail response to MediaMetadata."""
	fake_detail = _make_detail_result()
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.details.return_value = fake_detail
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep"):
		meta = scraper.get_metadata(tmdb_id=12345)
	assert isinstance(meta, moviemanager.scraper.types.MediaMetadata)
	assert meta.title == "Test Movie"
	assert meta.year == "2024"
	assert meta.runtime == 120
	assert meta.rating == 7.5
	assert meta.votes == 1000
	assert meta.genres == ["Action", "Comedy"]
	assert meta.studio == "Test Studio"
	assert meta.imdb_id == "tt1234567"
	assert meta.tmdb_id == 12345
	assert meta.certification == "PG-13"
	assert meta.country == "United States of America"
	assert meta.spoken_languages == "English"


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_get_metadata_extracts_director(mock_movie_cls, mock_tmdb_cls):
	"""Verify director is extracted from crew list."""
	fake_detail = _make_detail_result()
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.details.return_value = fake_detail
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep"):
		meta = scraper.get_metadata(tmdb_id=12345)
	assert meta.director == "Jane Director"
	assert meta.writer == "John Writer"


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_get_metadata_extracts_actors(mock_movie_cls, mock_tmdb_cls):
	"""Verify actors are mapped to CastMember dataclasses."""
	fake_detail = _make_detail_result()
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.details.return_value = fake_detail
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep"):
		meta = scraper.get_metadata(tmdb_id=12345)
	assert len(meta.actors) == 1
	actor = meta.actors[0]
	assert isinstance(actor, moviemanager.scraper.types.CastMember)
	assert actor.name == "Alice Actor"
	assert actor.role == "Hero"
	assert actor.tmdb_id == 999


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_get_artwork_returns_urls(mock_movie_cls, mock_tmdb_cls):
	"""Verify get_artwork returns poster and fanart URL lists."""
	fake_images = _make_images_result()
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.images.return_value = fake_images
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep"):
		artwork = scraper.get_artwork(tmdb_id=12345)
	assert "poster" in artwork
	assert "fanart" in artwork
	assert len(artwork["poster"]) == 2
	assert len(artwork["fanart"]) == 1
	base = "https://image.tmdb.org/t/p/original"
	assert artwork["poster"][0] == f"{base}/poster_a.jpg"
	assert artwork["fanart"][0] == f"{base}/back_a.jpg"


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
def test_sleep_between_calls(mock_movie_cls, mock_tmdb_cls):
	"""Verify time.sleep is called before API requests."""
	mock_movie_instance = mock_movie_cls.return_value
	mock_movie_instance.search.return_value = []
	mock_movie_instance.details.return_value = _make_detail_result()
	mock_movie_instance.images.return_value = _make_images_result()
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_movie = mock_movie_instance
	with unittest.mock.patch("time.sleep") as mock_sleep:
		scraper.search("Test")
		# sleep called once for search
		assert mock_sleep.call_count == 1
	with unittest.mock.patch("time.sleep") as mock_sleep:
		scraper.get_metadata(tmdb_id=1)
		assert mock_sleep.call_count == 1
	with unittest.mock.patch("time.sleep") as mock_sleep:
		scraper.get_artwork(tmdb_id=1)
		assert mock_sleep.call_count == 1


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
@unittest.mock.patch("tmdbv3api.Find")
def test_find_by_imdb_id_returns_tmdb_id_and_poster(
	mock_find_cls, mock_movie_cls, mock_tmdb_cls
):
	"""Verify imdb_id lookup returns TMDB id and poster URL."""
	fake_match = types.SimpleNamespace(id=155, poster_path="/dk.jpg")
	fake_find_result = types.SimpleNamespace(movie_results=[fake_match])
	mock_find_instance = mock_find_cls.return_value
	mock_find_instance.find_by_imdb_id.return_value = fake_find_result
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_find = mock_find_instance
	with unittest.mock.patch("time.sleep"):
		tmdb_id, poster_url = scraper.find_by_imdb_id("tt0468569")
	assert tmdb_id == 155
	assert poster_url == "https://image.tmdb.org/t/p/w500/dk.jpg"


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
@unittest.mock.patch("tmdbv3api.Find")
def test_find_by_imdb_id_empty_returns_defaults(
	mock_find_cls, mock_movie_cls, mock_tmdb_cls
):
	"""Verify imdb_id lookup handles no TMDB match."""
	fake_find_result = types.SimpleNamespace(movie_results=[])
	mock_find_instance = mock_find_cls.return_value
	mock_find_instance.find_by_imdb_id.return_value = fake_find_result
	scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(api_key="fake")
	scraper._tmdb_find = mock_find_instance
	with unittest.mock.patch("time.sleep"):
		tmdb_id, poster_url = scraper.find_by_imdb_id("tt0000000")
	assert tmdb_id == 0
	assert poster_url == ""
