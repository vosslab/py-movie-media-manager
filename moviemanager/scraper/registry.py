"""Scraper registry and provider pipeline for dynamic provider discovery."""

# Standard Library
import os
import inspect
import logging
import importlib

# local repo modules
import moviemanager.scraper.interfaces


# module logger
_LOG = logging.getLogger(__name__)


#============================================
class ScraperRegistry:
	"""Registry of scraper provider classes indexed by name and capability.

	Stores provider classes along with their required settings keys.
	Supports filtering providers by capability and settings availability,
	and creating provider instances on demand.
	"""

	#============================================
	def __init__(self):
		"""Initialize an empty registry."""
		# maps provider name -> dict with 'cls' and 'requires_keys'
		self._providers = {}

	#============================================
	def register(
		self, name: str, provider_class: type, requires_keys: list = None,
	) -> None:
		"""Register a provider class under a name.

		Args:
			name: Unique name for this provider.
			provider_class: The provider class to register.
			requires_keys: List of settings attribute names required
				for this provider to be available.
		"""
		if requires_keys is None:
			requires_keys = []
		entry = {
			"cls": provider_class,
			"requires_keys": requires_keys,
		}
		self._providers[name] = entry

	#============================================
	def get_available(
		self,
		capability: moviemanager.scraper.interfaces.ProviderCapability,
		settings,
	) -> list:
		"""Return provider names that support a capability and have keys.

		Filters registered providers by capability (checking the class-level
		capabilities attribute) and by whether all required settings keys
		are present and non-empty.

		Args:
			capability: The capability to filter for.
			settings: Settings object with API key attributes.

		Returns:
			list: List of provider name strings that are available.
		"""
		available = []
		for name, entry in self._providers.items():
			cls = entry["cls"]
			# check capability
			caps = getattr(cls, "capabilities", set())
			if capability not in caps:
				continue
			# check required keys are present in settings
			keys_ok = True
			for key in entry["requires_keys"]:
				value = getattr(settings, key, "")
				if not value:
					keys_ok = False
					break
			if keys_ok:
				available.append(name)
		return available

	#============================================
	def create_provider(self, name: str, settings) -> object:
		"""Create a provider instance by name using settings for config.

		Maps known settings keys to constructor arguments:
		- tmdb_api_key -> api_key + scrape_language -> language
		- fanart_api_key -> api_key
		- opensubtitles_api_key -> api_key

		Args:
			name: Registered provider name.
			settings: Settings object with API key attributes.

		Returns:
			A new provider instance.

		Raises:
			KeyError: If name is not registered.
		"""
		if name not in self._providers:
			raise KeyError(f"Provider '{name}' is not registered")
		entry = self._providers[name]
		cls = entry["cls"]
		requires = entry["requires_keys"]
		# build constructor kwargs based on required keys
		kwargs = {}
		if "tmdb_api_key" in requires:
			kwargs["api_key"] = getattr(settings, "tmdb_api_key", "")
			kwargs["language"] = getattr(settings, "scrape_language", "en")
		elif "fanart_api_key" in requires:
			kwargs["api_key"] = getattr(settings, "fanart_api_key", "")
		elif "opensubtitles_api_key" in requires:
			kwargs["api_key"] = getattr(
				settings, "opensubtitles_api_key", ""
			)
		instance = cls(**kwargs)
		return instance

	#============================================
	def create_pipeline(self, settings) -> "ProviderPipeline":
		"""Build a ProviderPipeline respecting scraper_provider setting.

		Honors settings.scraper_provider ("imdb" or "tmdb") when the
		chosen provider is available. Falls back to IMDB when the
		requested provider lacks a required API key.

		Args:
			settings: Settings object with API key attributes.

		Returns:
			ProviderPipeline: Configured pipeline instance.
		"""
		_Cap = moviemanager.scraper.interfaces.ProviderCapability
		# check which metadata providers are available
		metadata_providers = self.get_available(_Cap.METADATA, settings)
		primary = None
		supplements = []
		# respect the user's scraper_provider setting
		preferred = getattr(settings, "scraper_provider", "imdb")
		if preferred == "tmdb" and "tmdb" in metadata_providers:
			# user chose TMDB and key is available
			primary = self.create_provider("tmdb", settings)
			if "imdb" in metadata_providers:
				imdb_scraper = self.create_provider("imdb", settings)
				supplements.append(imdb_scraper)
		elif "imdb" in metadata_providers:
			# user chose IMDB, or TMDB unavailable
			primary = self.create_provider("imdb", settings)
			# add TMDB as supplement for artwork when key is available
			if "tmdb" in metadata_providers:
				tmdb_scraper = self.create_provider("tmdb", settings)
				supplements.append(tmdb_scraper)
		elif "tmdb" in metadata_providers:
			# IMDB unavailable (shouldn't happen), fall back to TMDB
			primary = self.create_provider("tmdb", settings)
		# add parental guide provider if available
		pg_providers = self.get_available(
			_Cap.PARENTAL_GUIDE, settings,
		)
		for pg_name in pg_providers:
			# skip if primary already has parental guide capability
			primary_caps = getattr(primary, "capabilities", set())
			if _Cap.PARENTAL_GUIDE in primary_caps:
				break
			# skip if already added as supplement
			already = any(
				type(s).__name__ == self._providers[pg_name]["cls"].__name__
				for s in supplements
			)
			if not already:
				pg_prov = self.create_provider(pg_name, settings)
				supplements.append(pg_prov)
		# add trailer provider if available
		trailer_providers = self.get_available(
			_Cap.TRAILER, settings,
		)
		for tp_name in trailer_providers:
			trailer_prov = self.create_provider(tp_name, settings)
			supplements.append(trailer_prov)
		# add subtitle provider if available
		subtitle_providers = self.get_available(
			_Cap.SUBTITLES, settings,
		)
		for sp_name in subtitle_providers:
			# skip if already added as primary or supplement
			already = any(
				type(s).__name__ == self._providers[sp_name]["cls"].__name__
				for s in supplements
			)
			if not already:
				sub_prov = self.create_provider(sp_name, settings)
				supplements.append(sub_prov)
		# add artwork provider if available
		artwork_providers = self.get_available(
			_Cap.ARTWORK, settings,
		)
		for ap_name in artwork_providers:
			ap_cls = self._providers[ap_name]["cls"]
			# skip if primary is the same class
			if primary is not None and type(primary).__name__ == ap_cls.__name__:
				continue
			# skip if already added as supplement
			already = any(
				type(s).__name__ == ap_cls.__name__
				for s in supplements
			)
			if not already:
				art_prov = self.create_provider(ap_name, settings)
				supplements.append(art_prov)
		pipeline = ProviderPipeline(
			primary=primary, supplements=supplements,
		)
		return pipeline

	#============================================
	def get_registered_names(self) -> list:
		"""Return all registered provider names.

		Returns:
			list: Sorted list of registered provider name strings.
		"""
		names = sorted(self._providers.keys())
		return names


