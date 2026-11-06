"""Trailer download provider using yt-dlp."""

# Standard Library
import subprocess

# local repo modules
import moviemanager.scraper.interfaces


#============================================
class YtdlpTrailerProvider(moviemanager.scraper.interfaces.TrailerProvider):
	"""Download trailers using the yt-dlp CLI tool.

	Downloads combined MP4 files directly, without merging or transcoding.
	"""

	# capabilities advertised by this provider
	capabilities = {
		moviemanager.scraper.interfaces.ProviderCapability.TRAILER,
	}

	# no API keys required for yt-dlp
	requires_keys = []

	#============================================
	def download_trailer(self, url: str, output_path: str) -> str:
		"""Download a trailer from a URL using yt-dlp.

		Args:
			url: Trailer URL to download.
			output_path: Destination file path for the trailer.

		Returns:
			str: Path to the downloaded trailer file.

		Raises:
			subprocess.TimeoutExpired: If yt-dlp takes longer than 300s.
			subprocess.CalledProcessError: If yt-dlp exits with an error.
		"""
		cmd = [
			"yt-dlp",
			"--ignore-config",
			"-o", output_path,
			# A direct combined stream avoids merging and transcoding.
			"--format", "best[ext=mp4][protocol=https]/best[ext=mp4][protocol=http]",
			"--fixup", "never",
			"--no-playlist",
			"--",
			url,
		]
		# ASVS 1.2.5: pass arguments directly, without shell interpretation.
		subprocess.run(
			cmd, check=True, timeout=300,
			capture_output=True,
		)
		return output_path
