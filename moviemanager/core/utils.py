"""Utility functions for filename parsing and validation."""

# Standard Library
import os
import re
import datetime

# local repo modules
import moviemanager.core.constants

# cached lowercase stopwords set for fast lookup
STOPWORDS_LOWER = frozenset(
	w.lower() for w in moviemanager.core.constants.STOPWORDS
)


#============================================
def is_video_file(path: str) -> bool:
	"""Check if a file path has a recognized video extension.

	Args:
		path: file path or filename to check.

	Returns:
		True if the extension is a known video format.
	"""
	# extract the file extension and compare lowercase
	_, ext = os.path.splitext(path)
	result = ext.lower() in moviemanager.core.constants.VIDEO_EXTENSIONS
	return result


#============================================
def parse_title_year(filename: str) -> tuple:
	"""Extract movie title and year from a media filename.

	Ported from Java ParserUtils.detectCleanMovienameAndYear().

	Args:
		filename: media filename (with or without path).

	Returns:
		Tuple of (title, year) where year is a string or empty string.
	"""
	# strip file extension
	name = re.sub(r"\.\w{2,4}$", "", filename)
	# split on delimiters: brackets, parens, underscore, dot, space
	# preserve hyphens between word characters (e.g. Wall-E)
	tokens = re.split(r"[\[\]()_.\s]+", name)
	# remove empty tokens
	tokens = [t for t in tokens if t]

	# use module-level cached stopwords set
	stopwords_lower = STOPWORDS_LOWER

	# imdb id pattern
	imdb_pattern = re.compile(r"^tt\d{7,}$", re.IGNORECASE)

	# compute the current year ceiling for plausible year check
	max_year = datetime.datetime.now().year + 5

	# mark each token as stopword or not
	is_stopword = []
	for token in tokens:
		token_lower = token.lower()
		# check stopword list or imdb id pattern
		if token_lower in stopwords_lower or imdb_pattern.match(token):
			is_stopword.append(True)
		else:
			is_stopword.append(False)

	# scan backwards for a 4-digit year among non-stopword tokens
	year = ""
	year_index = -1
	for i in range(len(tokens) - 1, -1, -1):
		if is_stopword[i]:
			continue
		if re.match(r"^\d{4}$", tokens[i]):
			candidate = int(tokens[i])
			if 1888 < candidate < max_year:
				year = tokens[i]
				year_index = i
				# mark the year token as a stopword so it acts as a boundary
				is_stopword[i] = True
				break

	# determine the cutoff: use year position if found
	if year_index >= 0:
		cutoff = year_index
	else:
		# find the first stopword position (must be at index >= 2)
		cutoff = len(tokens)
		for i, flag in enumerate(is_stopword):
			if flag and i >= 2:
				cutoff = i
				break

	# also check for a stopword boundary before the year
	if year_index >= 0:
		for i, flag in enumerate(is_stopword):
			if flag and i >= 2 and i < cutoff:
				cutoff = i
				break

	# take all tokens before the cutoff
	title_tokens = tokens[:cutoff]
	# join with spaces to form the title
	title = " ".join(title_tokens)
	return (title, year)


# simple assertion test for parse_title_year
result = parse_title_year("The.Dark.Knight.2008.BluRay.x264.mkv")
assert result == ("The Dark Knight", "2008")


#============================================
def clean_filename(name: str) -> str:
	"""Remove characters unsafe for filesystems from a filename.

	Args:
		name: raw filename string.

	Returns:
		Cleaned filename safe for most filesystems.
	"""
	# remove unsafe characters: / \ : * ? " < > |
	cleaned = re.sub(r'[/\\:*?"<>|]', "", name)
	# collapse multiple spaces to one
	cleaned = re.sub(r" {2,}", " ", cleaned)
	# strip leading/trailing whitespace and dots
	cleaned = cleaned.strip().strip(".")
	return cleaned
