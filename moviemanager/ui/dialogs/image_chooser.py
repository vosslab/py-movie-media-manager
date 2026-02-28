"""Artwork browser and downloader dialog."""

# Standard Library
import os
import time
import random

# PIP3 modules
import requests
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.ui.widgets.image_label


#============================================
class ImageChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for browsing and downloading artwork."""

	def __init__(self, movie, artwork_urls: dict, parent=None):
		super().__init__(parent)
		self._movie = movie
		self._artwork_urls = artwork_urls
		self.setWindowTitle(f"Artwork - {movie.title}")
		self.resize(800, 600)
		self._setup_ui()
		self._load_artwork_list()

	#============================================
	def _setup_ui(self):
		"""Build the type selector, URL list, and preview."""
		layout = PySide6.QtWidgets.QHBoxLayout(self)
		# left: artwork type list and URL list
		left = PySide6.QtWidgets.QVBoxLayout()
		self._type_combo = PySide6.QtWidgets.QComboBox()
		self._type_combo.currentTextChanged.connect(
			self._on_type_changed
		)
		left.addWidget(self._type_combo)
		self._url_list = PySide6.QtWidgets.QListWidget()
		self._url_list.currentRowChanged.connect(
			self._on_url_selected
		)
		left.addWidget(self._url_list)
		# download button
		download_btn = PySide6.QtWidgets.QPushButton(
			"Download Selected"
		)
		download_btn.clicked.connect(self._download_selected)
		left.addWidget(download_btn)
		close_btn = PySide6.QtWidgets.QPushButton("Close")
		close_btn.clicked.connect(self.accept)
		left.addWidget(close_btn)
		layout.addLayout(left, 1)
		# right: image preview
		self._preview = (
			moviemanager.ui.widgets.image_label.ImageLabel()
		)
		self._preview.setMinimumSize(400, 400)
		layout.addWidget(self._preview, 2)

	#============================================
	def _load_artwork_list(self):
		"""Populate type combo from artwork_urls keys."""
		for art_type in sorted(self._artwork_urls.keys()):
			urls = self._artwork_urls[art_type]
			if urls:
				label = f"{art_type} ({len(urls)})"
				self._type_combo.addItem(label, art_type)

	#============================================
	def _on_type_changed(self, text: str) -> None:
		"""Update URL list when artwork type changes."""
		art_type = self._type_combo.currentData()
		if not art_type:
			return
		urls = self._artwork_urls.get(art_type, [])
		self._url_list.clear()
		for url in urls:
			# show just the filename part
			filename = url.split("/")[-1]
			self._url_list.addItem(filename)

	#============================================
	def _on_url_selected(self, row: int) -> None:
		"""Preview selected artwork URL."""
		# clear preview (downloading thumbnails would need async)
		self._preview.set_image("")

	#============================================
	def _download_selected(self) -> None:
		"""Download the selected artwork to the movie directory."""
		art_type = self._type_combo.currentData()
		row = self._url_list.currentRow()
		if not art_type or row < 0:
			return
		urls = self._artwork_urls.get(art_type, [])
		if row >= len(urls):
			return
		url = urls[row]
		if not self._movie.path:
			PySide6.QtWidgets.QMessageBox.warning(
				self, "Error", "Movie has no directory path."
			)
			return
		# determine output filename
		ext = ".jpg"
		if url.lower().endswith(".png"):
			ext = ".png"
		output_name = f"{art_type}{ext}"
		output_path = os.path.join(self._movie.path, output_name)
		# rate-limit the download request
		time.sleep(random.random())
		response = requests.get(url, timeout=30)
		if response.status_code == 200:
			with open(output_path, "wb") as fh:
				fh.write(response.content)
			PySide6.QtWidgets.QMessageBox.information(
				self, "Downloaded",
				f"Saved to {output_name}"
			)
		else:
			PySide6.QtWidgets.QMessageBox.warning(
				self, "Error",
				f"Download failed: HTTP {response.status_code}"
			)