#============================================
class ProviderPipeline:
	"""Routes capability requests to the appropriate provider.

	Holds a primary provider for search/metadata and optional
	supplement providers for additional capabilities like parental
	guide, artwork, or subtitles.
	"""

	#============================================
	def __init__(self, primary=None, supplements: list = None):
		"""Initialize the pipeline with primary and supplement providers.

		Args:
			primary: Primary provider for search and metadata.
			supplements: List of supplemental provider instances.
		"""
		self.primary = primary
		self.supplements = supplements or []

	#============================================
	def get_for_capability(
		self,
		capability: moviemanager.scraper.interfaces.ProviderCapability,
	) -> object:
		"""Return the first provider that supports a capability.

		Checks the primary provider first, then supplements.

		Args:
			capability: The capability to look for.

		Returns:
			Provider instance, or None if no provider supports it.
		"""
		# check primary first
		if self.primary is not None:
			caps = getattr(self.primary, "capabilities", set())
			if capability in caps:
				return self.primary
		# check supplements
		for provider in self.supplements:
			caps = getattr(provider, "capabilities", set())
			if capability in caps:
				return provider
		return None

	#============================================
	def get_artwork_providers(self) -> list:
		"""Return all providers that support the ARTWORK capability.

		Returns:
			list: Provider instances with ARTWORK capability.
		"""
		_Cap = moviemanager.scraper.interfaces.ProviderCapability
		providers = []
		for provider in self.supplements:
			caps = getattr(provider, "capabilities", set())
			if _Cap.ARTWORK in caps:
				providers.append(provider)
		return providers


#============================================
def build_default_registry() -> ScraperRegistry:
	"""Build a registry by auto-discovering scraper classes.

	Scans all Python modules in the moviemanager/scraper/ directory
	for classes that have a 'capabilities' attribute (indicating they
	are scraper providers). Registers each discovered class under a
	name derived from the class name (e.g. TmdbScraper -> 'tmdb').

	Returns:
		ScraperRegistry: Populated with all discovered providers.
	"""
	registry = ScraperRegistry()
	# find the scraper package directory
	scraper_pkg = importlib.import_module("moviemanager.scraper")
	pkg_dir = os.path.dirname(scraper_pkg.__file__)
	# scan for Python modules in the scraper directory
	for filename in sorted(os.listdir(pkg_dir)):
		if not filename.endswith(".py"):
			continue
		if filename.startswith("_"):
			continue
		module_name = filename[:-3]
		full_module = f"moviemanager.scraper.{module_name}"
		try:
			mod = importlib.import_module(full_module)
		except Exception as err:
			_LOG.debug(
				"Skipping module %s during auto-discovery: %s",
				full_module, err,
			)
			continue
		# inspect classes in the module
		for attr_name in dir(mod):
			obj = getattr(mod, attr_name)
			if not inspect.isclass(obj):
				continue
			# skip classes not defined in this module
			if obj.__module__ != full_module:
				continue
			# check for capabilities attribute
			caps = getattr(obj, "capabilities", None)
			if not caps:
				continue
			# derive provider name: TmdbScraper -> 'tmdb'
			provider_name = _class_name_to_provider_name(attr_name)
			requires = getattr(obj, "requires_keys", [])
			registry.register(provider_name, obj, requires)
			_LOG.debug(
				"Auto-discovered provider '%s' from %s.%s",
				provider_name, full_module, attr_name,
			)
	return registry


#============================================
def _class_name_to_provider_name(class_name: str) -> str:
	"""Convert a class name like 'TmdbScraper' to a provider name like 'tmdb'.

	Strips common suffixes ('Scraper', 'Provider') and lowercases.

	Args:
		class_name: The class name string.

	Returns:
		str: Lowercase provider name.
	"""
	name = class_name
	# strip known suffixes
	for suffix in ("Scraper", "Provider"):
		if name.endswith(suffix):
			name = name[:-len(suffix)]
			break
	result = name.lower()
	return result


# simple assertions for _class_name_to_provider_name
assert _class_name_to_provider_name("TmdbScraper") == "tmdb"
assert _class_name_to_provider_name("ImdbScraper") == "imdb"
assert _class_name_to_provider_name("FanartScraper") == "fanart"
assert _class_name_to_provider_name("SubtitleScraper") == "subtitle"
assert _class_name_to_provider_name("ImdbParentalGuideScraper") == "imdbparentalguide"
