"""Verify that core/ and scraper/ packages never import PySide6."""

import os

import pytest

import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()

# directories that must not import PySide6
GUARDED_DIRS = [
	os.path.join(REPO_ROOT, "moviemanager", "core"),
	os.path.join(REPO_ROOT, "moviemanager", "scraper"),
	os.path.join(REPO_ROOT, "moviemanager", "api"),
]


#============================================
def _collect_python_files() -> list:
	"""Collect all .py files in guarded directories."""
	files = []
	for guarded_dir in GUARDED_DIRS:
		for dirpath, dirnames, filenames in os.walk(guarded_dir):
			for filename in filenames:
				if filename.endswith(".py"):
					filepath = os.path.join(dirpath, filename)
					# use relative path for test id
					relpath = os.path.relpath(filepath, REPO_ROOT)
					files.append(relpath)
	return sorted(files)


#============================================
@pytest.mark.parametrize("relpath", _collect_python_files())
def test_no_pyside6_import(relpath: str) -> None:
	"""Verify that file does not import PySide6."""
	filepath = os.path.join(REPO_ROOT, relpath)
	with open(filepath, "r") as f:
		content = f.read()
	# check for PySide6 imports
	has_import = "import PySide6" in content
	has_from = "from PySide6" in content
	assert not has_import and not has_from, (
		f"{relpath} imports PySide6 -- core/scraper/api must not depend on Qt"
	)
