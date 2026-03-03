"""Write Movie data models to Kodi-format NFO XML files."""

# Standard Library
import os
import copy

# PIP3 modules
import lxml.etree

# local repo modules
import moviemanager.core.models.movie


#============================================
def _add_text_element(
	parent: lxml.etree._Element, tag: str, text: str
) -> None:
	"""Add a child element with text content to the parent.

	Args:
		parent: Parent XML element to append to.
		tag: Tag name for the new child element.
		text: Text content for the child element.
	"""
	child = lxml.etree.SubElement(parent, tag)
	child.text = text


#============================================
def _add_actor_element(
	parent: lxml.etree._Element, tag: str, actor: dict
) -> None:
	"""Add an actor or producer element with child fields.

	Args:
		parent: Parent XML element to append to.
		tag: Tag name, typically "actor" or "producer".
		actor: Dict with keys: name, role, thumb, tmdb_id.
	"""
	elem = lxml.etree.SubElement(parent, tag)
	# add name
	name = actor.get("name", "")
	if name:
		_add_text_element(elem, "name", name)
	# add role
	role = actor.get("role", "")
	if role:
		_add_text_element(elem, "role", role)
	# add thumb
	thumb = actor.get("thumb", "")
	if thumb:
		_add_text_element(elem, "thumb", thumb)
	# add tmdb_id
	tmdb_id = actor.get("tmdb_id", 0)
	if tmdb_id:
		_add_text_element(elem, "tmdbid", str(tmdb_id))


