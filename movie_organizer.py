#!/usr/bin/env python3
"""Movie media manager CLI tool."""

# Standard Library
import os
import argparse

# PIP3 modules
import rich.console
import rich.progress
import rich.table

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.nfo.writer
import moviemanager.core.settings


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace with parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Movie media manager - organize and scrape movie metadata"
	)

	# global config option
	parser.add_argument(
		'-c', '--config', dest='config_file', default='',
		help='Path to config YAML file'
	)

	subparsers = parser.add_subparsers(
		dest='command', help='Available commands'
	)

	# scan subcommand
	scan_parser = subparsers.add_parser(
		'scan', help='Scan directory for movies'
	)
	scan_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Directory to scan for movies'
	)

	# info subcommand
	info_parser = subparsers.add_parser(
		'info', help='Show library info'
	)
	info_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Movie directory'
	)

	# scrape subcommand
	scrape_parser = subparsers.add_parser(
		'scrape', help='Scrape metadata for movies'
	)
	scrape_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Movie directory'
	)
	scrape_parser.add_argument(
		'-k', '--tmdb-key', dest='tmdb_key', default='',
		help='TMDB API key'
	)
	scrape_parser.add_argument(
		'-b', '--batch', dest='batch_mode',
		action='store_true',
		help='Auto-select first result'
	)
	scrape_parser.set_defaults(batch_mode=False)

	# rename subcommand
	rename_parser = subparsers.add_parser(
		'rename', help='Rename movie files'
	)
	rename_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Movie directory'
	)
	rename_parser.add_argument(
		'-t', '--template', dest='template',
		default='{title} ({year})',
		help='Rename template'
	)
	rename_parser.add_argument(
		'-n', '--dry-run', dest='dry_run',
		action='store_true',
		help='Preview renames without moving files'
	)
	rename_parser.add_argument(
		'-x', '--execute', dest='dry_run',
		action='store_false',
		help='Actually rename files'
	)
	rename_parser.set_defaults(dry_run=True)

	# edit subcommand
	edit_parser = subparsers.add_parser(
		'edit', help='Edit movie metadata'
	)
	edit_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Movie directory'
	)
	edit_parser.add_argument(
		'--title', dest='title', default='',
		help='Set movie title'
	)
	edit_parser.add_argument(
		'--year', dest='year', default='',
		help='Set movie year'
	)
	edit_parser.add_argument(
		'--genre', dest='genre', default='',
		help='Add genre to movie'
	)
	edit_parser.add_argument(
		'--director', dest='director', default='',
		help='Set movie director'
	)
	edit_parser.add_argument(
		'--rating', dest='rating', type=float, default=0.0,
		help='Set movie rating'
	)

	# artwork subcommand
	artwork_parser = subparsers.add_parser(
		'artwork', help='Download artwork for movies'
	)
	artwork_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Movie directory'
	)
	artwork_parser.add_argument(
		'--trailer', dest='download_trailer',
		action='store_true',
		help='Also download trailers'
	)
	artwork_parser.add_argument(
		'--subtitles', dest='download_subtitles',
		action='store_true',
		help='Also download subtitles'
	)
	artwork_parser.set_defaults(download_trailer=False)
	artwork_parser.set_defaults(download_subtitles=False)

	# list subcommand
	list_parser = subparsers.add_parser(
		'list', help='List movies with filtering'
	)
	list_parser.add_argument(
		'-d', '--directory', dest='directory', required=True,
		help='Movie directory'
	)
	list_parser.add_argument(
		'-f', '--filter', dest='filter_text', default='',
		help='Filter movies by title substring'
	)
	list_parser.add_argument(
		'-u', '--unscraped', dest='unscraped_only',
		action='store_true',
		help='Show only unscraped movies'
	)
	list_parser.set_defaults(unscraped_only=False)

	args = parser.parse_args()
	return args


#============================================
def cmd_scan(args: argparse.Namespace) -> None:
	"""Scan directory and print movie table.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	# print results as a table
	console = rich.console.Console()
	table = rich.table.Table(title="Movies Found")
	table.add_column("Title", style="cyan")
	table.add_column("Year", style="green")
	table.add_column("NFO", style="yellow")
	table.add_column("Scraped", style="magenta")
	for movie in movies:
		nfo_status = "Yes" if movie.has_nfo else "No"
		scraped_status = "Yes" if movie.scraped else "No"
		table.add_row(
			movie.title, movie.year, nfo_status, scraped_status
		)
	console.print(table)
	console.print(f"\nTotal: {len(movies)} movies")


#============================================
def cmd_info(args: argparse.Namespace) -> None:
	"""Print library statistics.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	console = rich.console.Console()
	console.print(f"Total movies:    {api.get_movie_count()}")
	console.print(f"Scraped:         {api.get_scraped_count()}")
	console.print(f"Unscraped:       {api.get_unscraped_count()}")
	# count movies with artwork files
	poster_count = sum(1 for m in movies if m.poster_url)
	fanart_count = sum(1 for m in movies if m.fanart_url)
	console.print(f"With poster:     {poster_count}")
	console.print(f"With fanart:     {fanart_count}")


