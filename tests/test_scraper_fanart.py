"""Tests for the Fanart.tv scraper module."""

# Standard Library
import unittest.mock

# PIP3 modules
import requests

# local repo modules
import moviemanager.scraper.fanart_scraper
import moviemanager.scraper.types


#============================================
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.requests.get")
def test_get_artwork_returns_urls(mock_get, mock_sleep):
	"""Verify artwork JSON is mapped to correct type names and URLs."""
	# mock a successful JSON response
	mock_response = unittest.mock.MagicMock()
	mock_response.json.return_value = {
		"movieposter": [
			{"url": "https://fanart.tv/poster1.jpg"},
			{"url": "https://fanart.tv/poster2.jpg"},
		],
		"moviebackground": [
			{"url": "https://fanart.tv/bg1.jpg"},
		],
		"hdmovielogo": [
			{"url": "https://fanart.tv/logo1.png"},
		],
	}
	mock_response.raise_for_status = unittest.mock.MagicMock()
	mock_get.return_value = mock_response
	scraper = moviemanager.scraper.fanart_scraper.FanartScraper(
		api_key="test_key"
	)
	artwork = scraper.get_artwork(tmdb_id=603)
	# verify type mapping
	assert "poster" in artwork
	assert len(artwork["poster"]) == 2
	assert artwork["poster"][0] == "https://fanart.tv/poster1.jpg"
	assert "fanart" in artwork
	assert len(artwork["fanart"]) == 1
	assert "logo" in artwork
	assert len(artwork["logo"]) == 1
	# verify the API was called with correct params
	mock_get.assert_called_once()
	call_args = mock_get.call_args
	assert "603" in call_args[0][0]
	assert call_args[1]["params"]["api_key"] == "test_key"


#============================================
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.requests.get")
def test_get_artwork_empty_response(mock_get, mock_sleep):
	"""Verify empty JSON response returns empty dict."""
	mock_response = unittest.mock.MagicMock()
	mock_response.json.return_value = {}
	mock_response.raise_for_status = unittest.mock.MagicMock()
	mock_get.return_value = mock_response
	scraper = moviemanager.scraper.fanart_scraper.FanartScraper(
		api_key="test_key"
	)
	artwork = scraper.get_artwork(tmdb_id=12345)
	assert artwork == {}


#============================================
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.time.sleep")
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.requests.get")
def test_get_artwork_request_error(mock_get, mock_sleep):
	"""Verify request errors return empty dict gracefully."""
	mock_get.side_effect = requests.RequestException("Connection failed")
	scraper = moviemanager.scraper.fanart_scraper.FanartScraper(
		api_key="test_key"
	)
	artwork = scraper.get_artwork(tmdb_id=603)
	assert artwork == {}


#============================================
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.requests.get")
@unittest.mock.patch("moviemanager.scraper.fanart_scraper.time.sleep")
def test_sleep_between_calls(mock_sleep, mock_get):
	"""Verify time.sleep is called for rate limiting."""
	mock_response = unittest.mock.MagicMock()
	mock_response.json.return_value = {}
	mock_response.raise_for_status = unittest.mock.MagicMock()
	mock_get.return_value = mock_response
	scraper = moviemanager.scraper.fanart_scraper.FanartScraper(
		api_key="test_key"
	)
	scraper.get_artwork(tmdb_id=603)
	# verify sleep was called at least once
	mock_sleep.assert_called_once()
