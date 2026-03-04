"""Pure template logic for movie file and path name expansion."""

# Standard Library
import re

# local repo modules
import moviemanager.core.constants
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
		spaces_to_underscores: if True, apply shell_safe_filename to values.

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
	"""Assemble a file template from hardcoded title-year base plus media tokens.

	Uses {title} and {year} joined by the configured separator as the base,
	then appends media tokens (resolution, vcodec, acodec, channels) if their
	corresponding checkboxes are enabled.

	Args:
		settings: Settings dataclass with separator and checkbox fields.

	Returns:
		Assembled template string, e.g. "{title}-{year}-{resolution}-{vcodec}".
	"""
	sep = settings.media_separator
	# hardcoded base: title and year joined by separator
	template = "{title}" + sep + "{year}"
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
