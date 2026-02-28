#!/usr/bin/env python3
"""Movie media manager CLI tool."""

# Standard Library
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
	api.scan_directory(args.directory)
	console = rich.console.Console()
	console.print(f"Total movies:    {api.get_movie_count()}")
	console.print(f"Scraped:         {api.get_scraped_count()}")
	console.print(f"Unscraped:       {api.get_unscraped_count()}")


#============================================
def cmd_scrape(args: argparse.Namespace) -> None:
	"""Placeholder for scrape command.

	Args:
		args: Parsed command-line arguments.
	"""
	console = rich.console.Console()
	console.print(
		"[yellow]Scrape command requires TMDB API key"
		" and will be fully wired in M3.[/yellow]"
	)


#============================================
def cmd_rename(args: argparse.Namespace) -> None:
	"""Placeholder for rename command.

	Args:
		args: Parsed command-line arguments.
	"""
	console = rich.console.Console()
	console.print(
		"[yellow]Rename command will be fully wired in M3.[/yellow]"
	)


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
