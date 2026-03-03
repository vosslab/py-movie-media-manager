"""Movie file renaming and template expansion."""

# Standard Library
import os
import re
import shutil

# local repo modules
import moviemanager.core.constants
import moviemanager.core.models.media_file
import moviemanager.core.models.movie
import moviemanager.core.utils


#============================================
def expand_template(
	template: str,
	movie: moviemanager.core.models.movie.Movie,
	spaces_to_underscores: bool = False,
) -> str:
	"""Substitute template tokens with movie field values.

	Supported tokens use curly braces: {title}, {original_title},
	{sort_title}, {year}, {imdb_id}, {tmdb_id}, {certification},
	{genre}, {director}, {rating}, {first_letter}.

	Args:
		template: format string with curly-brace tokens.
		movie: Movie dataclass providing field values.

	Returns:
		Expanded string with unsafe filename characters removed.
	"""
	# determine the first genre or empty string
	first_genre = movie.genres[0] if movie.genres else ""
	# determine first letter of title
	first_letter = movie.title[0].upper() if movie.title else ""

	# find the first video media file for media tokens
	video_type = moviemanager.core.constants.MediaFileType.VIDEO
	video_mf = None
	for mf in movie.media_files:
		if mf.file_type == video_type:
			video_mf = mf
			break

	# extract media token values from the video file
	resolution = video_mf.resolution_label if video_mf else ""
	vcodec = video_mf.video_codec if video_mf else ""
	acodec = video_mf.audio_codec if video_mf else ""
	channels = video_mf.audio_channels if video_mf else ""

	# build the replacement mapping
	token_map = {
		"title": movie.title,
		"original_title": movie.original_title,
		"sort_title": movie.sort_title,
		"year": movie.year,
		"imdb_id": movie.imdb_id,
		"tmdb_id": str(movie.tmdb_id),
		"certification": movie.certification,
		"genre": first_genre,
		"director": movie.director,
		"rating": str(movie.rating),
		"first_letter": first_letter,
		# media tokens
		"resolution": resolution,
		"vcodec": vcodec,
		"codec": vcodec,
		"acodec": acodec,
		"audio": acodec,
		"channels": channels,
	}

	# shell-safe each token value individually before substitution
	# this preserves template separators (hyphens, dots) while cleaning values
	if spaces_to_underscores:
		for token, value in token_map.items():
			token_map[token] = moviemanager.core.utils.shell_safe_filename(value)

	# replace each token in the template
	result = template
	for token, value in token_map.items():
		result = result.replace("{" + token + "}", value)

	# clean unsafe filesystem characters
	result = moviemanager.core.utils.clean_filename(result)
	# remove empty parentheses, brackets, and braces
	result = re.sub(r"\(\s*\)", "", result)
	result = re.sub(r"\[\s*\]", "", result)
	result = re.sub(r"\{\s*\}", "", result)
	# collapse multiple spaces to one
	result = re.sub(r" {2,}", " ", result)
	# strip leading and trailing whitespace
	result = result.strip()
	return result


#============================================
def build_file_template(
	settings: "moviemanager.core.settings.Settings",
) -> str:
	"""Assemble a file template from base template plus enabled media tokens.

	Reads the base file_template from settings and appends media tokens
	(resolution, vcodec, acodec, channels) if their corresponding
	checkboxes are enabled. Tokens are joined with the configured separator.

	Args:
		settings: Settings dataclass with template and checkbox fields.

	Returns:
		Assembled template string, e.g. "{title}-{year}-{resolution}-{vcodec}".
	"""
	template = settings.file_template
	sep = settings.media_separator
	# append each enabled media token
	token_list = []
	if settings.rename_resolution:
		token_list.append("{resolution}")
	if settings.rename_vcodec:
		token_list.append("{vcodec}")
	if settings.rename_acodec:
		token_list.append("{acodec}")
	if settings.rename_channels:
		token_list.append("{channels}")
	# join tokens with separator and append to base template
	if token_list:
		suffix = sep.join(token_list)
		template = template + sep + suffix
	return template


#============================================
def _collect_artwork_files(directory: str, video_basename: str = "") -> list:
	"""Find artwork files in a movie directory.

	Scans the directory for filenames that match known artwork
	names from ARTWORK_FILENAMES. Also finds prefixed artwork
	files like 'Movie.Name-poster.jpg' in multi-movie directories.

	Args:
		directory: path to the movie directory.
		video_basename: video filename without extension, used to
			match prefixed artwork (e.g. 'Movie.Name').

	Returns:
		List of full paths to artwork files that exist on disk.
	"""
	artwork_paths = []
	# flatten all known artwork filenames into a set
	known_names = set()
	for names in moviemanager.core.constants.ARTWORK_FILENAMES.values():
		for name in names:
			known_names.add(name.lower())

	# check each file in the directory
	if not os.path.isdir(directory):
		return artwork_paths
	collected = set()
	for entry in os.listdir(directory):
		# exact match: poster.jpg, fanart.jpg, etc.
		if entry.lower() in known_names:
			full_path = os.path.join(directory, entry)
			if os.path.isfile(full_path):
				collected.add(full_path)

	# second pass: find prefixed artwork like Movie.Name-poster.jpg
	if video_basename:
		prefix_lower = video_basename.lower()
		for entry in os.listdir(directory):
			entry_lower = entry.lower()
			# check for video_basename followed by separator (- or .)
			for sep in ("-", "."):
				prefix_with_sep = prefix_lower + sep
				if not entry_lower.startswith(prefix_with_sep):
					continue
				# extract the suffix after the prefix+separator
				suffix = entry_lower[len(prefix_with_sep):]
				if suffix in known_names:
					full_path = os.path.join(directory, entry)
					if os.path.isfile(full_path):
						collected.add(full_path)

	artwork_paths = sorted(collected)
	return artwork_paths


