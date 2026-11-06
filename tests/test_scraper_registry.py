"""Tests for scraper registry, auto-discovery, and provider pipeline."""

# Standard Library
import types
import unittest.mock

# local repo modules
import moviemanager.scraper.imdb_parental_guide_scraper
import moviemanager.scraper.imdb_scraper
import moviemanager.scraper.interfaces
import moviemanager.scraper.registry
import moviemanager.scraper.tmdb_scraper


# shorthand for ProviderCapability
_Cap = moviemanager.scraper.interfaces.ProviderCapability


#============================================
def _make_settings(**overrides) -> types.SimpleNamespace:
	"""Build a fake settings object with optional overrides.

	Args:
		**overrides: Keyword arguments to set on the settings object.

	Returns:
		SimpleNamespace with default empty settings and overrides applied.
	"""
	defaults = {
		"tmdb_api_key": "",
		"fanart_api_key": "",
		"opensubtitles_api_key": "",
		"scrape_language": "en",
		"scraper_provider": "imdb",
	}
	defaults.update(overrides)
	settings = types.SimpleNamespace(**defaults)
	return settings


#============================================
def test_get_available_filters_by_capability() -> None:
	"""Verify get_available only returns providers with matching capability."""
	registry = moviemanager.scraper.registry.ScraperRegistry()
	registry.register(
		"tmdb", moviemanager.scraper.tmdb_scraper.TmdbScraper,
		requires_keys=["tmdb_api_key"],
	)
	registry.register(
		"imdb", moviemanager.scraper.imdb_scraper.ImdbScraper,
		requires_keys=[],
	)
	registry.register(
		"imdbparentalguide",
		moviemanager.scraper.imdb_parental_guide_scraper.ImdbParentalGuideScraper,
		requires_keys=[],
	)
	settings = _make_settings(tmdb_api_key="fake_key")
	# both have METADATA capability
	metadata_available = registry.get_available(_Cap.METADATA, settings)
	assert "tmdb" in metadata_available
	assert "imdb" in metadata_available
	# only ImdbParentalGuideScraper has PARENTAL_GUIDE capability
	pg_available = registry.get_available(_Cap.PARENTAL_GUIDE, settings)
	assert "imdbparentalguide" in pg_available
	assert "tmdb" not in pg_available
	assert "imdb" not in pg_available
	# only TMDB has ARTWORK capability
	art_available = registry.get_available(_Cap.ARTWORK, settings)
	assert "tmdb" in art_available
	assert "imdb" not in art_available


#============================================
def test_get_available_filters_by_settings_keys() -> None:
	"""Verify get_available excludes providers when required keys are missing."""
	registry = moviemanager.scraper.registry.ScraperRegistry()
	registry.register(
		"tmdb", moviemanager.scraper.tmdb_scraper.TmdbScraper,
		requires_keys=["tmdb_api_key"],
	)
	registry.register(
		"imdb", moviemanager.scraper.imdb_scraper.ImdbScraper,
		requires_keys=[],
	)
	# no TMDB API key set
	settings = _make_settings(tmdb_api_key="")
	metadata_available = registry.get_available(_Cap.METADATA, settings)
	# TMDB should not be available without key
	assert "tmdb" not in metadata_available
	# IMDB needs no keys, so it should be available
	assert "imdb" in metadata_available


#============================================
def test_create_provider_unknown_raises() -> None:
	"""Verify create_provider raises KeyError for unknown provider."""
	registry = moviemanager.scraper.registry.ScraperRegistry()
	settings = _make_settings()
	raised = False
	try:
		registry.create_provider("nonexistent", settings)
	except KeyError:
		raised = True
	assert raised


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
@unittest.mock.patch("tmdbv3api.Find")
def test_create_pipeline_tmdb_primary(mock_find: object, mock_movie: object, mock_tmdb: object) -> None:
	"""Verify pipeline uses TMDB primary + IMDB + parental guide supplements."""
	registry = moviemanager.scraper.registry.ScraperRegistry()
	registry.register(
		"tmdb", moviemanager.scraper.tmdb_scraper.TmdbScraper,
		requires_keys=["tmdb_api_key"],
	)
	registry.register(
		"imdb", moviemanager.scraper.imdb_scraper.ImdbScraper,
		requires_keys=[],
	)
	registry.register(
		"imdbparentalguide",
		moviemanager.scraper.imdb_parental_guide_scraper.ImdbParentalGuideScraper,
		requires_keys=[],
	)
	settings = _make_settings(
		tmdb_api_key="fake_key", scraper_provider="tmdb",
	)
	pipeline = registry.create_pipeline(settings)
	assert isinstance(
		pipeline.primary, moviemanager.scraper.tmdb_scraper.TmdbScraper,
	)
	# supplements: IMDB metadata + parental guide
	assert len(pipeline.supplements) == 2
	assert isinstance(
		pipeline.supplements[0],
		moviemanager.scraper.imdb_scraper.ImdbScraper,
	)
	assert isinstance(
		pipeline.supplements[1],
		moviemanager.scraper.imdb_parental_guide_scraper.ImdbParentalGuideScraper,
	)


