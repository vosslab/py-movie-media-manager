"""Run the real IMDb suggestion lookup outside pytest's fast lane."""

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# local repo modules
import moviemanager.scraper.imdb_scraper


#============================================
def main() -> None:
	"""Verify the CDN suggestion API returns Clerks (1994)."""
	scraper = moviemanager.scraper.imdb_scraper.ImdbScraper()
	results = scraper.search("Clerks", year="1994")
	for result in results:
		if result.title == "Clerks" and result.year == "1994" and result.imdb_id == "tt0109445":
			return
	raise RuntimeError("IMDb search did not return Clerks (1994, tt0109445).")


#============================================
if __name__ == "__main__":
	main()
