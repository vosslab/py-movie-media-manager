"""Artwork display widget with aspect-ratio scaling."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtGui
import PySide6.QtCore

_MAX_IMAGE_DIMENSION = 4096


#============================================
def _scale_size_to_max_dimension(
	size: PySide6.QtCore.QSize, max_dimension: int = _MAX_IMAGE_DIMENSION
) -> PySide6.QtCore.QSize:
	"""Return a size constrained so the largest dimension is max_dimension."""
	if not size.isValid():
		return size
	if max_dimension <= 0:
		return size
	width = size.width()
	height = size.height()
	largest = max(width, height)
	if largest <= max_dimension:
		return size
	scale = max_dimension / float(largest)
	scaled_width = max(1, int(round(width * scale)))
	scaled_height = max(1, int(round(height * scale)))
	if width >= height:
		scaled_width = max_dimension
	else:
		scaled_height = max_dimension
	scaled_size = PySide6.QtCore.QSize(scaled_width, scaled_height)
	return scaled_size


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
			self._show_placeholder("No artwork")
			return
		reader = PySide6.QtGui.QImageReader(path)
		reader.setAutoTransform(True)
		self._pixmap = self._read_pixmap(reader)
		if self._pixmap is None:
			self._show_placeholder("Invalid image")
			return
		self._update_scaled()

	#============================================
	def set_image_data(self, data: bytes, source_url: str = "") -> None:
		"""Load and display an image from raw bytes.

		Args:
			data: Raw image bytes (e.g. from HTTP response).
			source_url: Optional URL used for CLI diagnostics on decode failure.
		"""
		if not data:
			self._show_placeholder("No artwork")
			return
		byte_array = PySide6.QtCore.QByteArray(data)
		buffer = PySide6.QtCore.QBuffer(byte_array)
		buffer.open(PySide6.QtCore.QIODevice.OpenModeFlag.ReadOnly)
		reader = PySide6.QtGui.QImageReader(buffer)
		reader.setAutoTransform(True)
		self._pixmap = self._read_pixmap(reader)
		buffer.close()
		if self._pixmap is None:
			if source_url:
				print(f"Image decode failed for URL: {source_url}")
			self._show_placeholder("Invalid image")
			return
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
	def _show_placeholder(self, text: str) -> None:
		"""Show placeholder text and clear any loaded pixmap."""
		self._pixmap = None
		self.clear()
		self.setText(text)
		self.setForegroundRole(
			PySide6.QtGui.QPalette.ColorRole.PlaceholderText
		)

	#============================================
	def _read_pixmap(
		self, reader: PySide6.QtGui.QImageReader
	) -> PySide6.QtGui.QPixmap | None:
		"""Decode an image reader with max-dimension scaling."""
		image_size = reader.size()
		if image_size.isValid():
			scaled_size = _scale_size_to_max_dimension(image_size)
			if scaled_size != image_size:
				reader.setScaledSize(scaled_size)
		image = reader.read()
		if image.isNull():
			return None
		pixmap = PySide6.QtGui.QPixmap.fromImage(image)
		if pixmap.isNull():
			return None
		return pixmap

	#============================================
	def resizeEvent(self, event):
		"""Re-scale image on resize."""
		self._update_scaled()
		super().resizeEvent(event)
