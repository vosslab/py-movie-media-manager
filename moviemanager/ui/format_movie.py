"""Pure formatting functions for movie metadata display.

Converts native Python types (float, int, list) to display strings.
Duck-typed on Movie attributes -- any object with the right fields works.
No PySide6 imports.
"""


#============================================
def format_rating(rating: float) -> str:
	"""Format a numeric rating for display.

	Args:
		rating: Rating value (0.0 means unset).

	Returns:
		Formatted string like "7.3/10", or empty if unset.
	"""
	if not rating:
		return ""
	text = f"{rating}/10"
	return text

assert format_rating(7.3) == "7.3/10"
assert format_rating(0.0) == ""
assert format_rating(10.0) == "10.0/10"


#============================================
def format_genres(genres: list) -> str:
	"""Format a list of genre strings for display.

	Args:
		genres: List of genre name strings.

	Returns:
		Comma-separated string like "Action, Drama", or empty.
	"""
	if not genres:
		return ""
	text = ", ".join(genres)
	return text

assert format_genres(["Action", "Drama"]) == "Action, Drama"
assert format_genres([]) == ""
assert format_genres(["Sci-Fi"]) == "Sci-Fi"


#============================================
def format_runtime(runtime: int) -> str:
	"""Format a runtime in minutes for display.

	Args:
		runtime: Runtime in minutes (0 means unset).

	Returns:
		Formatted string like "142 min", or empty if unset.
	"""
	if not runtime:
		return ""
	text = f"{runtime} min"
	return text

assert format_runtime(142) == "142 min"
assert format_runtime(0) == ""


#============================================
def format_ids(imdb_id: str, tmdb_id: int) -> str:
	"""Format external IDs for display.

	Args:
		imdb_id: IMDB identifier string (e.g. "tt1234567").
		tmdb_id: TMDB numeric identifier (0 means unset).

	Returns:
		Formatted string like "IMDB: tt1234567  TMDB: 155", or empty.
	"""
	parts = []
	if imdb_id:
		parts.append(f"IMDB: {imdb_id}")
	if tmdb_id:
		parts.append(f"TMDB: {tmdb_id}")
	text = "  ".join(parts)
	return text

assert format_ids("tt1234567", 155) == "IMDB: tt1234567  TMDB: 155"
assert format_ids("", 0) == ""
assert format_ids("tt0000001", 0) == "IMDB: tt0000001"
assert format_ids("", 42) == "TMDB: 42"


#============================================
def format_movie_fields(movie) -> dict:
	"""Format all display fields from a movie object.

	Duck-typed: works with any object that has the expected attributes.
	All values in the returned dict are strings, None-guarded.

	Args:
		movie: Object with title, year, rating, director, certification,
			genres, runtime, imdb_id, tmdb_id, and plot attributes.

	Returns:
		Dict with keys: title, year, rating, director, certification,
		genres, runtime, ids, plot. All values are strings.
	"""
	fields = {
		"title": movie.title or "",
		"year": movie.year or "",
		"rating": format_rating(movie.rating),
		"director": movie.director or "",
		"certification": movie.certification or "",
		"genres": format_genres(movie.genres),
		"runtime": format_runtime(movie.runtime),
		"ids": format_ids(movie.imdb_id, movie.tmdb_id),
		"plot": movie.plot or "",
	}
	return fields
