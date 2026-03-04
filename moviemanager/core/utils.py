"""Utility functions for filename parsing and validation."""

# Standard Library
import re
import datetime

# PIP3 modules
import unidecode

# local repo modules
import moviemanager.core.constants
import moviemanager.core.file.classifier

# cached lowercase stopwords set for fast lookup
STOPWORDS_LOWER = frozenset(
	w.lower() for w in moviemanager.core.constants.STOPWORDS
)


#============================================
def is_video_file(path: str) -> bool:
	"""Check if a file path has a recognized video extension.

	Delegates to moviemanager.core.file.classifier.is_video_file().

	Args:
		path: file path or filename to check.

	Returns:
		True if the extension is a known video format.
	"""
	result = moviemanager.core.file.classifier.is_video_file(path)
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
def shell_safe_filename(name: str) -> str:
	"""Make a filename shell-safe using a whitelist approach.

	Transliterates unicode to ASCII, replaces ampersands with 'and',
	removes quotes, and strips any character not in the whitelist
	(alphanumeric, hyphen, dot, underscore, slash).

	Modeled on the rmspaces.py cleanName() function.

	Args:
		name: raw filename string.

	Returns:
		Cleaned filename safe for shell use.
	"""
	# transliterate unicode characters to ASCII equivalents
	result = unidecode.unidecode(name)
	# replace ampersand with the word 'and'
	result = result.replace("&", "and")
	# replace single and double quotes with underscores
	result = result.replace("'", "_")
	result = result.replace('"', "_")
	# replace spaces with underscores
	result = result.replace(" ", "_")
	# replace any character NOT in the whitelist with underscore
	result = re.sub(r"[^-./_ 0-9A-Za-z]", "_", result)
	# clean up triple and double separator patterns
	result = result.replace("_._", ".")
	result = result.replace("._.", "_")
	result = result.replace("-_-", "_")
	result = result.replace("_-_", "-")
	# collapse double dots and double underscores
	result = re.sub(r"\.{2,}", ".", result)
	result = re.sub(r"_{2,}", "_", result)
	# strip leading and trailing underscores, hyphens, and dots
	result = result.strip("_-.")
	return result


# simple assertion tests for shell_safe_filename
assert shell_safe_filename("Fast & Furious") == "Fast_and_Furious"
assert shell_safe_filename("Ocean's Eleven") == "Ocean_s_Eleven"
assert shell_safe_filename("The Matrix (1999)") == "The_Matrix_1999"


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
