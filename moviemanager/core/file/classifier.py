"""Centralized file type detection for movie media files."""

# Standard Library
import os

# local repo modules
import moviemanager.core.constants


#============================================
def classify_file(filename: str) -> moviemanager.core.constants.MediaFileType:
	"""Classify a filename into a MediaFileType based on its extension and name.

	Examines the file extension and name patterns to determine what type
	of media file this is. Trailers are detected by checking for 'trailer'
	in the filename stem combined with a video extension.

	Args:
		filename: filename or path to classify.

	Returns:
		The MediaFileType enum value for the file.
	"""
	_, ext = os.path.splitext(filename)
	ext_lower = ext.lower()
	basename_lower = os.path.splitext(os.path.basename(filename))[0].lower()

	# check NFO first (simple extension match)
	if ext_lower == ".nfo":
		return moviemanager.core.constants.MediaFileType.NFO

	# check subtitle extensions
	if ext_lower in moviemanager.core.constants.SUBTITLE_EXTENSIONS:
		return moviemanager.core.constants.MediaFileType.SUBTITLE

	# check audio extensions
	if ext_lower in moviemanager.core.constants.AUDIO_EXTENSIONS:
		return moviemanager.core.constants.MediaFileType.AUDIO

	# check video extensions (trailer detection before generic video)
	if ext_lower in moviemanager.core.constants.VIDEO_EXTENSIONS:
		# trailer: filename stem contains 'trailer'
		if "trailer" in basename_lower:
			return moviemanager.core.constants.MediaFileType.TRAILER
		# sample: filename stem is exactly 'sample' or starts with 'sample'
		if basename_lower == "sample" or basename_lower.startswith("sample"):
			return moviemanager.core.constants.MediaFileType.SAMPLE
		return moviemanager.core.constants.MediaFileType.VIDEO

	# check image extensions for artwork types
	if ext_lower in moviemanager.core.constants.IMAGE_EXTENSIONS:
		# check for specific artwork types by filename
		if _is_artwork_name(filename):
			return _classify_artwork(filename)
		return moviemanager.core.constants.MediaFileType.GRAPHIC

	# text files
	if ext_lower == ".txt":
		return moviemanager.core.constants.MediaFileType.TEXT

	return moviemanager.core.constants.MediaFileType.UNKNOWN


#============================================
def _is_artwork_name(filename: str) -> bool:
	"""Check if a filename matches any known artwork filename pattern.

	Args:
		filename: filename to check.

	Returns:
		True if the basename matches a known artwork filename.
	"""
	basename_lower = os.path.basename(filename).lower()
	for art_names in moviemanager.core.constants.ARTWORK_FILENAMES.values():
		for name in art_names:
			if basename_lower == name.lower():
				return True
	return False


#============================================
def _classify_artwork(filename: str) -> moviemanager.core.constants.MediaFileType:
	"""Classify an artwork file into its specific artwork type.

	Args:
		filename: filename known to be an artwork file.

	Returns:
		The specific artwork MediaFileType (POSTER, FANART, etc.).
	"""
	basename_lower = os.path.basename(filename).lower()
	# map artwork type strings to MediaFileType enum values
	type_map = {
		"poster": moviemanager.core.constants.MediaFileType.POSTER,
		"fanart": moviemanager.core.constants.MediaFileType.FANART,
		"banner": moviemanager.core.constants.MediaFileType.BANNER,
		"clearart": moviemanager.core.constants.MediaFileType.CLEARART,
		"logo": moviemanager.core.constants.MediaFileType.LOGO,
		"discart": moviemanager.core.constants.MediaFileType.DISCART,
		"thumb": moviemanager.core.constants.MediaFileType.THUMB,
	}
	for art_type, art_names in moviemanager.core.constants.ARTWORK_FILENAMES.items():
		for name in art_names:
			if basename_lower == name.lower():
				return type_map.get(
					art_type,
					moviemanager.core.constants.MediaFileType.GRAPHIC,
				)
	return moviemanager.core.constants.MediaFileType.GRAPHIC


#============================================
def is_video_file(filename: str) -> bool:
	"""Check if a filename has a recognized video extension.

	Args:
		filename: file path or filename to check.

	Returns:
		True if the extension is a known video format.
	"""
	_, ext = os.path.splitext(filename)
	result = ext.lower() in moviemanager.core.constants.VIDEO_EXTENSIONS
	return result


#============================================
def is_subtitle_file(filename: str) -> bool:
	"""Check if a filename has a recognized subtitle extension.

	Args:
		filename: file path or filename to check.

	Returns:
		True if the extension is a known subtitle format.
	"""
	_, ext = os.path.splitext(filename)
	result = ext.lower() in moviemanager.core.constants.SUBTITLE_EXTENSIONS
	return result


#============================================
def is_artwork_file(filename: str) -> bool:
	"""Check if a filename is a recognized image/artwork format.

	Args:
		filename: file path or filename to check.

	Returns:
		True if the extension is a known image format.
	"""
	_, ext = os.path.splitext(filename)
	result = ext.lower() in moviemanager.core.constants.IMAGE_EXTENSIONS
	return result


#============================================
def is_trailer_file(filename: str) -> bool:
	"""Check if a filename is a trailer (video extension + 'trailer' in name).

	Args:
		filename: file path or filename to check.

	Returns:
		True if the file is a trailer.
	"""
	_, ext = os.path.splitext(filename)
	if ext.lower() not in moviemanager.core.constants.VIDEO_EXTENSIONS:
		return False
	basename_lower = os.path.splitext(os.path.basename(filename))[0].lower()
	result = "trailer" in basename_lower
	return result


#============================================
def is_nfo_file(filename: str) -> bool:
	"""Check if a filename has an .nfo extension.

	Args:
		filename: file path or filename to check.

	Returns:
		True if the extension is .nfo.
	"""
	_, ext = os.path.splitext(filename)
	result = ext.lower() == ".nfo"
	return result
