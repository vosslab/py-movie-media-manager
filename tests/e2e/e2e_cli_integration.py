"""Run CLI scan, info, and rename workflows outside pytest's fast lane."""

# Standard Library
import pathlib
import subprocess
import sys
import tempfile


#============================================
def run_command(repo_root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
	"""Run the CLI using the active Python interpreter."""
	command = [sys.executable, "movie_organizer.py", *args]
	result = subprocess.run(command, capture_output=True, text=True, cwd=repo_root)
	return result


#============================================
def require_success(result: subprocess.CompletedProcess[str]) -> None:
	"""Raise with CLI diagnostics when a command fails."""
	if result.returncode != 0:
		raise RuntimeError(result.stderr)


#============================================
def main() -> None:
	"""Exercise scan, info, and dry-run rename against temporary movie files."""
	repo_root = pathlib.Path(__file__).resolve().parents[2]
	with tempfile.TemporaryDirectory() as temp_dir:
		movie_root = pathlib.Path(temp_dir)
		inception_dir = movie_root / "Inception (2010)"
		inception_dir.mkdir()
		(inception_dir / "Inception.2010.mkv").touch()
		scan_result = run_command(repo_root, "scan", "-d", str(movie_root))
		require_success(scan_result)
		if "Inception" not in scan_result.stdout:
			raise RuntimeError(scan_result.stdout)
		info_result = run_command(repo_root, "info", "-d", str(movie_root))
		require_success(info_result)
		rename_result = run_command(repo_root, "rename", "-d", str(movie_root), "-n")
		require_success(rename_result)
		if not (inception_dir / "Inception.2010.mkv").is_file():
			raise RuntimeError("Dry-run rename moved the source video.")


#============================================
if __name__ == "__main__":
	main()
