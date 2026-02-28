"""OpenSubtitles REST API client for subtitle search and download."""

# Standard Library
import os
import time
import random

# PIP3 modules
import requests


# OpenSubtitles REST API base URL
_API_BASE = "https://api.opensubtitles.com/api/v1"


#============================================
class SubtitleScraper:
	"""Client for searching and downloading subtitles via OpenSubtitles API."""

	#============================================
	def __init__(self, api_key: str):
		"""Initialize with an OpenSubtitles API key.

		Args:
			api_key: OpenSubtitles REST API key.
		"""
		self._api_key = api_key
		self._headers = {
			"Api-Key": api_key,
			"Content-Type": "application/json",
			"User-Agent": "MovieMediaManager v1.0",
		}

	#============================================
	def search(self, imdb_id: str = "", languages: str = "en") -> list:
		"""Search for subtitles by IMDB ID.

		Args:
			imdb_id: IMDB identifier string (tt format).
			languages: Comma-separated language codes.

		Returns:
			list: List of subtitle result dicts with keys:
				file_id, language, release, download_count.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		params = {
			"imdb_id": imdb_id,
			"languages": languages,
		}
		response = requests.get(
			f"{_API_BASE}/subtitles",
			headers=self._headers,
			params=params,
			timeout=30,
		)
		response.raise_for_status()
		data = response.json()
		# parse results
		results = []
		for item in data.get("data", []):
			attributes = item.get("attributes", {})
			files = attributes.get("files", [])
			if not files:
				continue
			file_id = files[0].get("file_id", 0)
			result = {
				"file_id": file_id,
				"language": attributes.get("language", ""),
				"release": attributes.get("release", ""),
				"download_count": attributes.get("download_count", 0),
			}
			results.append(result)
		return results

	#============================================
	def download(self, file_id: int, output_path: str) -> str:
		"""Download a subtitle file by file ID.

		Args:
			file_id: OpenSubtitles file ID from search results.
			output_path: Path to save the subtitle file.

		Returns:
			str: Path to the downloaded subtitle file.
		"""
		# rate-limit courtesy pause
		time.sleep(random.random())
		# request download link
		response = requests.post(
			f"{_API_BASE}/download",
			headers=self._headers,
			json={"file_id": file_id},
			timeout=30,
		)
		response.raise_for_status()
		download_data = response.json()
		download_link = download_data.get("link", "")
		if not download_link:
			return ""
		# download the actual subtitle file
		time.sleep(random.random())
		sub_response = requests.get(download_link, timeout=30)
		sub_response.raise_for_status()
		with open(output_path, "wb") as f:
			f.write(sub_response.content)
		return output_path
