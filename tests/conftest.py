"""Pytest configuration -- add repo root to sys.path for imports."""
import sys
import git_file_utils

# add repo root so 'import moviemanager' works without pip install
_repo_root = git_file_utils.get_repo_root()
if _repo_root not in sys.path:
	sys.path.insert(0, _repo_root)
