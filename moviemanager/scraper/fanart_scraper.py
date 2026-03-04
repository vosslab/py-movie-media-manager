"""Fanart.tv scraper implementing ArtworkProvider using requests."""

# Standard Library
import time
import random

# PIP3 modules
import requests

# local repo modules
import moviemanager.scraper.interfaces
import moviemanager.scraper.types


# Fanart.tv API base URL
FANART_BASE_URL = "http://webservice.fanart.tv/v3/movies"

# mapping from fanart.tv JSON keys to our artwork type names
_ARTWORK_TYPE_MAP = {
	"movieposter": "poster",
	"moviebackground": "fanart",
	"hdmovielogo": "logo",
	"hdmovieclearart": "clearart",
	"moviedisc": "discart",
	"moviebanner": "banner",
	"moviethumb": "thumb",
}


#============================================
class FanartScraper(moviemanager.scraper.interfaces.ArtworkProvider):
	"""Fanart.tv artwork scraper using the REST API.

	Fetches artwork URLs for movies from the Fanart.tv service
	via direct HTTP requests.
	"""

	# capabilities advertised by this scraper
	capabilities = {
		moviemanager.scraper.interfaces.ProviderCapability.ARTWORK,
	}

	# settings keys required to instantiate this scraper
	requires_keys = ["fanart_api_key"]

	#============================================
	def __init__(self, api_key: str):
		"""Initialize the Fanart.tv scraper with an API key.

		Args:
			api_key: Fanart.tv API key for authentication.
		"""
		self._api_key = api_key

	#============================================
	def get_artwork(self, tmdb_id: int = 0, imdb_id: str = "") -> dict:
		"""Fetch available artwork URLs for a movie from Fanart.tv.

		Args:
			tmdb_id: TMDB movie ID.
			imdb_id: IMDB movie ID.

		Returns:
			dict: Mapping of artwork type to list of URL strings.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		# build the request URL
		url = f"{FANART_BASE_URL}/{tmdb_id}"
		params = {"api_key": self._api_key}
		try:
			response = requests.get(url, params=params, timeout=30)
			response.raise_for_status()
		except requests.RequestException:
			# return empty dict on any request error
			return {}
		data = response.json()
		# map fanart.tv artwork types to our type names
		artwork = {}
		for fanart_key, our_type in _ARTWORK_TYPE_MAP.items():
			raw_items = data.get(fanart_key, [])
			urls = []
			for item in raw_items:
				image_url = item.get("url", "")
				if image_url:
					urls.append(image_url)
			if urls:
				artwork[our_type] = urls
		return artwork
