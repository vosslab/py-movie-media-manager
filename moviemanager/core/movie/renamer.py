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
def expand_template(template: str, movie: moviemanager.core.models.movie.Movie) -> str:
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
	}

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
def _collect_artwork_files(directory: str) -> list:
	"""Find artwork files in a movie directory.

	Scans the directory for filenames that match known artwork
	names from ARTWORK_FILENAMES.

	Args:
		directory: path to the movie directory.

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
	for entry in os.listdir(directory):
		if entry.lower() in known_names:
			full_path = os.path.join(directory, entry)
			if os.path.isfile(full_path):
				artwork_paths.append(full_path)
	return artwork_paths


#============================================
def rename_movie(
	movie: moviemanager.core.models.movie.Movie,
	path_template: str,
	file_template: str,
	dry_run: bool = True,
) -> list:
	"""Rename and move movie files according to templates.

	Builds target directory and file names from templates, then
	collects all associated files (video, NFO, artwork) and
	computes rename pairs. When dry_run is False, files are moved
	and the movie object is updated.

	Args:
		movie: Movie dataclass with current file paths.
		path_template: template for the target directory name.
		file_template: template for the target file basename.
		dry_run: if True, compute pairs without moving files.

	Returns:
		List of (source_path, dest_path) tuples for all files.
	"""
	# expand templates for directory and file basename
	target_dir = expand_template(path_template, movie)
	target_basename = expand_template(file_template, movie)

	# determine the parent of the current movie directory
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
	artwork_files = _collect_artwork_files(movie.path)
	for art_path in artwork_files:
		# keep original artwork filename in the new directory
		art_name = os.path.basename(art_path)
		art_dest = os.path.join(dest_dir, art_name)
		rename_pairs.append((art_path, art_dest))

	if not dry_run:
		# create the target directory
		os.makedirs(dest_dir, exist_ok=True)
		# move each file
		for source, dest in rename_pairs:
			_move_file(source, dest)
		# update the movie object paths
		_update_movie_paths(movie, dest_dir, target_basename, rename_pairs)

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
