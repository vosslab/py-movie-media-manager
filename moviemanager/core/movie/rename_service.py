"""Movie file renaming service using template engine and file mover."""

# Standard Library
import os

# local repo modules
import moviemanager.core.constants
import moviemanager.core.file.collector
import moviemanager.core.file.mover
import moviemanager.core.models.movie
import moviemanager.core.movie.template_engine


#============================================
def _collect_artwork_files(directory: str, video_basename: str = "") -> list:
	"""Find artwork files in a movie directory.

	Delegates to moviemanager.core.file.collector.collect_artwork_file_paths().

	Args:
		directory: path to the movie directory.
		video_basename: video filename without extension, used to
			match prefixed artwork (e.g. 'Movie.Name').

	Returns:
		List of full paths to artwork files that exist on disk.
	"""
	artwork_paths = moviemanager.core.file.collector.collect_artwork_file_paths(
		directory, video_basename=video_basename,
	)
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
	target_dir = moviemanager.core.movie.template_engine.expand_template(
		path_template, movie,
		spaces_to_underscores=spaces_to_underscores,
	)
	target_basename = moviemanager.core.movie.template_engine.expand_template(
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
	for sub_path in moviemanager.core.file.collector.collect_subtitle_files(
		movie.path
	):
		sub_name = os.path.basename(sub_path)
		sub_dest = os.path.join(dest_dir, sub_name)
		rename_pairs.append((sub_path, sub_dest))

	# collect trailer files from the movie directory
	for trailer_path in moviemanager.core.file.collector.collect_trailer_files(
		movie.path
	):
		trailer_name = os.path.basename(trailer_path)
		trailer_dest = os.path.join(dest_dir, trailer_name)
		rename_pairs.append((trailer_path, trailer_dest))

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
			moviemanager.core.file.mover.move_file(source, dest)
		# update the movie object paths
		moviemanager.core.file.mover.update_movie_paths(
			movie, dest_dir, target_basename, rename_pairs,
		)
		# remove old empty directory after move
		if old_dir != dest_dir and os.path.isdir(old_dir):
			remaining = os.listdir(old_dir)
			if not remaining:
				os.rmdir(old_dir)

	return rename_pairs
