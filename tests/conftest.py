# Exclude both end-to-end tiers from pytest collection. tests/playwright/
# holds browser-driven tests (Playwright), and tests/e2e/ holds heavier
# shell/Python whole-system runners. Both run outside pytest -- see
# docs/PLAYWRIGHT_USAGE.md and docs/E2E_TESTS.md.
collect_ignore = ["e2e", "playwright"]

"""Pytest configuration -- add repo root to sys.path for imports."""
import sys
import git_file_utils

# add repo root so 'import moviemanager' works without pip install
_repo_root = git_file_utils.get_repo_root()
if _repo_root not in sys.path:
	sys.path.insert(0, _repo_root)
