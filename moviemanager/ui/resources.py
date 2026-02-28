"""Resource loading utilities for the GUI."""

# Standard Library
import os


#============================================
def get_icon_path(name: str) -> str:
	"""Get path to an icon file.

	Args:
		name: Icon filename.

	Returns:
		str: Full path to the icon file.
	"""
	icon_dir = os.path.join(os.path.dirname(__file__), "icons")
	path = os.path.join(icon_dir, name)
	return path
