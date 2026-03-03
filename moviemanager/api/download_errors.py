"""Categorized download error types for trailer and subtitle downloads."""

# Standard Library
import enum


#============================================
class DownloadCategory(enum.Enum):
	"""Categories of download failures for error reporting."""

	no_url = "No Url"
	no_api_key = "No Api Key"
	no_imdb_id = "No Imdb Id"
	no_results = "No Results"
	network_error = "Network Error"
	api_error = "Api Error"
	download_failed = "Download Failed"
	timeout = "Timeout"
	no_path = "No Path"


#============================================
class DownloadError(Exception):
	"""A download failure with a category for structured reporting.

	Args:
		category: DownloadCategory enum value.
		detail: Optional human-readable detail string.
	"""

	def __init__(self, category: DownloadCategory, detail: str = ""):
		self.category = category
		self.detail = detail
		# build message as "category_value: detail"
		if detail:
			message = f"{category.value}: {detail}"
		else:
			message = category.value
		super().__init__(message)
