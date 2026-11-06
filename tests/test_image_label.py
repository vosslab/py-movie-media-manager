"""Unit tests for ImageLabel widget behavior."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtCore

# local repo modules
import moviemanager.ui.widgets.image_label


#============================================
def _make_png_bytes(width: int, height: int) -> bytes:
	"""Build PNG bytes for a solid-color image of the given size."""
	image = PySide6.QtGui.QImage(
		width,
		height,
		PySide6.QtGui.QImage.Format.Format_RGB32,
	)
	image.fill(PySide6.QtGui.QColor("red"))
	byte_array = PySide6.QtCore.QByteArray()
	buffer = PySide6.QtCore.QBuffer(byte_array)
	buffer.open(PySide6.QtCore.QIODevice.OpenModeFlag.WriteOnly)
	saved = image.save(buffer, "PNG")
	buffer.close()
	assert saved
	image_bytes = bytes(byte_array)
	return image_bytes


#============================================
def test_set_image_data_downscales_large_image(qtbot: object) -> None:
	"""Images larger than 4K on one side should be decoded at max 4096."""
	label = moviemanager.ui.widgets.image_label.ImageLabel()
	qtbot.addWidget(label)
	data = _make_png_bytes(5000, 100)
	label.set_image_data(data, source_url="https://example.com/large.png")
	assert label._pixmap is not None
	assert label._pixmap.width() == 4096
	assert 80 <= label._pixmap.height() <= 83
