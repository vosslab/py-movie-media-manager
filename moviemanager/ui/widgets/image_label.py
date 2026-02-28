"""Artwork display widget with aspect-ratio scaling."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore


#============================================
class ImageLabel(PySide6.QtWidgets.QLabel):
	"""QLabel subclass that displays images with aspect-ratio scaling."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self._pixmap = None
		self.setMinimumSize(100, 150)
		self.setAlignment(PySide6.QtCore.Qt.AlignmentFlag.AlignCenter)

	#============================================
	def set_image(self, path: str) -> None:
		"""Load and display an image from file path."""
		if not path or not os.path.exists(path):
			# show placeholder text for missing artwork
			self._pixmap = None
			self.clear()
			self.setText("No artwork")
			# use palette placeholder color for the text
			self.setForegroundRole(
				PySide6.QtGui.QPalette.ColorRole.PlaceholderText
			)
			return
		self._pixmap = PySide6.QtGui.QPixmap(path)
		self._update_scaled()

	#============================================
	def set_image_data(self, data: bytes) -> None:
		"""Load and display an image from raw bytes.

		Args:
			data: Raw image bytes (e.g. from HTTP response).
		"""
		if not data:
			self._pixmap = None
			self.clear()
			self.setText("No artwork")
			self.setForegroundRole(
				PySide6.QtGui.QPalette.ColorRole.PlaceholderText
			)
			return
		pixmap = PySide6.QtGui.QPixmap()
		# load the raw image bytes into a QPixmap
		loaded = pixmap.loadFromData(data)
		if not loaded or pixmap.isNull():
			self._pixmap = None
			self.clear()
			self.setText("Invalid image")
			self.setForegroundRole(
				PySide6.QtGui.QPalette.ColorRole.PlaceholderText
			)
			return
		self._pixmap = pixmap
		self._update_scaled()

	#============================================
	def _update_scaled(self) -> None:
		"""Scale pixmap to fit label size."""
		if self._pixmap and not self._pixmap.isNull():
			scaled = self._pixmap.scaled(
				self.size(),
				PySide6.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
				PySide6.QtCore.Qt.TransformationMode.SmoothTransformation,
			)
			self.setPixmap(scaled)

	#============================================
	def resizeEvent(self, event):
		"""Re-scale image on resize."""
		self._update_scaled()
		super().resizeEvent(event)
