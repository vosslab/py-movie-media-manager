"""File movement operations for movie file renaming."""

# Standard Library
import os
import shutil

# local repo modules
import moviemanager.core.constants
import moviemanager.core.models.movie


#============================================
def move_file(source: str, dest: str) -> None:
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
def update_movie_paths(
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
