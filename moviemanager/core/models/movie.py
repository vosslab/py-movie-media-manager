"""Complete movie metadata model."""

# Standard Library
import os
import dataclasses

# local repo modules
import moviemanager.core.constants
import moviemanager.core.file.classifier
import moviemanager.core.file.collector
import moviemanager.core.models.media_file
import moviemanager.core.models.movie_set


#============================================
@dataclasses.dataclass
class Movie:
	"""Complete movie metadata model.

	Ported from tinyMediaManager Movie.java and MediaEntity.java.
	Holds identity, external IDs, metadata, ratings, credits,
	classification, artwork URLs, paths, state, and associated
	media files.

	Attributes:
		title: Primary display title.
		original_title: Original language title.
		sort_title: Title used for alphabetical sorting.
		year: Release year as a string.
		imdb_id: IMDb identifier string.
		tmdb_id: The Movie Database numeric identifier.
		ids: Mapping of provider name to external ID.
		tagline: Short promotional tagline.
		plot: Full plot summary.
		runtime: Runtime in minutes.
		certification: Content rating (e.g. PG-13, R).
		country: Country of origin.
		spoken_languages: Comma-separated language list.
		release_date: Release date string.
		rating: Average rating score.
		votes: Number of votes for the rating.
		top250: Position in a top-250 list, or 0.
		user_rating: User-assigned personal rating.
		director: Director name(s).
		writer: Writer name(s).
		studio: Production studio name.
		actors: List of cast member dicts.
		producers: List of producer names or dicts.
		genres: List of genre strings.
		tags: List of user-defined tag strings.
		media_source: Physical source (BluRay, DVD, etc.).
		video_3d: Whether the movie is in 3D.
		poster_url: URL to the poster image.
		fanart_url: URL to the fanart image.
		banner_url: URL to the banner image.
		clearart_url: URL to the clearart image.
		logo_url: URL to the logo image.
		discart_url: URL to the disc art image.
		thumb_url: URL to the thumbnail image.
		extra_thumbs: List of extra thumbnail URLs.
		extra_fanarts: List of extra fanart URLs.
		path: Directory path containing the movie files.
		nfo_path: Path to the NFO metadata file.
		scraped: Whether metadata has been scraped.
		watched: Whether the movie has been watched.
		date_added: Date the movie was added to the library.
		last_watched: Date the movie was last watched.
		multi_movie_dir: Whether the directory has multiple movies.
		is_disc: Whether the source is a disc folder structure.
		trailer: List of trailer URLs or paths.
		media_files: List of MediaFile instances.
		movie_set: Optional MovieSet this movie belongs to.
		unknown_elements: Preserved unknown NFO XML elements.
	"""

	# identity
	title: str = ""
	original_title: str = ""
	sort_title: str = ""
	year: str = ""
	# external IDs
	imdb_id: str = ""
	tmdb_id: int = 0
	ids: dict = dataclasses.field(default_factory=dict)
	# metadata
	tagline: str = ""
	plot: str = ""
	runtime: int = 0
	certification: str = ""
	country: str = ""
	spoken_languages: str = ""
	release_date: str = ""
	# ratings
	rating: float = 0.0
	votes: int = 0
	top250: int = 0
	user_rating: float = 0.0
	# credits
	director: str = ""
	writer: str = ""
	studio: str = ""
	actors: list = dataclasses.field(default_factory=list)
	producers: list = dataclasses.field(default_factory=list)
	# classification
	genres: list = dataclasses.field(default_factory=list)
	tags: list = dataclasses.field(default_factory=list)
	# parental guide severity levels by category
	parental_guide: dict = dataclasses.field(default_factory=dict)
	# ISO date when parental guide was last checked (empty = never)
	parental_guide_checked: str = ""
	# media
	media_source: str = ""
	video_3d: bool = False
	# artwork URLs
	poster_url: str = ""
	fanart_url: str = ""
	banner_url: str = ""
	clearart_url: str = ""
	logo_url: str = ""
	discart_url: str = ""
	thumb_url: str = ""
	extra_thumbs: list = dataclasses.field(default_factory=list)
	extra_fanarts: list = dataclasses.field(default_factory=list)
	# paths
	path: str = ""
	nfo_path: str = ""
	# state
	scraped: bool = False
	watched: bool = False
	date_added: str = ""
	last_watched: str = ""
	multi_movie_dir: bool = False
	is_disc: bool = False
	# trailers
	trailer_url: str = ""
	trailer: list = dataclasses.field(default_factory=list)
	# media files
	media_files: list = dataclasses.field(default_factory=list)
	# movie set
	movie_set: moviemanager.core.models.movie_set.MovieSet | None = None
	# preserve unknown NFO elements for round-trip
	unknown_elements: list = dataclasses.field(default_factory=list)
	# cached artwork types and trailer detection from scanner (avoids re-stat)
	_artwork_types_cache: set | None = dataclasses.field(
		default=None, repr=False)
	_has_trailer_cache: bool | None = dataclasses.field(
		default=None, repr=False)

	#============================================
	@property
	def has_data(self) -> bool:
		"""Return whether meaningful metadata exists for this movie.

		True when the movie has been scraped via API or has data loaded
		from an NFO file (title plus plot or external ID).

		Returns:
			True if the movie has populated metadata beyond filename parsing.
		"""
		if self.scraped:
			return True
		# check for data loaded from NFO: title alone comes from filename
		# parsing, so require title plus additional metadata fields
		has_ids = bool(self.tmdb_id or self.imdb_id)
		has_plot = bool(self.plot)
		has_extra = has_ids or has_plot
		return bool(self.title and has_extra)

	#============================================
	@property
	def video_file(self) -> moviemanager.core.models.media_file.MediaFile | None:
		"""Return the first media file with VIDEO type, or None.

		Returns:
			The first MediaFile with file_type VIDEO, or None if absent.
		"""
		video_type = moviemanager.core.constants.MediaFileType.VIDEO
		for mf in self.media_files:
			if mf.file_type == video_type:
				return mf
		return None

	#============================================
	@property
	def has_subtitle(self) -> bool:
		"""Return whether any subtitle file exists in the movie directory.

		Returns:
			True if a file with a subtitle extension is found on disk.
		"""
		if not self.path or not os.path.isdir(self.path):
			return False
		for entry in os.listdir(self.path):
			# check file extension against known subtitle extensions
			if moviemanager.core.file.classifier.is_subtitle_file(entry):
				return True
		return False

	#============================================
	@property
	def has_trailer(self) -> bool:
		"""Return whether a trailer video file exists in the movie directory.

		Checks for any file with 'trailer' in the name and a video extension.
		Uses cached result from scanner when available.

		Returns:
			True if a trailer file is found on disk.
		"""
		# use cached result from scanner when available
		if self._has_trailer_cache is not None:
			return self._has_trailer_cache
		if not self.path or not os.path.isdir(self.path):
			return False
		for entry in os.listdir(self.path):
			# match files with 'trailer' in the name and a video extension
			if moviemanager.core.file.classifier.is_trailer_file(entry):
				return True
		return False

	#============================================
	@property
	def has_nfo(self) -> bool:
		"""Return whether this movie has an NFO file path set.

		Returns:
			True if nfo_path is non-empty.
		"""
		result = bool(self.nfo_path)
		return result

	#============================================
	@property
	def is_organized(self) -> bool:
		"""Return whether movie is in its own dedicated folder.

		True when the movie is the only video in its directory and the
		folder name matches the expanded path template exactly,
		indicating it was placed into a dedicated folder by the
		organize step.

		Returns:
			True if the movie directory is a dedicated movie folder.
		"""
		result = self.check_organized()
		return result

	#============================================
	def check_organized(self, settings=None) -> bool:
		"""Check whether movie folder matches the expected path template.

		When settings is provided, skips the load_settings() disk read.
		This allows batch callers to load settings once and pass it in.

		Args:
			settings: Optional pre-loaded Settings object. Loaded from
				disk when None.

		Returns:
			True if the movie directory is a dedicated movie folder.
		"""
		if not self.path or self.multi_movie_dir:
			return False
		if not self.title:
			return False
		# lazy import to avoid circular dependency (template_engine imports movie)
		import moviemanager.core.movie.template_engine
		if settings is None:
			import moviemanager.core.settings
			settings = moviemanager.core.settings.load_settings()
		# expand the template to get the expected folder name
		expected = moviemanager.core.movie.template_engine.expand_template(
			settings.path_template, self,
			spaces_to_underscores=settings.spaces_to_underscores,
		)
		# compare against the actual folder name
		folder_name = os.path.basename(self.path)
		is_match = (folder_name == expected)
		return is_match

	#============================================
	@property
	def has_poster(self) -> bool:
		"""Return whether poster artwork exists in the movie directory.

		Uses cached result from scanner when available.

		Returns:
			True if poster artwork is found on disk.
		"""
		if self._artwork_types_cache is not None:
			return "poster" in self._artwork_types_cache
		if not self.path:
			return False
		poster_path = os.path.join(self.path, "poster.jpg")
		return os.path.isfile(poster_path)

	#============================================
	@property
	def has_fanart(self) -> bool:
		"""Return whether fanart artwork exists in the movie directory.

		Uses cached result from scanner when available.

		Returns:
			True if fanart artwork is found on disk.
		"""
		if self._artwork_types_cache is not None:
			return "fanart" in self._artwork_types_cache
		if not self.path:
			return False
		fanart_path = os.path.join(self.path, "fanart.jpg")
		return os.path.isfile(fanart_path)

	#============================================
	@property
	def artwork_types_on_disk(self) -> set:
		"""Return set of artwork type names found on disk.

		Uses cached result from scanner when available,
		falls back to collector scan.

		Returns:
			Set of artwork type strings present on disk.
		"""
		if self._artwork_types_cache is not None:
			return set(self._artwork_types_cache)
		if not self.path or not os.path.isdir(self.path):
			return set()
		# fallback: check disk using collector
		artwork = moviemanager.core.file.collector.collect_artwork_files(
			self.path,
		)
		return set(artwork.keys())
