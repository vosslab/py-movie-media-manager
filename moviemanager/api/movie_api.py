"""Facade providing all movie operations for CLI and GUI."""

# Standard Library
import os
import time
import random
import subprocess

# PIP3 modules
import requests

# local repo modules
import moviemanager.core.movie.movie_list
import moviemanager.core.movie.renamer
import moviemanager.core.movie.scanner
import moviemanager.core.nfo.writer
import moviemanager.core.settings
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.tmdb_scraper


#============================================
class MovieAPI:
	"""Facade providing all movie operations for CLI and GUI.

	Wraps scanning, scraping, and renaming behind a single interface.
	Maintains an in-memory MovieList for the current session.
	"""

	def __init__(self, settings: moviemanager.core.settings.Settings = None):
		"""Initialize the MovieAPI.

		Args:
			settings: Application settings. If None, uses defaults.
		"""
		if settings is None:
			settings = moviemanager.core.settings.Settings()
		self._settings = settings
		self._movie_list = moviemanager.core.movie.movie_list.MovieList()
		self._scraper = None

	#============================================
	def scan_directory(self, root_path: str, progress_callback=None) -> list:
		"""Scan a directory for movie files and add them to the library.

		Args:
			root_path: Root directory path to scan.
			progress_callback: Optional callable(current, message) for progress.

		Returns:
			List of Movie instances discovered during the scan.
		"""
		movies = moviemanager.core.movie.scanner.scan_directory(
			root_path, progress_callback=progress_callback
		)
		for movie in movies:
			self._movie_list.add(movie)
		return movies

	#============================================
	def get_movies(self) -> list:
		"""Return all movies in the library.

		Returns:
			List of all Movie instances.
		"""
		result = self._movie_list.get_all()
		return result

	#============================================
	def get_unscraped(self) -> list:
		"""Return movies that have not been scraped.

		Returns:
			List of unscraped Movie instances.
		"""
		result = self._movie_list.get_unscraped()
		return result

	#============================================
	def _ensure_scraper(self) -> None:
		"""Create the scraper based on settings provider preference.

		Uses IMDB scraper (no key needed) or TMDB scraper (key required).
		Falls back to IMDB if TMDB key is missing.
		"""
		if self._scraper is not None:
			return
		provider = self._settings.scraper_provider
		if provider == "tmdb":
			api_key = self._settings.tmdb_api_key
			if api_key:
				self._scraper = moviemanager.scraper.tmdb_scraper.TmdbScraper(
					api_key=api_key,
					language=self._settings.scrape_language,
				)
				return
			# fall back to IMDB if no TMDB key
		self._scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()

	#============================================
	def search_movie(self, title: str, year: str = "") -> list:
		"""Search for movie metadata by title.

		Args:
			title: Movie title to search for.
			year: Optional release year to narrow results.

		Returns:
			List of SearchResult instances from the scraper.
		"""
		self._ensure_scraper()
		result = self._scraper.search(title, year)
		return result

	#============================================
	def scrape_movie(self, movie, tmdb_id: int = 0, imdb_id: str = "") -> None:
		"""Fetch and apply metadata to a movie from the active scraper.

		Maps MediaMetadata fields onto the Movie object, marks it
		as scraped, and writes a Kodi-format NFO file.

		Args:
			movie: Movie instance to update with scraped metadata.
			tmdb_id: TMDB ID to fetch metadata for.
			imdb_id: IMDB ID to fetch metadata for.
		"""
		self._ensure_scraper()
		metadata = self._scraper.get_metadata(
			tmdb_id=tmdb_id, imdb_id=imdb_id
		)
		# map MediaMetadata fields to the Movie object
		movie.title = metadata.title or movie.title
		movie.original_title = metadata.original_title or movie.original_title
		movie.year = metadata.year or movie.year
		movie.plot = metadata.plot
		movie.tagline = metadata.tagline
		movie.runtime = metadata.runtime
		movie.rating = metadata.rating
		movie.votes = metadata.votes
		movie.genres = metadata.genres
		movie.director = metadata.director
		movie.writer = metadata.writer
		movie.studio = metadata.studio
		movie.country = metadata.country
		movie.spoken_languages = metadata.spoken_languages
		movie.imdb_id = metadata.imdb_id
		movie.tmdb_id = metadata.tmdb_id
		movie.poster_url = metadata.poster_url
		movie.fanart_url = metadata.fanart_url
		movie.certification = metadata.certification
		movie.release_date = metadata.release_date
		movie.trailer_url = metadata.trailer_url
		# convert CastMember dataclasses to dicts for NFO writer
		movie.actors = [
			{"name": a.name, "role": a.role, "tmdb_id": a.tmdb_id}
			for a in metadata.actors
		]
		movie.scraped = True
		# build NFO path from first video file basename
		nfo_path = ""
		video_file = movie.video_file
		if video_file:
			base, _ = os.path.splitext(video_file.filename)
			nfo_path = os.path.join(movie.path, base + ".nfo")
		else:
			# fallback: use movie title
			safe_title = movie.title or "movie"
			nfo_path = os.path.join(movie.path, safe_title + ".nfo")
		# write the NFO file
		moviemanager.core.nfo.writer.write_nfo(movie, nfo_path)
		movie.nfo_path = nfo_path

	#============================================
	def rename_movie(
		self,
		movie,
		path_template: str = "",
		file_template: str = "",
		dry_run: bool = True,
	) -> list:
		"""Generate rename operations for a movie.

		Args:
			movie: Movie instance to rename.
			path_template: Template for directory name.
			file_template: Template for file name.
			dry_run: If True, only return planned renames.

		Returns:
			List of (source, destination) path tuples.
		"""
		# use settings templates as defaults
		if not path_template:
			path_template = self._settings.path_template
		if not file_template:
			file_template = self._settings.file_template
		result = moviemanager.core.movie.renamer.rename_movie(
			movie, path_template, file_template, dry_run=dry_run,
		)
		return result

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
				response = requests.get(movie.poster_url, timeout=30)
				response.raise_for_status()
				with open(poster_path, "wb") as f:
					f.write(response.content)
				downloaded.append(poster_path)
		# download fanart
		if self._settings.download_fanart and movie.fanart_url:
			fanart_path = os.path.join(movie.path, "fanart.jpg")
			if not os.path.exists(fanart_path):
				time.sleep(random.random())
				response = requests.get(movie.fanart_url, timeout=30)
				response.raise_for_status()
				with open(fanart_path, "wb") as f:
					f.write(response.content)
				downloaded.append(fanart_path)
		return downloaded

	#============================================
	def get_movie_count(self) -> int:
		"""Return the total number of movies in the library.

		Returns:
			Integer count of movies.
		"""
		result = self._movie_list.count()
		return result

	#============================================
	def get_scraped_count(self) -> int:
		"""Return the number of scraped movies.

		Returns:
			Integer count of scraped movies.
		"""
		result = len(self._movie_list.get_scraped())
		return result

	#============================================
	def get_unscraped_count(self) -> int:
		"""Return the number of unscraped movies.

		Returns:
			Integer count of unscraped movies.
		"""
		result = len(self._movie_list.get_unscraped())
		return result

	#============================================
	def download_trailer(self, movie) -> str:
		"""Download a movie trailer using yt-dlp.

		Args:
			movie: Movie instance with trailer_url set.

		Returns:
			str: Path to downloaded trailer file, or empty string.
		"""
		if not movie.trailer_url or not movie.path:
			return ""
		output_path = os.path.join(movie.path, "trailer.mp4")
		# skip if trailer already exists
		if os.path.exists(output_path):
			return output_path
		cmd = [
			"yt-dlp",
			"-o", output_path,
			"--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
			"--no-playlist",
			movie.trailer_url,
		]
		subprocess.run(cmd, check=True, timeout=300)
		return output_path

	#============================================
	def download_subtitles(self, movie, languages: str = "en") -> list:
		"""Download subtitles for a movie from OpenSubtitles.

		Args:
			movie: Movie instance with imdb_id set.
			languages: Comma-separated language codes.

		Returns:
			list: Paths of downloaded subtitle files.
		"""
		if not movie.imdb_id or not movie.path:
			return []
		api_key = self._settings.opensubtitles_api_key
		if not api_key:
			raise ValueError(
				"OpenSubtitles API key is not configured. "
				"Set it in Settings > API Keys."
			)
		import moviemanager.scraper.subtitle_scraper
		scraper = moviemanager.scraper.subtitle_scraper.SubtitleScraper(
			api_key
		)
		results = scraper.search(
			imdb_id=movie.imdb_id, languages=languages
		)
		if not results:
			return []
		# group by language, take best per language (highest download count)
		downloaded = []
		by_lang = {}
		for r in results:
			lang = r.get("language", "en")
			if lang not in by_lang:
				by_lang[lang] = r
			elif r.get("download_count", 0) > by_lang[lang].get("download_count", 0):
				by_lang[lang] = r
		for lang, best in by_lang.items():
			file_id = best.get("file_id", 0)
			if not file_id:
				continue
			# name subtitle file with language code
			srt_filename = f"subtitles.{lang}.srt"
			srt_path = os.path.join(movie.path, srt_filename)
			# skip if already exists
			if os.path.exists(srt_path):
				downloaded.append(srt_path)
				continue
			result_path = scraper.download(file_id, srt_path)
			if result_path:
				downloaded.append(result_path)
		return downloaded