#============================================
def cmd_scrape(args: argparse.Namespace) -> None:
	"""Scrape metadata from TMDB for unscraped movies.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	# override tmdb key from CLI if provided
	if args.tmdb_key:
		settings.tmdb_api_key = args.tmdb_key
	api = moviemanager.api.movie_api.MovieAPI(settings)
	api.scan_directory(args.directory)
	unscraped = api.get_unscraped()
	console = rich.console.Console()
	if not unscraped:
		console.print("All movies are already scraped.")
		return
	console.print(f"Found {len(unscraped)} unscraped movies.\n")
	for movie in rich.progress.track(unscraped, description="Scraping..."):
		console.print(f"Searching: {movie.title} ({movie.year})")
		results = api.search_movie(movie.title, movie.year)
		# try fallback search strategies if no results
		strategy = ""
		if not results:
			results, strategy = api.search_movie_with_fallback(
				movie.title, movie.year
			)
			if strategy and results:
				console.print(f"  Fallback ({strategy})")
		if not results:
			console.print("  No results found, skipping.\n")
			continue
		# display results table
		table = rich.table.Table(title="Search Results")
		table.add_column("#", style="bold")
		table.add_column("Title", style="cyan")
		table.add_column("Year", style="green")
		table.add_column("ID", style="yellow")
		for idx, sr in enumerate(results[:10], start=1):
			# show whichever ID is available
			id_text = str(sr.tmdb_id) if sr.tmdb_id else sr.imdb_id
			table.add_row(str(idx), sr.title, sr.year, id_text)
		console.print(table)
		# select result
		chosen_result = None
		if args.batch_mode:
			best = results[0]
			# check confidence before auto-selecting
			confidence = moviemanager.api.movie_api.MovieAPI.compute_match_confidence(
				movie.title, movie.year,
				best.title, best.year,
			)
			if confidence >= 0.7:
				chosen_result = best
				console.print(
					f"  Batch: auto-selected '{best.title}'"
					f" (confidence: {confidence:.1f})"
				)
			else:
				console.print(
					f"  Skipped: low confidence {confidence:.1f}"
					f" for '{best.title}'\n"
				)
				continue
		else:
			# interactive: prompt user to pick
			choice = input("Pick a number (0 to skip): ").strip()
			if choice.isdigit() and 1 <= int(choice) <= len(results[:10]):
				chosen_result = results[int(choice) - 1]
			else:
				console.print("  Skipped.\n")
				continue
		# scrape the chosen movie using available ID
		if chosen_result.tmdb_id:
			api.scrape_movie(movie, tmdb_id=chosen_result.tmdb_id)
		elif chosen_result.imdb_id:
			api.scrape_movie(movie, imdb_id=chosen_result.imdb_id)
		console.print(f"  Scraped: {movie.title} ({movie.year})\n")


#============================================
def cmd_rename(args: argparse.Namespace) -> None:
	"""Rename movie files according to a template.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	# override path template from CLI if provided
	if args.template:
		settings.path_template = args.template
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	console = rich.console.Console()
	if not movies:
		console.print("No movies found.")
		return
	# preview renames (always dry_run first)
	all_pairs = []
	for movie in rich.progress.track(movies, description="Generating preview..."):
		pairs = api.rename_movie(movie, dry_run=True)
		all_pairs.extend(pairs)
	if not all_pairs:
		console.print("No renames needed.")
		return
	# show preview table
	table = rich.table.Table(title="Rename Preview")
	table.add_column("Source", style="cyan")
	table.add_column("Destination", style="green")
	for source, dest in all_pairs:
		table.add_row(
			os.path.basename(source), os.path.basename(dest)
		)
	console.print(table)
	# if dry run, stop here
	if args.dry_run:
		console.print("\nDry run -- no files moved.")
		return
	# prompt user for confirmation
	answer = input("Proceed with rename? [y/N] ").strip().lower()
	if answer != "y":
		console.print("Aborted.")
		return
	# execute renames
	for movie in movies:
		pairs = api.rename_movie(movie, dry_run=False)
		for source, dest in pairs:
			console.print(f"  Moved: {os.path.basename(source)}"
				f" -> {os.path.basename(dest)}")
	console.print(f"\nRenamed {len(movies)} movies.")


