#!/usr/bin/env python3
"""Unit tests for the browser cookie loader with mocked file system."""

# Standard Library
import os
import sys
import sqlite3
import tempfile
import unittest.mock

# PIP3 modules
import pytest

# add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import moviemanager.scraper.browser_cookies


#============================================
def _create_mock_cookies_db(db_path: str, cookies: list) -> None:
	"""Create a mock Firefox cookies.sqlite file with test data.

	Args:
		db_path: Path to create the database file.
		cookies: List of tuples (name, value, host, path, isSecure, expiry).
	"""
	conn = sqlite3.connect(db_path)
	conn.execute(
		"CREATE TABLE moz_cookies ("
		"name TEXT, value TEXT, host TEXT, path TEXT, "
		"isSecure INTEGER, expiry INTEGER)"
	)
	for cookie in cookies:
		conn.execute(
			"INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?, ?)",
			cookie,
		)
	conn.commit()
	conn.close()


#============================================
def test_load_firefox_cookies(tmp_path):
	"""Load IMDB cookies from a mocked Firefox profile."""
	# create a mock profile directory with cookies.sqlite
	profile_dir = str(tmp_path / "test_profile")
	os.makedirs(profile_dir)
	db_path = os.path.join(profile_dir, "cookies.sqlite")
	test_cookies = [
		("session-id", "abc123", ".imdb.com", "/", 1, 9999999999),
		("ubid-main", "def456", ".imdb.com", "/", 1, 9999999999),
		("other-cookie", "xyz", ".example.com", "/", 0, 9999999999),
	]
	_create_mock_cookies_db(db_path, test_cookies)
	# load cookies using the internal function
	result = moviemanager.scraper.browser_cookies._load_firefox_cookies(
		profile_dir
	)
	# should only get the 2 imdb cookies, not the example.com one
	assert len(result) == 2
	names = [c["name"] for c in result]
	assert "session-id" in names
	assert "ubid-main" in names
	# verify dict structure
	for cookie in result:
		assert "name" in cookie
		assert "value" in cookie
		assert "domain" in cookie
		assert "path" in cookie
		assert "secure" in cookie
		assert "expires" in cookie


#============================================
def test_load_firefox_cookies_missing_db(tmp_path):
	"""Missing cookies.sqlite returns empty list."""
	profile_dir = str(tmp_path / "empty_profile")
	os.makedirs(profile_dir)
	result = moviemanager.scraper.browser_cookies._load_firefox_cookies(
		profile_dir
	)
	assert result == []


#============================================
def test_unsupported_browser():
	"""Unsupported browser spec raises ValueError."""
	with pytest.raises(ValueError, match="Unsupported browser"):
		moviemanager.scraper.browser_cookies.load_imdb_cookies_from_browser(
			"chrome"
		)


#============================================
def test_unsupported_browser_safari():
	"""Safari browser spec raises ValueError."""
	with pytest.raises(ValueError, match="Unsupported browser"):
		moviemanager.scraper.browser_cookies.load_imdb_cookies_from_browser(
			"Safari"
		)


#============================================
def test_find_profile_no_firefox(tmp_path):
	"""Missing profiles.ini raises FileNotFoundError."""
	with unittest.mock.patch.dict(os.environ, {"HOME": str(tmp_path)}):
		with pytest.raises(FileNotFoundError, match="profiles.ini"):
			moviemanager.scraper.browser_cookies._find_firefox_profile_dir()


#============================================
def test_find_profile_no_imdb_cookies(tmp_path):
	"""Profile found but no IMDB cookies raises FileNotFoundError."""
	# set up macOS-style Firefox directory
	ff_dir = tmp_path / "Library" / "Application Support" / "Firefox"
	ff_dir.mkdir(parents=True)
	# create profiles.ini
	ini_path = ff_dir / "profiles.ini"
	ini_path.write_text(
		"[Profile0]\n"
		"Name=default\n"
		"IsRelative=1\n"
		"Path=test.default\n"
	)
	# create profile with cookies.sqlite but no IMDB cookies
	profile_dir = ff_dir / "test.default"
	profile_dir.mkdir()
	db_path = str(profile_dir / "cookies.sqlite")
	# only non-IMDB cookies
	_create_mock_cookies_db(db_path, [
		("other", "val", ".example.com", "/", 0, 9999999999),
	])
	with unittest.mock.patch.dict(os.environ, {"HOME": str(tmp_path)}):
		with pytest.raises(FileNotFoundError, match="No Firefox profile"):
			moviemanager.scraper.browser_cookies._find_firefox_profile_dir()


#============================================
def test_find_profile_with_imdb_cookies(tmp_path):
	"""Profile with IMDB cookies is correctly found."""
	# set up macOS-style Firefox directory
	ff_dir = tmp_path / "Library" / "Application Support" / "Firefox"
	ff_dir.mkdir(parents=True)
	# create profiles.ini
	ini_path = ff_dir / "profiles.ini"
	ini_path.write_text(
		"[Profile0]\n"
		"Name=default\n"
		"IsRelative=1\n"
		"Path=abc.default\n"
	)
	# create profile with IMDB cookies
	profile_dir = ff_dir / "abc.default"
	profile_dir.mkdir()
	db_path = str(profile_dir / "cookies.sqlite")
	_create_mock_cookies_db(db_path, [
		("session-id", "abc123", ".imdb.com", "/", 1, 9999999999),
	])
	with unittest.mock.patch.dict(os.environ, {"HOME": str(tmp_path)}):
		result = moviemanager.scraper.browser_cookies._find_firefox_profile_dir()
	assert result == str(profile_dir)


#============================================
def test_load_imdb_cookies_from_browser_firefox(tmp_path):
	"""Full pipeline: load_imdb_cookies_from_browser with firefox spec."""
	# set up macOS-style Firefox directory
	ff_dir = tmp_path / "Library" / "Application Support" / "Firefox"
	ff_dir.mkdir(parents=True)
	# create profiles.ini
	ini_path = ff_dir / "profiles.ini"
	ini_path.write_text(
		"[Profile0]\n"
		"Name=default\n"
		"IsRelative=1\n"
		"Path=test.default\n"
	)
	# create profile with IMDB cookies
	profile_dir = ff_dir / "test.default"
	profile_dir.mkdir()
	db_path = str(profile_dir / "cookies.sqlite")
	_create_mock_cookies_db(db_path, [
		("session-id", "val1", ".imdb.com", "/", 1, 9999999999),
		("ubid-main", "val2", ".imdb.com", "/", 1, 9999999999),
	])
	with unittest.mock.patch.dict(os.environ, {"HOME": str(tmp_path)}):
		result = moviemanager.scraper.browser_cookies.load_imdb_cookies_from_browser(
			"firefox"
		)
	assert len(result) == 2
