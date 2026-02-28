#!/usr/bin/env python3
"""Data model for a named collection of related movies."""

# Standard Library
import dataclasses


#============================================
@dataclasses.dataclass
class MovieSet:
	"""A named collection of related movies.

	Attributes:
		name: Display name for the movie set.
		tmdb_id: The Movie Database identifier.
		overview: Short description of the set.
		poster_url: URL to the set poster image.
		fanart_url: URL to the set fanart image.
	"""

	name: str = ""
	tmdb_id: int = 0
	overview: str = ""
	# artwork URLs
	poster_url: str = ""
	fanart_url: str = ""
