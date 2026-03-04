"""Directory-level file collection for movie media files."""

# Standard Library
import os

# local repo modules
import moviemanager.core.constants
import moviemanager.core.file.classifier


#============================================
def collect_artwork_files(
	dir_path: str, filenames: list = None, video_basename: str = "",
) -> dict:
	"""Scan a directory for artwork files matching known artwork filenames.

	Supports two use cases:
	- Scanner: pass filenames from os.walk() to avoid stat calls.
	- Renamer: pass video_basename to find prefixed artwork like
	  'Movie.Name-poster.jpg' in multi-movie directories.

	When filenames is provided, uses set membership instead of stat calls.
	When video_basename is provided, also checks for prefixed artwork.

	Args:
		dir_path: path to the directory to scan for artwork.
		filenames: optional list of filenames from os.walk() to avoid stat calls.
		video_basename: video filename without extension, used to
			match prefixed artwork (e.g. 'Movie.Name').

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
def collect_artwork_file_paths(
	directory: str, video_basename: str = "",
) -> list:
	"""Find artwork file paths in a movie directory.

	Scans the directory for filenames that match known artwork
	names from ARTWORK_FILENAMES. Also finds prefixed artwork
	files like 'Movie.Name-poster.jpg' in multi-movie directories.

	This is the renamer use case, returning a flat list of paths.

	Args:
		directory: path to the movie directory.
		video_basename: video filename without extension, used to
			match prefixed artwork (e.g. 'Movie.Name').

	Returns:
		Sorted list of full paths to artwork files that exist on disk.
	"""
	# flatten all known artwork filenames into a set
	known_names = set()
	for names in moviemanager.core.constants.ARTWORK_FILENAMES.values():
		for name in names:
			known_names.add(name.lower())

	if not os.path.isdir(directory):
		return []

	collected = set()
	# first pass: exact match for known artwork filenames
	for entry in os.listdir(directory):
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
def collect_subtitle_files(dir_path: str) -> list:
	"""Collect subtitle files from a directory.

	Args:
		dir_path: path to the directory to scan.

	Returns:
		Sorted list of full paths to subtitle files found.
	"""
	if not os.path.isdir(dir_path):
		return []
	results = []
	for entry in os.listdir(dir_path):
		if moviemanager.core.file.classifier.is_subtitle_file(entry):
			results.append(os.path.join(dir_path, entry))
	results.sort()
	return results


#============================================
def collect_trailer_files(dir_path: str) -> list:
	"""Collect trailer files from a directory.

	Args:
		dir_path: path to the directory to scan.

	Returns:
		Sorted list of full paths to trailer files found.
	"""
	if not os.path.isdir(dir_path):
		return []
	results = []
	for entry in os.listdir(dir_path):
		if moviemanager.core.file.classifier.is_trailer_file(entry):
			results.append(os.path.join(dir_path, entry))
	results.sort()
	return results


#============================================
def collect_nfo_files(dir_path: str) -> list:
	"""Collect NFO files from a directory.

	Args:
		dir_path: path to the directory to scan.

	Returns:
		Sorted list of full paths to NFO files found.
	"""
	if not os.path.isdir(dir_path):
		return []
	results = []
	for entry in os.listdir(dir_path):
		if moviemanager.core.file.classifier.is_nfo_file(entry):
			results.append(os.path.join(dir_path, entry))
	results.sort()
	return results


#============================================
def collect_all_movie_files(dir_path: str, video_basename: str = "") -> dict:
	"""Collect all movie-related files from a directory.

	Gathers artwork, subtitles, trailers, and NFO files into a
	single dict keyed by file category.

	Args:
		dir_path: path to the directory to scan.
		video_basename: video filename without extension for prefixed artwork.

	Returns:
		Dict with keys 'artwork', 'subtitles', 'trailers', 'nfo_files'
		mapping to their respective file lists.
	"""
	result = {
		"artwork": collect_artwork_files(dir_path, video_basename=video_basename),
		"subtitles": collect_subtitle_files(dir_path),
		"trailers": collect_trailer_files(dir_path),
		"nfo_files": collect_nfo_files(dir_path),
	}
	return result
