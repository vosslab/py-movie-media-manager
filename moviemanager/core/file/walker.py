"""Directory traversal for discovering movie directories."""

# Standard Library
import os
import dataclasses
import collections.abc

# local repo modules
import moviemanager.core.constants
import moviemanager.core.file.classifier


#============================================
@dataclasses.dataclass
class DirEntry:
	"""A directory entry discovered during movie directory walking.

	Attributes:
		path: full path to the directory.
		filenames: all filenames found in the directory.
		video_files: filenames with recognized video extensions
			(excluding trailers).
		nfo_files: filenames with .nfo extension.
	"""
	path: str = ""
	filenames: list = dataclasses.field(default_factory=list)
	video_files: list = dataclasses.field(default_factory=list)
	nfo_files: list = dataclasses.field(default_factory=list)


#============================================
def walk_movie_directories(
	root_path: str, progress_callback=None,
) -> collections.abc.Iterator:
	"""Walk a directory tree and yield DirEntry for dirs with video files.

	Skips hidden directories and directories listed in SKIP_DIRS.
	For each directory containing video files (excluding trailers),
	yields a DirEntry with classified file lists.

	Args:
		root_path: root directory path to begin walking.
		progress_callback: optional callable(current, message) for progress.

	Yields:
		DirEntry for each directory containing video files.
	"""
	dirs_processed = 0
	for dirpath, dirnames, filenames in os.walk(root_path):
		dirs_processed += 1
		if progress_callback:
			# report progress with directory count
			rel_path = os.path.relpath(dirpath, root_path)
			progress_callback(dirs_processed, f"Scanning: {rel_path}")

		# skip hidden directories and directories in SKIP_DIRS
		# modify dirnames in-place to prevent os.walk from descending
		dirnames[:] = [
			d for d in dirnames
			if not d.startswith(".")
			and d not in moviemanager.core.constants.SKIP_DIRS
		]

		# find video files, skipping trailer files
		# the app saves trailers as "trailer.mp4", so match that exact stem
		video_files = [
			f for f in filenames
			if moviemanager.core.file.classifier.is_video_file(f)
			and os.path.splitext(f)[0].lower() != "trailer"
		]
		if not video_files:
			continue

		# collect NFO files in this directory
		nfo_files = [
			f for f in filenames
			if moviemanager.core.file.classifier.is_nfo_file(f)
		]

		entry = DirEntry(
			path=dirpath,
			filenames=filenames,
			video_files=video_files,
			nfo_files=nfo_files,
		)
		yield entry