#============================================
def test_create_pipeline_imdb_fallback() -> None:
	"""Verify pipeline falls back to IMDB-only when no TMDB key."""
	registry = moviemanager.scraper.registry.ScraperRegistry()
	registry.register(
		"tmdb", moviemanager.scraper.tmdb_scraper.TmdbScraper,
		requires_keys=["tmdb_api_key"],
	)
	registry.register(
		"imdb", moviemanager.scraper.imdb_scraper.ImdbScraper,
		requires_keys=[],
	)
	settings = _make_settings(tmdb_api_key="")
	pipeline = registry.create_pipeline(settings)
	assert isinstance(
		pipeline.primary, moviemanager.scraper.imdb_scraper.ImdbScraper,
	)
	assert pipeline.supplements == []


#============================================
@unittest.mock.patch("tmdbv3api.TMDb")
@unittest.mock.patch("tmdbv3api.Movie")
@unittest.mock.patch("tmdbv3api.Find")
def test_create_pipeline_imdb_primary_with_tmdb_supplement(
	mock_find: object, mock_movie: object, mock_tmdb: object,
) -> None:
	"""Verify IMDB primary adds TMDB as supplement for artwork."""
	registry = moviemanager.scraper.registry.ScraperRegistry()
	registry.register(
		"tmdb", moviemanager.scraper.tmdb_scraper.TmdbScraper,
		requires_keys=["tmdb_api_key"],
	)
	registry.register(
		"imdb", moviemanager.scraper.imdb_scraper.ImdbScraper,
		requires_keys=[],
	)
	registry.register(
		"imdbparentalguide",
		moviemanager.scraper.imdb_parental_guide_scraper.ImdbParentalGuideScraper,
		requires_keys=[],
	)
	# IMDB primary (default) but TMDB key available
	settings = _make_settings(tmdb_api_key="fake_key")
	pipeline = registry.create_pipeline(settings)
	assert isinstance(
		pipeline.primary, moviemanager.scraper.imdb_scraper.ImdbScraper,
	)
	# supplements: TMDB for artwork + parental guide
	assert len(pipeline.supplements) == 2
	assert isinstance(
		pipeline.supplements[0],
		moviemanager.scraper.tmdb_scraper.TmdbScraper,
	)
	assert isinstance(
		pipeline.supplements[1],
		moviemanager.scraper.imdb_parental_guide_scraper.ImdbParentalGuideScraper,
	)


#============================================
def test_pipeline_get_for_capability() -> None:
	"""Verify pipeline routes capability requests to correct provider."""
	# create mock providers with capabilities
	primary = types.SimpleNamespace(
		capabilities={_Cap.SEARCH, _Cap.METADATA, _Cap.ARTWORK},
	)
	supplement = types.SimpleNamespace(
		capabilities={_Cap.PARENTAL_GUIDE},
	)
	pipeline = moviemanager.scraper.registry.ProviderPipeline(
		primary=primary, supplements=[supplement],
	)
	# SEARCH should route to primary
	assert pipeline.get_for_capability(_Cap.SEARCH) is primary
	# PARENTAL_GUIDE should route to supplement
	assert pipeline.get_for_capability(_Cap.PARENTAL_GUIDE) is supplement
	# SUBTITLES not available
	assert pipeline.get_for_capability(_Cap.SUBTITLES) is None


#============================================
def test_pipeline_get_for_capability_no_primary() -> None:
	"""Verify pipeline handles None primary gracefully."""
	supplement = types.SimpleNamespace(
		capabilities={_Cap.PARENTAL_GUIDE},
	)
	pipeline = moviemanager.scraper.registry.ProviderPipeline(
		primary=None, supplements=[supplement],
	)
	assert pipeline.get_for_capability(_Cap.SEARCH) is None
	assert pipeline.get_for_capability(_Cap.PARENTAL_GUIDE) is supplement


#============================================
def test_auto_discovery_capabilities() -> None:
	"""Verify discovered scrapers have correct capabilities."""
	registry = moviemanager.scraper.registry.build_default_registry()
	settings_with_keys = _make_settings(
		tmdb_api_key="fake",
		fanart_api_key="fake",
		opensubtitles_api_key="fake",
	)
	# SEARCH: tmdb and imdb
	search = registry.get_available(_Cap.SEARCH, settings_with_keys)
	assert "tmdb" in search
	assert "imdb" in search
	# METADATA: tmdb and imdb
	meta = registry.get_available(_Cap.METADATA, settings_with_keys)
	assert "tmdb" in meta
	assert "imdb" in meta
	# ARTWORK: tmdb and fanart
	art = registry.get_available(_Cap.ARTWORK, settings_with_keys)
	assert "tmdb" in art
	assert "fanart" in art
	# PARENTAL_GUIDE: imdbparentalguide only
	pg = registry.get_available(_Cap.PARENTAL_GUIDE, settings_with_keys)
	assert "imdbparentalguide" in pg
	assert len(pg) == 1
	# SUBTITLES: subtitle only
	subs = registry.get_available(_Cap.SUBTITLES, settings_with_keys)
	assert "subtitle" in subs
	assert len(subs) == 1
