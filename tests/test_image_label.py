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
def test_set_image_data_invalid_prints_source_url(qtbot, capsys):
	"""Invalid bytes should print source URL for CLI diagnostics."""
	label = moviemanager.ui.widgets.image_label.ImageLabel()
	qtbot.addWidget(label)
	url = "https://image.tmdb.org/t/p/w1280/example.jpg"
	label.set_image_data(b"not-an-image", source_url=url)
	captured = capsys.readouterr()
	assert f"Image decode failed for URL: {url}" in captured.out
	assert label.text() == "Invalid image"


#============================================
def test_scale_size_to_max_dimension_portrait():
	"""Portrait images should be constrained to max height 4096."""
	size = PySide6.QtCore.QSize(8268, 11811)
	scaled = moviemanager.ui.widgets.image_label._scale_size_to_max_dimension(
		size
	)
	assert scaled.height() == 4096
	assert 2800 < scaled.width() < 3000


#============================================
def test_set_image_data_downscales_large_image(qtbot):
	"""Images larger than 4K on one side should be decoded at max 4096."""
	label = moviemanager.ui.widgets.image_label.ImageLabel()
	qtbot.addWidget(label)
	data = _make_png_bytes(5000, 100)
	label.set_image_data(data, source_url="https://example.com/large.png")
	assert label._pixmap is not None
	assert label._pixmap.width() == 4096
	assert 80 <= label._pixmap.height() <= 83
