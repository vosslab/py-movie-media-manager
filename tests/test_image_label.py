#!/usr/bin/env python3
"""Unit tests for ImageLabel widget behavior."""

# local repo modules
import moviemanager.ui.widgets.image_label


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
