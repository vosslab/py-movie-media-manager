"""Run the CLI command-boundary checks outside pytest's fast lane."""

# Standard Library
import pathlib
import subprocess
import sys


#============================================
def run_command(repo_root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
	"""Run movie_organizer.py with the active Python interpreter."""
	command = [sys.executable, "movie_organizer.py", *args]
	result = subprocess.run(command, capture_output=True, text=True, cwd=repo_root)
	return result


#============================================
def require_success(result: subprocess.CompletedProcess[str], expected: str) -> None:
	"""Raise when a CLI result lacks its required text or exit status."""
	if result.returncode != 0:
		raise RuntimeError(result.stderr)
	if expected not in result.stdout:
		raise RuntimeError(f"Expected {expected!r} in: {result.stdout!r}")


#============================================
def main() -> None:
	"""Check help and the no-command result through the real CLI boundary."""
	repo_root = pathlib.Path(__file__).resolve().parents[2]
	require_success(run_command(repo_root, "--help"), "scan")
	require_success(run_command(repo_root, "scan", "--help"), "usage:")
	require_success(run_command(repo_root), "No command")


#============================================
if __name__ == "__main__":
	main()
