"""Directory scanner for discovering movie files and metadata."""

# Standard Library
import os
import time

# local repo modules
import moviemanager.core.constants
import moviemanager.core.models.media_file
import moviemanager.core.models.movie
import moviemanager.core.nfo.reader
import moviemanager.core.utils


#============================================
def detect_artwork_files(dir_path: str, filenames: list = None) -> dict:
	"""Scan a directory for artwork files matching known artwork filenames.

	Checks for each artwork type defined in ARTWORK_FILENAMES and returns
	a mapping of artwork type to the first matching file path found.
	When filenames is provided, uses set membership instead of stat calls.

	Args:
		dir_path: Path to the directory to scan for artwork.
		filenames: Optional list of filenames from os.walk() to avoid stat calls.

	Returns:
		Dict mapping artwork type string to the full file path found.
	"""
	# build a lowercase set for fast membership checks
	if filenames is not None:
		filename_set = set(f.lower() for f in filenames)
	else:
		filename_set = None
	artwork = {}
	for art_type, art_names in moviemanager.core.constants.ARTWORK_FILENAMES.items():
		for fname in art_names:
			if filename_set is not None:
				# check set membership instead of stat() call
				if fname.lower() in filename_set:
					artwork[art_type] = os.path.join(dir_path, fname)
					break
			else:
				full_path = os.path.join(dir_path, fname)
				if os.path.isfile(full_path):
					artwork[art_type] = full_path
					break
	return artwork


#============================================
def scan_directory(
	root_path: str, progress_callback=None, movie_callback=None,
) -> list:
	"""Recursively scan a directory tree for movie files.

	Walks root_path, skipping hidden directories and directories listed
	in SKIP_DIRS. For each directory containing video files, creates
	Movie objects with associated MediaFile entries and NFO metadata.

	Args:
		root_path: Root directory path to begin scanning.
		progress_callback: Optional callable(current, message) for progress.
		movie_callback: Optional callable(movie) for incremental delivery.

	Returns:
		List of Movie objects discovered during the scan.
	"""
	movies = []
	dirs_processed = 0
	scan_start = time.monotonic()

	for dirpath, dirnames, filenames in os.walk(root_path):
		dirs_processed += 1
		if progress_callback:
			# report progress with directory count
			rel_path = os.path.relpath(dirpath, root_path)
			progress_callback(
				dirs_processed,
				f"Scanning: {rel_path}"
			)
		# skip hidden directories and directories in SKIP_DIRS
		# modify dirnames in-place to prevent os.walk from descending
		dirnames[:] = [
			d for d in dirnames
			if not d.startswith(".")
			and d not in moviemanager.core.constants.SKIP_DIRS
		]

		# find video files in this directory, skipping trailer files
		# the app saves trailers as "trailer.mp4", so match that exact stem
		video_files = [
			f for f in filenames
			if moviemanager.core.utils.is_video_file(f)
			and os.path.splitext(f)[0].lower() != "trailer"
		]
		if not video_files:
			continue

		# determine if this is a multi-movie directory
		# multi-movie: multiple video files without per-video NFO files
		nfo_files_in_dir = [f for f in filenames if f.lower().endswith(".nfo")]
		# build a set of NFO basenames for matching
		nfo_basenames = set()
		for nfo_f in nfo_files_in_dir:
			base, _ = os.path.splitext(nfo_f)
			nfo_basenames.add(base.lower())

		# count how many videos have a matching NFO (same basename)
		matched_nfo_count = 0
		for vf in video_files:
			vbase, _ = os.path.splitext(vf)
			if vbase.lower() in nfo_basenames:
				matched_nfo_count += 1

		# multi-movie if multiple videos and not all have matching NFOs
		is_multi = len(video_files) > 1

		# detect artwork files using os.walk filenames to avoid stat calls
		artwork = detect_artwork_files(dirpath, filenames=filenames)

		for vf in video_files:
			# create a Movie object
			movie = moviemanager.core.models.movie.Movie()
			movie.path = dirpath
			movie.multi_movie_dir = is_multi

			# create a MediaFile for the video
			video_path = os.path.join(dirpath, vf)
			media_file = moviemanager.core.models.media_file.MediaFile(
				path=video_path,
				filename=vf,
				filesize=os.path.getsize(video_path),
				file_type=moviemanager.core.constants.MediaFileType.VIDEO,
			)
			movie.media_files.append(media_file)

			# look for a matching NFO file
			vbase, _ = os.path.splitext(vf)
			nfo_found = False

			# check for NFO with same basename as video
			for nfo_f in nfo_files_in_dir:
				nfo_base, _ = os.path.splitext(nfo_f)
				if nfo_base.lower() == vbase.lower():
					nfo_path = os.path.join(dirpath, nfo_f)
					nfo_movie = moviemanager.core.nfo.reader.read_nfo(nfo_path)
					# merge NFO metadata into the movie
					_merge_nfo_into_movie(movie, nfo_movie, nfo_path)
					nfo_found = True
					break

			# in single-movie dirs, also check for movie.nfo
			if not nfo_found and not is_multi:
				movie_nfo_path = os.path.join(dirpath, "movie.nfo")
				if os.path.isfile(movie_nfo_path):
					nfo_movie = moviemanager.core.nfo.reader.read_nfo(
						movie_nfo_path
					)
					_merge_nfo_into_movie(movie, nfo_movie, movie_nfo_path)
					nfo_found = True

			# if no NFO, parse title and year from filename
			if not nfo_found:
				title, year = moviemanager.core.utils.parse_title_year(vf)
				movie.title = title
				movie.year = year

			# set artwork paths on the movie
			if "poster" in artwork:
				movie.poster_url = artwork["poster"]
			if "fanart" in artwork:
				movie.fanart_url = artwork["fanart"]
			if "banner" in artwork:
				movie.banner_url = artwork["banner"]
			if "clearart" in artwork:
				movie.clearart_url = artwork["clearart"]
			if "logo" in artwork:
				movie.logo_url = artwork["logo"]
			if "discart" in artwork:
				movie.discart_url = artwork["discart"]
			if "thumb" in artwork:
				movie.thumb_url = artwork["thumb"]

			movies.append(movie)
			# notify callback for incremental delivery
			if movie_callback:
				movie_callback(movie)

	# summary timing for the full directory walk
	scan_ms = (time.monotonic() - scan_start) * 1000
	print(
		f"[scan] {len(movies)} movies in {dirs_processed} dirs, "
		f"{scan_ms:.0f}ms"
	)
	return movies


