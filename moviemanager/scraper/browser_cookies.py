#!/usr/bin/env python3
"""Load IMDB cookies from a local browser profile."""

# Standard Library
import os
import glob
import shutil
import sqlite3
import tempfile
import logging
import configparser


# module logger
_LOG = logging.getLogger(__name__)


#============================================
def _find_firefox_profile_dir() -> str:
	"""Locate the Firefox profile directory that contains IMDB cookies.

	Searches macOS and Linux default locations for profiles.ini,
	then picks the profile whose cookies.sqlite has .imdb.com entries.

	Returns:
		str: Absolute path to the Firefox profile directory.

	Raises:
		FileNotFoundError: If no Firefox profile with IMDB cookies is found.
	"""
	home = os.environ.get("HOME", "")
	# candidate locations for profiles.ini on macOS and Linux
	candidate_dirs = [
		os.path.join(home, "Library", "Application Support", "Firefox"),
		os.path.join(home, ".mozilla", "firefox"),
	]
	profiles_ini_path = ""
	firefox_dir = ""
	for candidate in candidate_dirs:
		ini_path = os.path.join(candidate, "profiles.ini")
		if os.path.isfile(ini_path):
			profiles_ini_path = ini_path
			firefox_dir = candidate
			break
	if not profiles_ini_path:
		raise FileNotFoundError(
			"Firefox profiles.ini not found in standard locations"
		)
	# parse profiles.ini to find profile directories
	config = configparser.ConfigParser()
	config.read(profiles_ini_path)
	profile_paths = []
	for section in config.sections():
		if not section.startswith("Profile"):
			continue
		path = config.get(section, "Path", fallback="")
		is_relative = config.getint(section, "IsRelative", fallback=1)
		if not path:
			continue
		if is_relative:
			full_path = os.path.join(firefox_dir, path)
		else:
			full_path = path
		profile_paths.append(full_path)
	# also check for profile dirs matching common patterns
	for pattern in ["*.default", "*.default-release", "*.default-esr"]:
		for match in glob.glob(os.path.join(firefox_dir, pattern)):
			if match not in profile_paths:
				profile_paths.append(match)
	# find the profile that has imdb cookies
	for profile_dir in profile_paths:
		cookies_db = os.path.join(profile_dir, "cookies.sqlite")
		if not os.path.isfile(cookies_db):
			continue
		# check if this profile has imdb cookies
		count = _count_imdb_cookies(cookies_db)
		if count > 0:
			_LOG.info(
				"Found Firefox profile with %d IMDB cookies: %s",
				count, profile_dir,
			)
			return profile_dir
	raise FileNotFoundError(
		"No Firefox profile found with .imdb.com cookies"
	)


#============================================
def _count_imdb_cookies(db_path: str) -> int:
	"""Count IMDB cookies in a Firefox cookies.sqlite without locking it.

	Args:
		db_path: Path to the cookies.sqlite file.

	Returns:
		int: Number of .imdb.com cookie rows.
	"""
	# copy to temp dir to avoid WAL lock conflicts with running Firefox
	tmp_dir = tempfile.mkdtemp(prefix="imdb_cookies_")
	tmp_db = os.path.join(tmp_dir, "cookies.sqlite")
	try:
		shutil.copy2(db_path, tmp_db)
		# also copy WAL and SHM files if present
		for suffix in ["-wal", "-shm"]:
			wal_src = db_path + suffix
			if os.path.isfile(wal_src):
				shutil.copy2(wal_src, tmp_db + suffix)
		conn = sqlite3.connect(tmp_db)
		cursor = conn.execute(
			"SELECT COUNT(*) FROM moz_cookies WHERE host LIKE '%imdb.com'"
		)
		count = cursor.fetchone()[0]
		conn.close()
		return count
	finally:
		shutil.rmtree(tmp_dir, ignore_errors=True)


#============================================
def _load_firefox_cookies(profile_dir: str) -> list:
	"""Read IMDB cookies from a Firefox profile's cookies.sqlite.

	Copies the database to a temp directory to avoid WAL lock
	conflicts with a running Firefox instance.

	Args:
		profile_dir: Path to the Firefox profile directory.

	Returns:
		list: List of cookie dicts with keys: name, value, domain, path, secure, expires.
	"""
	db_path = os.path.join(profile_dir, "cookies.sqlite")
	if not os.path.isfile(db_path):
		_LOG.warning("cookies.sqlite not found in %s", profile_dir)
		return []
	# copy DB to temp dir to avoid WAL lock
	tmp_dir = tempfile.mkdtemp(prefix="imdb_cookies_")
	tmp_db = os.path.join(tmp_dir, "cookies.sqlite")
	try:
		shutil.copy2(db_path, tmp_db)
		# also copy WAL and SHM files if present
		for suffix in ["-wal", "-shm"]:
			wal_src = db_path + suffix
			if os.path.isfile(wal_src):
				shutil.copy2(wal_src, tmp_db + suffix)
		conn = sqlite3.connect(tmp_db)
		cursor = conn.execute(
			"SELECT name, value, host, path, isSecure, expiry "
			"FROM moz_cookies WHERE host LIKE '%imdb.com'"
		)
		cookies = []
		for row in cursor.fetchall():
			cookie = {
				"name": row[0],
				"value": row[1],
				"domain": row[2],
				"path": row[3],
				"secure": bool(row[4]),
				"expires": row[5],
			}
			cookies.append(cookie)
		conn.close()
		_LOG.info("Loaded %d IMDB cookies from Firefox", len(cookies))
		return cookies
	finally:
		shutil.rmtree(tmp_dir, ignore_errors=True)


#============================================
def load_imdb_cookies_from_browser(browser_spec: str) -> list:
	"""Load IMDB cookies from a browser profile.

	Currently supports Firefox. The browser_spec string selects
	which browser to load cookies from.

	Args:
		browser_spec: Browser name string (e.g. 'firefox').

	Returns:
		list: List of cookie dicts.

	Raises:
		ValueError: If the browser_spec is not supported.
		FileNotFoundError: If the browser profile cannot be found.
	"""
	spec = browser_spec.strip().lower()
	if spec != "firefox":
		raise ValueError(
			f"Unsupported browser for cookie loading: {browser_spec!r}. "
			f"Only 'firefox' is currently supported."
		)
	profile_dir = _find_firefox_profile_dir()
	cookies = _load_firefox_cookies(profile_dir)
	return cookies
