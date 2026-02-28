#!/usr/bin/env python3
"""Movie media manager PySide6 GUI application."""

# Standard Library
import os
import sys
import signal
import argparse

# PIP3 modules
import PySide6.QtCore
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
	parser.add_argument(
		'-l', '--open-last', dest='open_last', action='store_true',
		help='Silently open the last used directory'
	)
	parser.set_defaults(open_last=False)
	args = parser.parse_args()
	return args


#============================================
def main():
	"""Launch the GUI application."""
	args = parse_args()
	settings = moviemanager.core.settings.load_settings(args.config_file)
	# resolve directory from --open-last flag
	directory = args.directory
	if not directory and args.open_last:
		last_dir = settings.last_directory
		if last_dir and os.path.isdir(last_dir):
			directory = last_dir
	app = PySide6.QtWidgets.QApplication(sys.argv)
	app.setApplicationName("Movie Media Manager")
	app.setOrganizationName("MovieMediaManager")
	app.setOrganizationDomain("moviemediamanager.local")
	# apply saved theme preference
	moviemanager.ui.theme.apply_theme(app, settings.theme)
	window = moviemanager.ui.main_window.MainWindow(settings, directory)
	window.show()
	# restore default Ctrl-C behavior so the OS can kill the process
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	# allow Python to process signals during Qt event loop
	signal_timer = PySide6.QtCore.QTimer()
	signal_timer.timeout.connect(lambda: None)
	signal_timer.start(200)
	exit_code = app.exec()
	raise SystemExit(exit_code)


if __name__ == '__main__':
	main()
