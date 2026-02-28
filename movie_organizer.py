#!/usr/bin/env python3
"""Movie media manager CLI tool."""

# Standard Library
import os
import argparse

# PIP3 modules
import rich.console
import rich.table

# local repo modules
import moviemanager.api.movie_api
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
	for movie in unscraped:
		console.print(f"Searching: {movie.title} ({movie.year})")
		results = api.search_movie(movie.title, movie.year)
		if not results:
			console.print("  No results found, skipping.\n")
			continue
		# display results table
		table = rich.table.Table(title="Search Results")
		table.add_column("#", style="bold")
		table.add_column("Title", style="cyan")
		table.add_column("Year", style="green")
		table.add_column("TMDB ID", style="yellow")
		for idx, sr in enumerate(results[:10], start=1):
			table.add_row(
				str(idx), sr.title, sr.year, str(sr.tmdb_id)
			)
		console.print(table)
		# select result
		chosen_id = 0
		if args.batch_mode:
			# auto-select first result in batch mode
			chosen_id = results[0].tmdb_id
			console.print(f"  Batch: auto-selected '{results[0].title}'")
		else:
			# interactive: prompt user to pick
			choice = input("Pick a number (0 to skip): ").strip()
			if choice.isdigit() and 1 <= int(choice) <= len(results[:10]):
				chosen_id = results[int(choice) - 1].tmdb_id
			else:
				console.print("  Skipped.\n")
				continue
		# scrape the chosen movie
		api.scrape_movie(movie, chosen_id)
		console.print(f"  Scraped: {movie.title} ({movie.year})\n")


#============================================
def cmd_rename(args: argparse.Namespace) -> None:
	"""Rename movie files according to a template.

	Args:
		args: Parsed command-line arguments.
	"""
	settings = moviemanager.core.settings.load_settings(args.config_file)
	# override template from CLI if provided
	if args.template:
		settings.path_template = args.template
		settings.file_template = args.template
	api = moviemanager.api.movie_api.MovieAPI(settings)
	movies = api.scan_directory(args.directory)
	console = rich.console.Console()
	if not movies:
		console.print("No movies found.")
		return
	# preview renames (always dry_run first)
	all_pairs = []
	for movie in movies:
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
	}
	cmd_func = commands.get(args.command)
	if cmd_func:
		cmd_func(args)


#============================================
if __name__ == '__main__':
	main()
