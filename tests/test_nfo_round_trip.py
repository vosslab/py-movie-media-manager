"""Round-trip tests for NFO reader and writer."""

# local repo modules
import moviemanager.core.nfo.reader
import moviemanager.core.nfo.writer
import moviemanager.core.models.movie
import moviemanager.core.models.movie_set


#============================================
def test_round_trip_basic(tmp_path):
	"""Write a Movie to NFO, read it back, verify all fields match."""
	# create a movie with representative data
	original = moviemanager.core.models.movie.Movie(
		title="The Dark Knight",
		original_title="The Dark Knight",
		sort_title="Dark Knight, The",
		year="2008",
		imdb_id="tt0468569",
		tmdb_id=155,
		tagline="Why So Serious?",
		plot="Batman raises the stakes in his war on crime.",
		runtime=152,
		certification="PG-13",
		country="US",
		spoken_languages="en",
		release_date="2008-07-18",
		rating=9.0,
		votes=2500000,
		top250=4,
		director="Christopher Nolan",
		writer="Jonathan Nolan, Christopher Nolan",
		studio="Warner Bros.",
		genres=["Action", "Crime", "Drama"],
		tags=["superhero", "dc comics"],
		actors=[
			{
				"name": "Christian Bale",
				"role": "Bruce Wayne",
				"thumb": "",
				"tmdb_id": 0,
			},
			{
				"name": "Heath Ledger",
				"role": "Joker",
				"thumb": "",
				"tmdb_id": 0,
			},
		],
		watched=True,
	)
	# write to temp file
	nfo_file = str(tmp_path / "movie.nfo")
	moviemanager.core.nfo.writer.write_nfo(original, nfo_file)
	# read back from file
	result = moviemanager.core.nfo.reader.read_nfo(nfo_file)
	# verify identity fields
	assert result.title == original.title
	assert result.original_title == original.original_title
	assert result.sort_title == original.sort_title
	assert result.year == original.year
	# verify external IDs
	assert result.imdb_id == original.imdb_id
	assert result.tmdb_id == original.tmdb_id
	# verify metadata fields
	assert result.tagline == original.tagline
	assert result.plot == original.plot
	assert result.runtime == original.runtime
	assert result.certification == original.certification
	assert result.country == original.country
	assert result.spoken_languages == original.spoken_languages
	assert result.release_date == original.release_date
	# verify ratings
	assert result.rating == original.rating
	assert result.votes == original.votes
	assert result.top250 == original.top250
	# verify credits
	assert result.director == original.director
	assert result.writer == original.writer
	assert result.studio == original.studio
	# verify classification
	assert result.genres == original.genres
	assert result.tags == original.tags
	# verify state
	assert result.watched == original.watched
	# verify actors
	assert len(result.actors) == 2
	assert result.actors[0]["name"] == "Christian Bale"
	assert result.actors[0]["role"] == "Bruce Wayne"
	assert result.actors[1]["name"] == "Heath Ledger"
	assert result.actors[1]["role"] == "Joker"


#============================================
def test_round_trip_empty(tmp_path):
	"""Empty movie should round-trip without errors."""
	original = moviemanager.core.models.movie.Movie()
	nfo_file = str(tmp_path / "empty.nfo")
	moviemanager.core.nfo.writer.write_nfo(original, nfo_file)
	result = moviemanager.core.nfo.reader.read_nfo(nfo_file)
	assert result.title == ""
	assert result.genres == []
	assert result.actors == []
	assert result.runtime == 0


#============================================
def test_round_trip_special_characters(tmp_path):
	"""Movie with special characters in title should round-trip."""
	original = moviemanager.core.models.movie.Movie(
		title="Leon: The Professional",
		plot="A hitman's life changes when he meets a girl.",
		tagline="It's a tough world & he knows it.",
	)
	nfo_file = str(tmp_path / "special.nfo")
	moviemanager.core.nfo.writer.write_nfo(original, nfo_file)
	result = moviemanager.core.nfo.reader.read_nfo(nfo_file)
	assert result.title == original.title
	assert result.plot == original.plot
	assert result.tagline == original.tagline


#============================================
def test_round_trip_movie_set(tmp_path):
	"""Movie with a movie set should round-trip the set name."""
	movie_set = moviemanager.core.models.movie_set.MovieSet(
		name="The Dark Knight Trilogy"
	)
	original = moviemanager.core.models.movie.Movie(
		title="Batman Begins",
		movie_set=movie_set,
	)
	nfo_file = str(tmp_path / "set.nfo")
	moviemanager.core.nfo.writer.write_nfo(original, nfo_file)
	result = moviemanager.core.nfo.reader.read_nfo(nfo_file)
	assert result.movie_set is not None
	assert result.movie_set.name == "The Dark Knight Trilogy"


#============================================
def test_round_trip_trailers(tmp_path):
	"""Movie with trailer URLs should round-trip them."""
	original = moviemanager.core.models.movie.Movie(
		title="Test Movie",
		trailer=[
			"https://example.com/trailer1.mp4",
			"https://example.com/trailer2.mp4",
		],
	)
	nfo_file = str(tmp_path / "trailer.nfo")
	moviemanager.core.nfo.writer.write_nfo(original, nfo_file)
	result = moviemanager.core.nfo.reader.read_nfo(nfo_file)
	assert len(result.trailer) == 2
	assert result.trailer[0] == "https://example.com/trailer1.mp4"
	assert result.trailer[1] == "https://example.com/trailer2.mp4"
