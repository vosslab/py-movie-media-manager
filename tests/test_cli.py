"""Tests for the movie_organizer CLI entry point."""

# Standard Library
import subprocess

# local repo modules
import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()


#============================================
def test_cli_help():
	"""CLI --help should exit 0 and show subcommands."""
	result = subprocess.run(
		["python3", "movie_organizer.py", "--help"],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	assert "scan" in result.stdout
	assert "info" in result.stdout


#============================================
def test_cli_scan_help():
	"""scan --help should exit 0."""
	result = subprocess.run(
		["python3", "movie_organizer.py", "scan", "--help"],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0


#============================================
def test_cli_no_command():
	"""Running with no command should exit 0 with a message."""
	result = subprocess.run(
		["python3", "movie_organizer.py"],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	assert "no command" in result.stdout.lower()


#============================================
def test_cli_scan_tmp(tmp_path):
	"""Scan an empty temp directory should find 0 movies."""
	result = subprocess.run(
		["python3", "movie_organizer.py", "scan", "-d", str(tmp_path)],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	# check that the output mentions 0 movies
	lower_out = result.stdout.lower()
	has_zero = "0 movies" in lower_out or "total: 0" in lower_out
	assert has_zero


#============================================
def test_cli_info_tmp(tmp_path):
	"""Info on an empty temp directory should show 0 counts."""
	result = subprocess.run(
		["python3", "movie_organizer.py", "info", "-d", str(tmp_path)],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	assert "0" in result.stdout
