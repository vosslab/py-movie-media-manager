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
import moviemanager.ui.task_api
import moviemanager.ui.widgets.image_label
import moviemanager.ui.workers


#============================================
class ImageChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for browsing and downloading artwork."""

	def __init__(self, movie, artwork_urls: dict, parent=None):
		super().__init__(parent)
		self._movie = movie
		self._artwork_urls = artwork_urls
		self._pool = PySide6.QtCore.QThreadPool()
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
		self._download_btn = PySide6.QtWidgets.QPushButton(
			"Download Selected"
		)
		self._download_btn.clicked.connect(self._download_selected)
		left.addWidget(self._download_btn)
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
		"""Preview selected artwork URL by downloading thumbnail (#6)."""
		if row < 0:
			self._preview.clear()
			return
		art_type = self._type_combo.currentData()
		if not art_type:
			return
		urls = self._artwork_urls.get(art_type, [])
		if row >= len(urls):
			return
		url = urls[row]
		# show loading state
		self._preview.setText("Loading preview...")
		# download thumbnail in background thread (#1)
		worker = moviemanager.ui.workers.ImageDownloadWorker(url)
		worker.signals.finished.connect(self._on_preview_loaded)
		worker.signals.error.connect(self._on_preview_error)
		self._pool.start(worker, moviemanager.ui.task_api.PRIORITY_BACKGROUND)

	#============================================
	def _on_preview_loaded(self, image_bytes: bytes) -> None:
		"""Display downloaded preview image (#6)."""
		pixmap = PySide6.QtGui.QPixmap()
		pixmap.loadFromData(image_bytes)
		if pixmap.isNull():
			self._preview.setText("Failed to decode image")
			return
		# scale to fit preview area
		scaled = pixmap.scaled(
			self._preview.size(),
			PySide6.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
			PySide6.QtCore.Qt.TransformationMode.SmoothTransformation,
		)
		self._preview.setPixmap(scaled)

	#============================================
	def _on_preview_error(self, error_text: str) -> None:
		"""Handle preview download error."""
		self._preview.setText("Preview unavailable")

	#============================================
	def _download_selected(self) -> None:
		"""Download the selected artwork to the movie directory."""
		art_type = self._type_combo.currentData()
		row = self._url_list.currentRow()
		if not art_type or row < 0:
			PySide6.QtWidgets.QMessageBox.information(
				self, "No Selection",
				"Please select an artwork URL to download."
			)
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
		# check for existing file and confirm overwrite (#13)
		if os.path.exists(output_path):
			reply = PySide6.QtWidgets.QMessageBox.question(
				self, "Overwrite?",
				f"{output_name} already exists.\n"
				"Do you want to overwrite it?",
				PySide6.QtWidgets.QMessageBox.StandardButton.Yes
				| PySide6.QtWidgets.QMessageBox.StandardButton.No,
			)
			yes_btn = PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			if reply != yes_btn:
				return
		# download in background thread (#1)
		self._download_btn.setEnabled(False)
		self._download_btn.setText("Downloading...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		worker = moviemanager.ui.workers.Worker(
			self._do_download, url, output_path, output_name
		)
		worker.signals.finished.connect(self._on_download_done)
		worker.signals.error.connect(self._on_download_error)
		self._pool.start(worker, moviemanager.ui.task_api.PRIORITY_BACKGROUND)

	#============================================
	def _do_download(self, url: str, output_path: str, output_name: str) -> str:
		"""Download file in background thread with rate limiting."""
		# rate-limit the download request
		time.sleep(random.random())
		response = requests.get(url, timeout=30)
		if response.status_code != 200:
			raise RuntimeError(
				f"Download failed: HTTP {response.status_code}"
			)
		with open(output_path, "wb") as fh:
			fh.write(response.content)
		return output_name

	#============================================
	def _on_download_done(self, output_name) -> None:
		"""Handle successful download."""
		self.unsetCursor()
		self._download_btn.setEnabled(True)
		self._download_btn.setText("Download Selected")
		PySide6.QtWidgets.QMessageBox.information(
			self, "Downloaded",
			f"Saved to {output_name}"
		)

	#============================================
	def _on_download_error(self, error_text: str) -> None:
		"""Handle download error (#2)."""
		self.unsetCursor()
		self._download_btn.setEnabled(True)
		self._download_btn.setText("Download Selected")
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Download Error",
			f"Failed to download artwork:\n{error_text}"
		)