#============================================
def _merge_nfo_into_movie(
	movie: moviemanager.core.models.movie.Movie,
	nfo_movie: moviemanager.core.models.movie.Movie,
	nfo_path: str,
) -> None:
	"""Merge metadata from an NFO-parsed movie into a target movie.

	Copies all non-default scalar fields from nfo_movie into movie,
	and extends list fields. Sets the nfo_path on the target movie.

	Args:
		movie: Target Movie to merge data into.
		nfo_movie: Movie parsed from NFO file.
		nfo_path: Path to the NFO file.
	"""
	movie.nfo_path = nfo_path
	# copy scalar fields if they have non-default values
	if nfo_movie.title:
		movie.title = nfo_movie.title
	if nfo_movie.original_title:
		movie.original_title = nfo_movie.original_title
	if nfo_movie.sort_title:
		movie.sort_title = nfo_movie.sort_title
	if nfo_movie.year:
		movie.year = nfo_movie.year
	if nfo_movie.imdb_id:
		movie.imdb_id = nfo_movie.imdb_id
	if nfo_movie.tmdb_id:
		movie.tmdb_id = nfo_movie.tmdb_id
	if nfo_movie.tagline:
		movie.tagline = nfo_movie.tagline
	if nfo_movie.plot:
		movie.plot = nfo_movie.plot
	if nfo_movie.runtime:
		movie.runtime = nfo_movie.runtime
	if nfo_movie.certification:
		movie.certification = nfo_movie.certification
	if nfo_movie.country:
		movie.country = nfo_movie.country
	if nfo_movie.spoken_languages:
		movie.spoken_languages = nfo_movie.spoken_languages
	if nfo_movie.release_date:
		movie.release_date = nfo_movie.release_date
	if nfo_movie.rating:
		movie.rating = nfo_movie.rating
	if nfo_movie.votes:
		movie.votes = nfo_movie.votes
	if nfo_movie.director:
		movie.director = nfo_movie.director
	if nfo_movie.writer:
		movie.writer = nfo_movie.writer
	if nfo_movie.studio:
		movie.studio = nfo_movie.studio
	if nfo_movie.media_source:
		movie.media_source = nfo_movie.media_source
	# extend list fields
	if nfo_movie.genres:
		movie.genres.extend(nfo_movie.genres)
	if nfo_movie.tags:
		movie.tags.extend(nfo_movie.tags)
	if nfo_movie.actors:
		movie.actors.extend(nfo_movie.actors)
	if nfo_movie.producers:
		movie.producers.extend(nfo_movie.producers)
	# URLs
	if nfo_movie.poster_url:
		movie.poster_url = nfo_movie.poster_url
	if nfo_movie.fanart_url:
		movie.fanart_url = nfo_movie.fanart_url
	# movie set
	if nfo_movie.movie_set:
		movie.movie_set = nfo_movie.movie_set
	# parental guide
	if nfo_movie.parental_guide:
		movie.parental_guide.update(nfo_movie.parental_guide)
	# state
	if nfo_movie.watched:
		movie.watched = nfo_movie.watched
	if nfo_movie.date_added:
		movie.date_added = nfo_movie.date_added
	# populate video MediaFile from cached fileinfo if available
	fileinfo = getattr(nfo_movie, "_fileinfo", None)
	if fileinfo:
		vf = movie.video_file
		if vf is not None and not vf.video_codec:
			vf.video_codec = fileinfo.get("video_codec", "")
			vf.video_width = fileinfo.get("video_width", 0)
			vf.video_height = fileinfo.get("video_height", 0)
			vf.aspect_ratio = fileinfo.get("aspect_ratio", 0.0)
			vf.duration = fileinfo.get("duration_seconds", 0)
			vf.audio_codec = fileinfo.get("audio_codec", "")
			vf.audio_channels = fileinfo.get("audio_channels", "")
	# mark as scraped if NFO provided external IDs
	if movie.imdb_id or movie.tmdb_id:
		movie.scraped = True
