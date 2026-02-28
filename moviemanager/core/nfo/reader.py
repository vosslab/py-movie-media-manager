#!/usr/bin/env python3
"""Read Kodi-format NFO XML files into Movie data models."""

# Standard Library
import os

# PIP3 modules
import lxml.etree

# local repo modules
import moviemanager.core.models.movie
import moviemanager.core.models.movie_set


# set of element tags that are handled by the reader
KNOWN_TAGS = {
	"title", "originaltitle", "sorttitle", "year", "id", "tmdbid",
	"tagline", "plot", "outline", "runtime", "mpaa", "country",
	"languages", "premiered", "rating", "votes", "top250",
	"userrating", "director", "credits", "studio", "watched",
	"playcount", "dateadded", "lastplayed", "trailer", "poster",
	"set", "genre", "tag", "actor", "producer", "thumb", "fanart",
}


#============================================
def _get_text(element: lxml.etree._Element, tag: str) -> str:
	"""Get the text content of a child element.

	Args:
		element: Parent XML element to search.
		tag: Tag name of the child element.

	Returns:
		Text content of the child, or empty string if missing.
	"""
	child = element.find(tag)
	if child is not None and child.text:
		text = child.text.strip()
		return text
	return ""


#============================================
def _parse_actor(actor_elem: lxml.etree._Element) -> dict:
	"""Parse an actor or producer XML element into a dict.

	Args:
		actor_elem: XML element containing name, role, thumb, tmdbid children.

	Returns:
		Dict with keys: name, role, thumb, tmdb_id.
	"""
	name = _get_text(actor_elem, "name")
	role = _get_text(actor_elem, "role")
	thumb = _get_text(actor_elem, "thumb")
	tmdb_id_str = _get_text(actor_elem, "tmdbid")
	# parse tmdb_id as int, default to 0
	if tmdb_id_str:
		tmdb_id = int(tmdb_id_str)
	else:
		tmdb_id = 0
	result = {
		"name": name,
		"role": role,
		"thumb": thumb,
		"tmdb_id": tmdb_id,
	}
	return result


#============================================
def _parse_set(set_elem: lxml.etree._Element) -> moviemanager.core.models.movie_set.MovieSet:
	"""Parse a set XML element into a MovieSet.

	Handles both <set><name>...</name></set> and <set>text</set> formats.

	Args:
		set_elem: XML element for the movie set.

	Returns:
		MovieSet with the parsed name.
	"""
	# check for <name> child element first
	name_child = set_elem.find("name")
	if name_child is not None and name_child.text:
		set_name = name_child.text.strip()
	elif set_elem.text:
		# fallback to direct text content
		set_name = set_elem.text.strip()
	else:
		set_name = ""
	movie_set = moviemanager.core.models.movie_set.MovieSet(name=set_name)
	return movie_set


#============================================
def read_nfo(nfo_path: str) -> moviemanager.core.models.movie.Movie:
	"""Read a Kodi-format NFO XML file and return a Movie.

	Args:
		nfo_path: Path to the NFO file on disk.

	Returns:
		Movie populated with data from the NFO file.
	"""
	# parse the XML file
	tree = lxml.etree.parse(nfo_path)
	root = tree.getroot()

	# create a new movie instance
	movie = moviemanager.core.models.movie.Movie()
	movie.nfo_path = nfo_path
	movie.path = os.path.dirname(nfo_path)

	# collect unknown elements for round-trip preservation
	unknown_elements = []

	for child in root:
		tag = child.tag
		text = child.text.strip() if child.text else ""

		if tag == "title":
			movie.title = text
		elif tag == "originaltitle":
			movie.original_title = text
		elif tag == "sorttitle":
			movie.sort_title = text
		elif tag == "year":
			movie.year = text
		elif tag == "id":
			movie.imdb_id = text
		elif tag == "tmdbid":
			if text:
				movie.tmdb_id = int(text)
		elif tag == "tagline":
			movie.tagline = text
		elif tag == "plot":
			movie.plot = text
		elif tag == "outline":
			# use outline as fallback for plot
			if not movie.plot:
				movie.plot = text
		elif tag == "runtime":
			if text:
				movie.runtime = int(text)
		elif tag == "mpaa":
			movie.certification = text
		elif tag == "country":
			movie.country = text
		elif tag == "languages":
			movie.spoken_languages = text
		elif tag == "premiered":
			movie.release_date = text
		elif tag == "rating":
			if text:
				movie.rating = float(text)
		elif tag == "votes":
			if text:
				# handle comma-separated vote counts like "1,234"
				cleaned = text.replace(",", "")
				movie.votes = int(cleaned)
		elif tag == "top250":
			if text:
				movie.top250 = int(text)
		elif tag == "userrating":
			if text:
				movie.user_rating = float(text)
		elif tag == "director":
			movie.director = text
		elif tag == "credits":
			movie.writer = text
		elif tag == "studio":
			movie.studio = text
		elif tag == "watched":
			movie.watched = text.lower() in ("true", "1")
		elif tag == "playcount":
			if text and int(text) > 0:
				movie.watched = True
		elif tag == "dateadded":
			movie.date_added = text
		elif tag == "lastplayed":
			movie.last_watched = text
		elif tag == "trailer":
			if text:
				movie.trailer.append(text)
		elif tag == "poster":
			movie.poster_url = text
		elif tag == "thumb":
			# thumb element can be poster
			movie.poster_url = text
		elif tag == "fanart":
			# fanart contains child thumb elements
			fanart_thumb = child.find("thumb")
			if fanart_thumb is not None and fanart_thumb.text:
				movie.fanart_url = fanart_thumb.text.strip()
		elif tag == "set":
			movie.movie_set = _parse_set(child)
		elif tag == "genre":
			if text:
				movie.genres.append(text)
		elif tag == "tag":
			if text:
				movie.tags.append(text)
		elif tag == "actor":
			actor_dict = _parse_actor(child)
			movie.actors.append(actor_dict)
		elif tag == "producer":
			producer_dict = _parse_actor(child)
			movie.producers.append(producer_dict)
		else:
			# preserve unknown elements for round-trip
			unknown_elements.append(child)

	movie.unknown_elements = unknown_elements
	return movie
