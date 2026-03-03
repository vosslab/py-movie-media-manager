"""Application settings loaded from a YAML config file."""

# Standard Library
import os
import dataclasses

# PIP3 modules
import yaml

# default config file location (XDG-style)
DEFAULT_CONFIG_PATH = os.path.join(
	os.environ.get("HOME", ""),
	".config",
	"movie_organizer.yaml",
)


#============================================
@dataclasses.dataclass
class Settings:
	"""Application settings loaded from YAML config file."""

	# API keys
	tmdb_api_key: str = ""
	fanart_api_key: str = ""
	# load browser cookies for IMDB scraping
	imdb_browser_cookies_enabled: bool = False
	# browser name for IMDB cookie loading (currently firefox)
	imdb_browser_cookies_browser: str = "firefox"

	# scraping preferences
	scrape_language: str = "en"
	scrape_country: str = "US"
	certification_country: str = "US"

	# renamer templates
	path_template: str = "{title}-{year}"
	file_template: str = "{title}-{year}"
	# replace spaces with underscores in filenames for shell safety
	spaces_to_underscores: bool = True
	# separator between appended media tokens (hyphen, dot, or underscore)
	media_separator: str = "-"
	# media token checkboxes for renamer
	rename_resolution: bool = False
	rename_vcodec: bool = False
	rename_acodec: bool = False
	rename_channels: bool = False

	# scanner options
	skip_hidden_dirs: bool = True

	# appearance
	theme: str = "system"

	# scraper provider ("imdb" or "tmdb")
	scraper_provider: str = "imdb"

	# last opened directory
	last_directory: str = ""

	# trailer/subtitle options
	download_trailer: bool = True
	download_subtitles: bool = False
	subtitle_languages: str = "en"

	# OpenSubtitles API key (stored in user .config)
	opensubtitles_api_key: str = ""

	# table column visibility (checkbox col 0 is always visible)
	visible_columns: list = dataclasses.field(
		default_factory=lambda: [
			"Title", "Year", "Rating", "Min", "M", "O", "A", "S", "T",
			"S&N", "V&G", "Prof", "A&D", "F&I",
		]
	)

	# artwork options
	download_poster: bool = True
	download_fanart: bool = True
	download_banner: bool = False
	download_clearart: bool = False
	download_logo: bool = False
	download_discart: bool = False


#============================================
def load_settings(config_path: str = "") -> Settings:
	"""Load settings from a YAML config file.

	Args:
		config_path: Path to the YAML config file.
			If empty, uses DEFAULT_CONFIG_PATH.

	Returns:
		Settings dataclass populated from the config file,
		or defaults if file does not exist.
	"""
	if not config_path:
		config_path = DEFAULT_CONFIG_PATH
	# return defaults when config file is missing
	if not os.path.isfile(config_path):
		return Settings()
	# read the yaml config file
	with open(config_path, "r") as f:
		data = yaml.safe_load(f)
	# handle empty or non-dict yaml
	if not isinstance(data, dict):
		return Settings()
	# collect only fields that exist on the dataclass
	known_fields = {field.name for field in dataclasses.fields(Settings)}
	filtered = {k: v for k, v in data.items() if k in known_fields}
	settings = Settings(**filtered)
	return settings


#============================================
def save_settings(settings: Settings, config_path: str = "") -> None:
	"""Save settings to a YAML config file.

	Args:
		settings: The Settings dataclass to persist.
		config_path: Path to the YAML config file.
			If empty, uses DEFAULT_CONFIG_PATH.
	"""
	if not config_path:
		config_path = DEFAULT_CONFIG_PATH
	# create parent directory if it does not exist
	parent_dir = os.path.dirname(config_path)
	if parent_dir:
		os.makedirs(parent_dir, exist_ok=True)
	# convert dataclass to dict and write yaml
	data = dataclasses.asdict(settings)
	with open(config_path, "w") as f:
		yaml.dump(data, f, default_flow_style=False)