#============================================
def rename_movie(
	movie: moviemanager.core.models.movie.Movie,
	path_template: str,
	file_template: str,
	dry_run: bool = True,
	spaces_to_underscores: bool = False,
) -> list:
	"""Rename and move movie files according to templates.

	Builds target directory and file names from templates, then
	collects all associated files (video, NFO, artwork, subtitles,
	trailers) and computes rename pairs. When dry_run is False,
	files are moved and the movie object is updated.

	Args:
		movie: Movie dataclass with current file paths.
		path_template: template for the target directory name.
		file_template: template for the target file basename.
		dry_run: if True, compute pairs without moving files.
		spaces_to_underscores: if True, replace spaces with underscores.

	Returns:
		List of (source_path, dest_path) tuples for all files.
	"""
	# expand templates for directory and file basename
	target_dir = expand_template(
		path_template, movie,
		spaces_to_underscores=spaces_to_underscores,
	)
	target_basename = expand_template(
		file_template, movie,
		spaces_to_underscores=spaces_to_underscores,
	)

	# determine where the new subfolder should be created
	# multi-movie dirs: create subfolder inside the shared directory
	# single-movie dirs: create subfolder alongside the current one
	if movie.multi_movie_dir:
		parent_dir = movie.path
	else:
		parent_dir = os.path.dirname(movie.path) if movie.path else ""
	dest_dir = os.path.join(parent_dir, target_dir)

	rename_pairs = []

	# collect video files from media_files list
	video_type = moviemanager.core.constants.MediaFileType.VIDEO
	for mf in movie.media_files:
		if mf.file_type == video_type:
			source = mf.path
			# keep original extension
			_, ext = os.path.splitext(source)
			dest = os.path.join(dest_dir, target_basename + ext)
			rename_pairs.append((source, dest))

	# collect NFO file
	if movie.nfo_path and os.path.isfile(movie.nfo_path):
		# use same basename as video but with .nfo extension
		nfo_dest = os.path.join(dest_dir, target_basename + ".nfo")
		rename_pairs.append((movie.nfo_path, nfo_dest))

	# collect artwork files from the movie directory
	# pass video basename to find prefixed artwork in multi-movie dirs
	video_basename = ""
	if movie.video_file:
		video_basename = os.path.splitext(movie.video_file.filename)[0]
	artwork_files = _collect_artwork_files(movie.path, video_basename)
	for art_path in artwork_files:
		# keep original artwork filename in the new directory
		art_name = os.path.basename(art_path)
		art_dest = os.path.join(dest_dir, art_name)
		rename_pairs.append((art_path, art_dest))

	# collect subtitle files from the movie directory
	subtitle_exts = moviemanager.core.constants.SUBTITLE_EXTENSIONS
	if os.path.isdir(movie.path):
		for entry in os.listdir(movie.path):
			ext = os.path.splitext(entry)[1].lower()
			if ext in subtitle_exts:
				sub_src = os.path.join(movie.path, entry)
				sub_dest = os.path.join(dest_dir, entry)
				rename_pairs.append((sub_src, sub_dest))

	# collect trailer files from the movie directory
	video_exts = moviemanager.core.constants.VIDEO_EXTENSIONS
	if os.path.isdir(movie.path):
		for entry in os.listdir(movie.path):
			name_lower = entry.lower()
			ext = os.path.splitext(entry)[1].lower()
			if "trailer" in name_lower and ext in video_exts:
				trailer_src = os.path.join(movie.path, entry)
				trailer_dest = os.path.join(dest_dir, entry)
				rename_pairs.append((trailer_src, trailer_dest))

	# skip when all source paths equal dest paths (already organized)
	all_same = all(src == dst for src, dst in rename_pairs)
	if all_same:
		return []

	# remember old directory for potential cleanup
	old_dir = movie.path

	if not dry_run:
		# create the target directory
		os.makedirs(dest_dir, exist_ok=True)
		# move each file
		for source, dest in rename_pairs:
			_move_file(source, dest)
		# update the movie object paths
		_update_movie_paths(movie, dest_dir, target_basename, rename_pairs)
		# remove old empty directory after move
		if old_dir != dest_dir and os.path.isdir(old_dir):
			remaining = os.listdir(old_dir)
			if not remaining:
				os.rmdir(old_dir)

	return rename_pairs


#============================================
def _move_file(source: str, dest: str) -> None:
	"""Move a file from source to dest, handling cross-device moves.

	Args:
		source: current file path.
		dest: target file path.
	"""
	try:
		os.rename(source, dest)
	except OSError:
		# cross-device move: fall back to shutil
		shutil.move(source, dest)


#============================================
def _update_movie_paths(
	movie: moviemanager.core.models.movie.Movie,
	dest_dir: str,
	target_basename: str,
	rename_pairs: list,
) -> None:
	"""Update movie object paths after files have been moved.

	Args:
		movie: Movie dataclass to update in place.
		dest_dir: new directory path.
		target_basename: new file basename (no extension).
		rename_pairs: list of (source, dest) tuples that were moved.
	"""
	movie.path = dest_dir
	# movie is now in its own dedicated folder
	movie.multi_movie_dir = False

	# update NFO path if it was moved
	nfo_dest = os.path.join(dest_dir, target_basename + ".nfo")
	if any(dest == nfo_dest for _, dest in rename_pairs):
		movie.nfo_path = nfo_dest

	# update media file paths
	video_type = moviemanager.core.constants.MediaFileType.VIDEO
	for mf in movie.media_files:
		if mf.file_type == video_type:
			_, ext = os.path.splitext(mf.path)
			new_path = os.path.join(dest_dir, target_basename + ext)
			mf.path = new_path
			mf.filename = target_basename + ext
