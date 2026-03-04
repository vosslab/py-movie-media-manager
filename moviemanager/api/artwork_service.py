"""Artwork download service for movie poster and fanart images."""

# Standard Library
import os
import time
import random

# PIP3 modules
import requests

# local repo modules
import moviemanager.core.settings


#============================================
class ArtworkService:
	"""Download poster and fanart images for movies.

	Downloads artwork files to the movie directory based on
	settings and available URLs. Skips files that already exist.
	"""

	#============================================
	def __init__(self, settings: moviemanager.core.settings.Settings):
		"""Initialize the artwork service.

		Args:
			settings: Application settings with download flags.
		"""
		self._settings = settings

	#============================================
	def download_artwork(self, movie) -> list:
		"""Download artwork files for a movie.

		Downloads poster and fanart images to the movie directory
		based on settings and available URLs.

		Args:
			movie: Movie instance with artwork URLs.

		Returns:
			list: Paths of downloaded artwork files.
		"""
		downloaded = []
		if not movie.path:
			return downloaded
		# download poster
		if self._settings.download_poster and movie.poster_url:
			poster_path = os.path.join(movie.path, "poster.jpg")
			if not os.path.exists(poster_path):
				time.sleep(random.random())
				response = requests.get(
					movie.poster_url, timeout=30
				)
				response.raise_for_status()
				with open(poster_path, "wb") as f:
					f.write(response.content)
				downloaded.append(poster_path)
		# download fanart
		if self._settings.download_fanart and movie.fanart_url:
			fanart_path = os.path.join(movie.path, "fanart.jpg")
			if not os.path.exists(fanart_path):
				time.sleep(random.random())
				response = requests.get(
					movie.fanart_url, timeout=30
				)
				response.raise_for_status()
				with open(fanart_path, "wb") as f:
					f.write(response.content)
				downloaded.append(fanart_path)
		return downloaded