#============================================
def write_nfo(
	movie: moviemanager.core.models.movie.Movie, nfo_path: str
) -> None:
	"""Write a Movie to a Kodi-format NFO XML file.

	Args:
		movie: Movie data model to serialize.
		nfo_path: Destination file path for the NFO file.
	"""
	# create parent directories if needed
	parent_dir = os.path.dirname(nfo_path)
	if parent_dir:
		os.makedirs(parent_dir, exist_ok=True)

	# create the root element
	root = lxml.etree.Element("movie")

	# 1. title
	if movie.title:
		_add_text_element(root, "title", movie.title)

	# 2. originaltitle
	if movie.original_title:
		_add_text_element(root, "originaltitle", movie.original_title)

	# 3. sorttitle
	if movie.sort_title:
		_add_text_element(root, "sorttitle", movie.sort_title)

	# 4. set
	if movie.movie_set and movie.movie_set.name:
		set_elem = lxml.etree.SubElement(root, "set")
		_add_text_element(set_elem, "name", movie.movie_set.name)

	# 5. rating
	if movie.rating:
		_add_text_element(root, "rating", str(movie.rating))

	# 6. userrating
	if movie.user_rating:
		_add_text_element(root, "userrating", str(movie.user_rating))

	# 7. year
	if movie.year:
		_add_text_element(root, "year", movie.year)

	# 8. top250
	if movie.top250:
		_add_text_element(root, "top250", str(movie.top250))

	# 9. votes
	if movie.votes:
		_add_text_element(root, "votes", str(movie.votes))

	# 10. outline (same as plot)
	if movie.plot:
		_add_text_element(root, "outline", movie.plot)

	# 11. plot
	if movie.plot:
		_add_text_element(root, "plot", movie.plot)

	# 12. tagline
	if movie.tagline:
		_add_text_element(root, "tagline", movie.tagline)

	# 13. runtime
	if movie.runtime:
		_add_text_element(root, "runtime", str(movie.runtime))

	# 14. thumb (poster_url)
	if movie.poster_url:
		_add_text_element(root, "thumb", movie.poster_url)

	# 15. fanart (with thumb child for fanart_url)
	if movie.fanart_url:
		fanart_elem = lxml.etree.SubElement(root, "fanart")
		_add_text_element(fanart_elem, "thumb", movie.fanart_url)

	# 16. mpaa (certification)
	if movie.certification:
		_add_text_element(root, "mpaa", movie.certification)

	# 17. parental_guide (advisory categories and severities)
	if movie.parental_guide:
		pg_elem = lxml.etree.SubElement(root, "parental_guide")
		for category, severity in sorted(movie.parental_guide.items()):
			advisory = lxml.etree.SubElement(pg_elem, "advisory")
			advisory.set("category", category)
			advisory.text = severity

	# 17b. parental_guide_checked (date last checked)
	if movie.parental_guide_checked:
		_add_text_element(
			root, "parental_guide_checked",
			movie.parental_guide_checked,
		)

	# 18. id (imdb_id)
	if movie.imdb_id:
		_add_text_element(root, "id", movie.imdb_id)

	# 18. tmdbid
	if movie.tmdb_id:
		_add_text_element(root, "tmdbid", str(movie.tmdb_id))

	# 19. trailer (one element per URL)
	for trailer_url in movie.trailer:
		_add_text_element(root, "trailer", trailer_url)

	# 20. country
	if movie.country:
		_add_text_element(root, "country", movie.country)

	# 21. premiered (release_date)
	if movie.release_date:
		_add_text_element(root, "premiered", movie.release_date)

	# 22. watched
	watched_str = str(movie.watched).lower()
	_add_text_element(root, "watched", watched_str)

	# 23. playcount
	playcount = "1" if movie.watched else "0"
	_add_text_element(root, "playcount", playcount)

	# 24. genre (one per genre)
	for genre in movie.genres:
		_add_text_element(root, "genre", genre)

	# 25. studio
	if movie.studio:
		_add_text_element(root, "studio", movie.studio)

	# 26. credits (writer)
	if movie.writer:
		_add_text_element(root, "credits", movie.writer)

	# 27. director
	if movie.director:
		_add_text_element(root, "director", movie.director)

	# 28. tag (one per tag)
	for tag in movie.tags:
		_add_text_element(root, "tag", tag)

	# 29. actor (one per actor)
	for actor in movie.actors:
		_add_actor_element(root, "actor", actor)

	# 30. producer (one per producer)
	for producer in movie.producers:
		_add_actor_element(root, "producer", producer)

	# 31. dateadded
	if movie.date_added:
		_add_text_element(root, "dateadded", movie.date_added)

	# 32. lastplayed
	if movie.last_watched:
		_add_text_element(root, "lastplayed", movie.last_watched)

	# 33. languages (spoken_languages)
	if movie.spoken_languages:
		_add_text_element(root, "languages", movie.spoken_languages)

	# 34. fileinfo (stream details from first video media file)
	vf = movie.video_file
	if vf is not None and vf.video_codec:
		fileinfo = lxml.etree.SubElement(root, "fileinfo")
		sd = lxml.etree.SubElement(fileinfo, "streamdetails")
		# video track
		video_elem = lxml.etree.SubElement(sd, "video")
		_add_text_element(video_elem, "codec", vf.video_codec)
		if vf.video_width:
			_add_text_element(
				video_elem, "width", str(vf.video_width)
			)
		if vf.video_height:
			_add_text_element(
				video_elem, "height", str(vf.video_height)
			)
		if vf.aspect_ratio:
			_add_text_element(
				video_elem, "aspect", f"{vf.aspect_ratio:.3f}"
			)
		if vf.duration:
			_add_text_element(
				video_elem, "durationinseconds", str(vf.duration)
			)
		# audio track
		if vf.audio_codec:
			audio_elem = lxml.etree.SubElement(sd, "audio")
			_add_text_element(audio_elem, "codec", vf.audio_codec)
			if vf.audio_channels:
				_add_text_element(
					audio_elem, "channels", vf.audio_channels
				)

	# 35. unknown_elements (re-emit preserved elements)
	for elem in movie.unknown_elements:
		# deep copy to avoid modifying the original tree
		root.append(copy.deepcopy(elem))

	# pretty-print with tab indentation
	lxml.etree.indent(root, space="\t")

	# build the element tree and write to file
	tree = lxml.etree.ElementTree(root)
	tree.write(
		nfo_path,
		xml_declaration=True,
		encoding="utf-8",
		pretty_print=True,
	)
