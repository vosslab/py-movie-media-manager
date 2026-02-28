"""Integration tests for CLI subcommands with real file operations."""

# Standard Library
import subprocess

# local repo modules
import git_file_utils
import moviemanager.core.models.movie
import moviemanager.core.nfo.writer

REPO_ROOT = git_file_utils.get_repo_root()


#============================================
def test_scan_with_movies(tmp_path):
	"""Scan a directory with a video file."""
	# create a fake movie directory with a video file
	movie_dir = tmp_path / "Inception (2010)"
	movie_dir.mkdir()
	(movie_dir / "Inception.2010.mkv").touch()
	result = subprocess.run(
		["python3", "movie_organizer.py", "scan", "-d", str(tmp_path)],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	assert "Inception" in result.stdout


#============================================
def test_info_with_movies(tmp_path):
	"""Info command shows correct counts."""
	# create an unscraped movie
	movie_dir = tmp_path / "Test Movie"
	movie_dir.mkdir()
	(movie_dir / "test.mkv").touch()
	# create a scraped movie with an NFO file
	movie_dir2 = tmp_path / "Scraped Movie"
	movie_dir2.mkdir()
	(movie_dir2 / "scraped.mkv").touch()
	# write an NFO for the scraped movie
	m = moviemanager.core.models.movie.Movie(
		title="Scraped Movie", year="2020", scraped=True
	)
	moviemanager.core.nfo.writer.write_nfo(
		m, str(movie_dir2 / "scraped.nfo")
	)
	result = subprocess.run(
		["python3", "movie_organizer.py", "info", "-d", str(tmp_path)],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	# should show total of 2 movies
	assert "2" in result.stdout


#============================================
def test_rename_dry_run(tmp_path):
	"""Rename dry run shows preview without moving."""
	# create a movie directory with a video file
	movie_dir = tmp_path / "raw_movie"
	movie_dir.mkdir()
	video_file = movie_dir / "Inception.2010.BluRay.mkv"
	video_file.touch()
	result = subprocess.run(
		["python3", "movie_organizer.py", "rename",
			"-d", str(tmp_path), "-n"],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	# file should still be in original location
	assert video_file.exists()


#============================================
def test_scan_empty_directory(tmp_path):
	"""Scan an empty directory should find 0 movies."""
	result = subprocess.run(
		["python3", "movie_organizer.py", "scan", "-d", str(tmp_path)],
		capture_output=True, text=True,
		cwd=REPO_ROOT,
	)
	assert result.returncode == 0
	lower_out = result.stdout.lower()
	has_zero = "0 movies" in lower_out or "total: 0" in lower_out
	assert has_zero
