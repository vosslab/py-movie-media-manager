"""Artwork download service for all enabled artwork types."""

# Standard Library
import os
import time
import random
import logging

# PIP3 modules
import requests

# local repo modules
import moviemanager.core.constants
import moviemanager.core.settings


# module logger
_LOG = logging.getLogger(__name__)

# artwork type -> (settings flag, movie URL attr, canonical filename)
_ARTWORK_DOWNLOAD_MAP = {
	"poster": ("download_poster", "poster_url", "poster.jpg"),
	"fanart": ("download_fanart", "fanart_url", "fanart.jpg"),
	"banner": ("download_banner", "banner_url", "banner.jpg"),
	"clearart": ("download_clearart", "clearart_url", "clearart.png"),
	"logo": ("download_logo", "logo_url", "logo.png"),
	"discart": ("download_discart", "discart_url", "disc.png"),
}


#============================================
class ArtworkService:
	"""Download artwork images for movies.

	Downloads all enabled artwork types to the movie directory
	based on settings and available URLs. Skips files that
	already exist on disk.
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
		"""Download all enabled artwork files for a movie.

		Iterates over all artwork types, checking the settings
		flag, URL availability, and disk presence before downloading.

		Args:
			movie: Movie instance with artwork URLs.

		Returns:
			list: Paths of downloaded artwork files.
		"""
		downloaded = []
		if not movie.path:
			return downloaded
		for art_type, (setting_flag, url_attr, filename) in _ARTWORK_DOWNLOAD_MAP.items():
			# check if this artwork type is enabled in settings
			if not getattr(self._settings, setting_flag, False):
				continue
			# check if the movie has a URL for this type
			url = getattr(movie, url_attr, "")
			if not url:
				continue
			# check if the file already exists on disk
			dest_path = os.path.join(movie.path, filename)
			if os.path.exists(dest_path):
				continue
			# download the artwork file
			time.sleep(random.random())
			try:
				response = requests.get(url, timeout=30)
				response.raise_for_status()
				with open(dest_path, "wb") as f:
					f.write(response.content)
				downloaded.append(dest_path)
				_LOG.info(
					"Downloaded %s for %s",
					art_type, movie.title,
				)
			except requests.RequestException as err:
				_LOG.warning(
					"Failed to download %s for %s: %s",
					art_type, movie.title, err,
				)
		return downloaded
