#!/usr/bin/env python3
"""Movie media manager PySide6 GUI application."""

# Standard Library
import sys
import argparse

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.main_window
import moviemanager.ui.theme
import moviemanager.core.settings


#============================================
def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Movie media manager GUI"
	)
	parser.add_argument(
		'-d', '--directory', dest='directory', default='',
		help='Movie directory to open on launch'
	)
	parser.add_argument(
		'-c', '--config', dest='config_file', default='',
		help='Path to config YAML file'
	)
	args = parser.parse_args()
	return args


#============================================
def main():
	"""Launch the GUI application."""
	args = parse_args()
	settings = moviemanager.core.settings.load_settings(args.config_file)
	app = PySide6.QtWidgets.QApplication(sys.argv)
	app.setApplicationName("Movie Media Manager")
	app.setOrganizationName("MovieMediaManager")
	app.setOrganizationDomain("moviemediamanager.local")
	# apply saved theme preference
	moviemanager.ui.theme.apply_theme(app, settings.theme)
	window = moviemanager.ui.main_window.MainWindow(settings, args.directory)
	window.show()
	exit_code = app.exec()
	raise SystemExit(exit_code)


if __name__ == '__main__':
	main()
