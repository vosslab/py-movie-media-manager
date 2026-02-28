"""IMDB scraper implementing MetadataProvider using cinemagoer."""

# Standard Library
import time
import random

# PIP3 modules
import imdb  # cinemagoer package

# local repo modules
import moviemanager.scraper.interfaces
import moviemanager.scraper.types


#============================================
class ImdbScraper(moviemanager.scraper.interfaces.MetadataProvider):
	"""IMDB metadata scraper using the cinemagoer library.

	Wraps the cinemagoer (formerly IMDbPY) package to fetch movie
	metadata from IMDB.
	"""

	#============================================
	def __init__(self):
		"""Initialize the IMDB scraper with a Cinemagoer instance."""
		self._ia = imdb.Cinemagoer()

	#============================================
	def search(self, title: str, year: str = "") -> list:
		"""Search IMDB for movies matching a title.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			list: List of SearchResult dataclasses.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		# build query with optional year
		query = title
		if year:
			query = f"{title} ({year})"
		raw_results = self._ia.search_movie(query)
		# map raw cinemagoer objects to SearchResult dataclasses
		results = []
		for item in raw_results:
			# format imdb id with tt prefix and zero-padding to 7 digits
			movie_id = item.movieID
			imdb_id = f"tt{int(movie_id):07d}"
			item_year = str(item.get("year", ""))
			search_result = moviemanager.scraper.types.SearchResult(
				title=item.get("title", ""),
				year=item_year,
				imdb_id=imdb_id,
			)
			results.append(search_result)
		return results

	#============================================
	def get_metadata(
		self, tmdb_id: int = 0, imdb_id: str = ""
	) -> moviemanager.scraper.types.MediaMetadata:
		"""Fetch full metadata for a movie from IMDB.

		Args:
			tmdb_id: TMDB movie ID (unused, kept for interface).
			imdb_id: IMDB movie ID (tt format).

		Returns:
			MediaMetadata: Complete movie metadata.
		"""
		# strip tt prefix to get numeric id
		numeric_id = imdb_id.lstrip("t")
		# rate-limit courtesy pause
		time.sleep(random.random())
		movie_obj = self._ia.get_movie(numeric_id)
		# update to fetch full data
		time.sleep(random.random())
		self._ia.update(movie_obj)
		# extract year
		year_str = str(movie_obj.get("year", ""))
		# extract rating and votes
		rating = float(movie_obj.get("rating", 0.0) or 0.0)
		votes = int(movie_obj.get("votes", 0) or 0)
		# extract top 250 rank
		top250 = int(movie_obj.get("top 250 rank", 0) or 0)
		# extract genres
		genres = list(movie_obj.get("genres", []))
		# extract US certification from certificates list
		certification = _extract_us_certification(
			movie_obj.get("certificates", [])
		)
		# extract director names
		raw_directors = movie_obj.get("director", [])
		director_names = [
			person.get("name", "") for person in raw_directors
		]
		director = ", ".join(director_names)
		# extract writer names
		raw_writers = movie_obj.get("writer", [])
		writer_names = [
			person.get("name", "") for person in raw_writers
		]
		writer = ", ".join(writer_names)
		# map cast to CastMember dataclasses
		raw_cast = movie_obj.get("cast", [])
		actors = []
		for person in raw_cast:
			cast_member = moviemanager.scraper.types.CastMember(
				name=person.get("name", ""),
				role=str(person.currentRole) if person.currentRole else "",
				imdb_id=f"nm{int(person.personID):07d}",
				department="Acting",
			)
			actors.append(cast_member)
		# extract plot
		plot = movie_obj.get("plot outline", "") or ""
		# extract runtime in minutes
		runtimes = movie_obj.get("runtimes", ["0"])
		runtime = int(runtimes[0]) if runtimes else 0
		# extract country
		countries = movie_obj.get("countries", [])
		country = ", ".join(countries)
		# format imdb_id with tt prefix
		formatted_imdb_id = f"tt{int(movie_obj.movieID):07d}"
		metadata = moviemanager.scraper.types.MediaMetadata(
			title=movie_obj.get("title", ""),
			year=year_str,
			plot=plot,
			runtime=runtime,
			rating=rating,
			votes=votes,
			top250=top250,
			genres=genres,
			certification=certification,
			director=director,
			writer=writer,
			actors=actors,
			country=country,
			imdb_id=formatted_imdb_id,
			media_source="imdb",
		)
		return metadata


#============================================
def _extract_us_certification(certificates: list) -> str:
	"""Extract US certification from IMDB certificates list.

	Args:
		certificates: List of certificate strings like 'United States:PG-13'.

	Returns:
		str: US certification string, or empty string if not found.
	"""
	for cert in certificates:
		if cert.startswith("United States:"):
			# return the rating portion after the colon
			rating = cert.split(":", 1)[1]
			return rating
	return ""
