"""Trailer download service using pluggable trailer providers."""

# Standard Library
import os
import subprocess

# local repo modules
import moviemanager.api.download_errors
import moviemanager.scraper.trailer_provider


#============================================
class TrailerService:
	"""Download movie trailers via a pluggable TrailerProvider.

	Delegates the actual download to a TrailerProvider instance
	(defaults to YtdlpTrailerProvider). Skips download when the
	file already exists.
	"""

	#============================================
	def __init__(self, provider=None):
		"""Initialize with an optional trailer provider.

		Args:
			provider: TrailerProvider instance. Defaults to
				YtdlpTrailerProvider if not given.
		"""
		if provider is None:
			provider = (
				moviemanager.scraper.trailer_provider
				.YtdlpTrailerProvider()
			)
		self._provider = provider

	#============================================
	def download_trailer(self, movie) -> str:
		"""Download a movie trailer using the configured provider.

		Args:
			movie: Movie instance with trailer_url set.

		Returns:
			str: Path to downloaded trailer file.

		Raises:
			DownloadError: With category describing the failure reason.
		"""
		_Cat = moviemanager.api.download_errors.DownloadCategory
		_Err = moviemanager.api.download_errors.DownloadError
		if not movie.trailer_url:
			raise _Err(_Cat.no_url, "No trailer URL for this movie")
		if not movie.path:
			raise _Err(_Cat.no_path, "Movie has no folder path")
		output_path = os.path.join(movie.path, "trailer.mp4")
		# skip if trailer already exists
		if os.path.exists(output_path):
			return output_path
		try:
			self._provider.download_trailer(
				movie.trailer_url, output_path,
			)
		except subprocess.TimeoutExpired:
			raise _Err(_Cat.timeout, "yt-dlp timed out after 300s")
		except subprocess.CalledProcessError as exc:
			# extract last line of stderr for a concise message
			stderr_text = (exc.stderr or b"").decode(
				"utf-8", errors="replace"
			)
			last_line = (
				stderr_text.strip().split("\n")[-1]
				if stderr_text.strip() else "unknown error"
			)
			raise _Err(_Cat.download_failed, last_line)
		return output_path