#============================================
def cmd_edit(args: argparse.Namespace) -> None:
	"""Edit metadata fields on a movie and write NFO.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	console = rich.console.Console()
	if not movies:
		console.print("No movies found.")
		return
	# select movie to edit
	movie = None
	if len(movies) == 1:
		movie = movies[0]
	else:
		# print list and ask user which one
		for idx, m in enumerate(movies, start=1):
			console.print(f"  {idx}. {m.title} ({m.year})")
		choice = input(f"Pick a movie (1-{len(movies)}): ").strip()
		if choice.isdigit() and 1 <= int(choice) <= len(movies):
			movie = movies[int(choice) - 1]
		else:
			console.print("Invalid choice.")
			return
	# update fields from CLI flags
	if args.title:
		movie.title = args.title
	if args.year:
		movie.year = args.year
	if args.genre:
		if args.genre not in movie.genres:
			movie.genres.append(args.genre)
	if args.director:
		movie.director = args.director
	if args.rating:
		movie.rating = args.rating
	# build NFO path from video file or title
	nfo_path = ""
	video_file = movie.video_file
	if video_file:
		base, _ = os.path.splitext(video_file.filename)
		nfo_path = os.path.join(movie.path, base + ".nfo")
	else:
		safe_title = movie.title or "movie"
		nfo_path = os.path.join(movie.path, safe_title + ".nfo")
	# write the NFO file
	moviemanager.core.nfo.writer.write_nfo(movie, nfo_path)
	movie.nfo_path = nfo_path
	console.print(f"Updated: {movie.title} ({movie.year})")
	console.print(f"NFO written: {nfo_path}")


#============================================
def cmd_artwork(args: argparse.Namespace) -> None:
	"""Download artwork for scraped movies.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	console = rich.console.Console()
	# filter to scraped movies only
	scraped_movies = [m for m in movies if m.scraped]
	if not scraped_movies:
		console.print("No scraped movies found.")
		return
	console.print(f"Found {len(scraped_movies)} scraped movies.\n")
	total_downloaded = 0
	for movie in rich.progress.track(
		scraped_movies, description="Downloading artwork..."
	):
		downloaded = api.download_artwork(movie)
		for path in downloaded:
			console.print(f"  Downloaded: {os.path.basename(path)}"
				f" for '{movie.title}'")
		total_downloaded += len(downloaded)
	console.print(f"\nDownloaded {total_downloaded} artwork files.")


#============================================
def cmd_list(args: argparse.Namespace) -> None:
	"""List movies with optional filtering.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	console = rich.console.Console()
	# apply filters
	if args.unscraped_only:
		movies = [m for m in movies if not m.scraped]
	if args.filter_text:
		filter_lower = args.filter_text.lower()
		movies = [m for m in movies if filter_lower in m.title.lower()]
	if not movies:
		console.print("No movies match the filters.")
		return
	# build table
	table = rich.table.Table(title="Movie Library")
	table.add_column("Title", style="cyan")
	table.add_column("Year", style="green")
	table.add_column("Rating", style="yellow")
	table.add_column("NFO", style="magenta")
	table.add_column("Scraped", style="blue")
	for movie in movies:
		rating_str = f"{movie.rating:.1f}" if movie.rating else "-"
		nfo_status = "Yes" if movie.has_nfo else "No"
		scraped_status = "Yes" if movie.scraped else "No"
		table.add_row(
			movie.title, movie.year, rating_str,
			nfo_status, scraped_status
		)
	console.print(table)
	console.print(f"\nShowing {len(movies)} movies.")


#============================================
def main():
	"""Main entry point for the CLI."""
	args = parse_args()
	# handle missing command
	if args.command is None:
		print("No command specified. Use --help for usage.")
		return
	# dispatch to command handler
	commands = {
		'scan': cmd_scan,
		'info': cmd_info,
		'scrape': cmd_scrape,
		'rename': cmd_rename,
		'edit': cmd_edit,
		'artwork': cmd_artwork,
		'list': cmd_list,
	}
	cmd_func = commands.get(args.command)
	if cmd_func:
		cmd_func(args)


#============================================
if __name__ == '__main__':
	main()
