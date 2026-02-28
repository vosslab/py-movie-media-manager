#!/usr/bin/env python3
"""Dataclasses for scraper layer data exchange."""

# Standard Library
import dataclasses


#============================================
@dataclasses.dataclass
class CastMember:
	"""A person involved in a movie production."""
	name: str = ""
	# character name for actors, job title for crew
	role: str = ""
	thumb_url: str = ""
	tmdb_id: int = 0
	imdb_id: str = ""
	# Acting, Directing, Writing, Production
	department: str = ""


#============================================
@dataclasses.dataclass
class SearchResult:
	"""A single result from a metadata search query."""
	title: str = ""
	original_title: str = ""
	year: str = ""
	tmdb_id: int = 0
	imdb_id: str = ""
	overview: str = ""
	poster_url: str = ""
	# relevance score
	score: float = 0.0


#============================================
@dataclasses.dataclass
class MediaMetadata:
	"""Complete metadata fetched from a scraper provider."""
	title: str = ""
	original_title: str = ""
	year: str = ""
	tagline: str = ""
	plot: str = ""
	runtime: int = 0
	certification: str = ""
	country: str = ""
	spoken_languages: str = ""
	release_date: str = ""
	rating: float = 0.0
	votes: int = 0
	top250: int = 0
	director: str = ""
	writer: str = ""
	studio: str = ""
	genres: list = dataclasses.field(default_factory=list)
	tags: list = dataclasses.field(default_factory=list)
	# list of CastMember
	actors: list = dataclasses.field(default_factory=list)
	producers: list = dataclasses.field(default_factory=list)
	tmdb_id: int = 0
	imdb_id: str = ""
	ids: dict = dataclasses.field(default_factory=dict)
	poster_url: str = ""
	fanart_url: str = ""
	banner_url: str = ""
	clearart_url: str = ""
	logo_url: str = ""
	discart_url: str = ""
	trailer_url: str = ""
	media_source: str = ""
	movie_set_name: str = ""
	movie_set_tmdb_id: int = 0
