"""Pre-match card widget showing existing movie match metadata."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.format_movie
import moviemanager.ui.task_api
import moviemanager.ui.widgets.image_label
import moviemanager.ui.workers


#============================================
class PrematchWidget(PySide6.QtWidgets.QFrame):
	"""Card-style widget showing an existing movie match.

	Displays poster, metadata fields, and a "Find Different Match"
	button. Emits rematch_requested when the user wants to search
	for a different match.

	Args:
		parent: Parent widget.
	"""

	# emitted when user clicks "Find Different Match"
	rematch_requested = PySide6.QtCore.Signal()

	def __init__(self, parent=None):
		super().__init__(parent)
		self._setup_ui()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the prematch card layout with poster and metadata."""
		# card-style frame with raised border for visual distinction
		self.setFrameShape(
			PySide6.QtWidgets.QFrame.Shape.StyledPanel
		)
		self.setFrameShadow(
			PySide6.QtWidgets.QFrame.Shadow.Raised
		)
		outer = PySide6.QtWidgets.QVBoxLayout(self)
		# banner row with checkmark icon
		banner_layout = PySide6.QtWidgets.QHBoxLayout()
		check_icon = self.style().standardIcon(
			PySide6.QtWidgets.QStyle
			.StandardPixmap.SP_DialogApplyButton
		)
		icon_label = PySide6.QtWidgets.QLabel()
		icon_label.setPixmap(check_icon.pixmap(20, 20))
		banner_layout.addWidget(icon_label)
		banner_text = PySide6.QtWidgets.QLabel("Existing Match")
		banner_font = banner_text.font()
		banner_font.setBold(True)
		banner_font.setPointSize(banner_font.pointSize() + 1)
		banner_text.setFont(banner_font)
		banner_layout.addWidget(banner_text)
		banner_layout.addStretch()
		outer.addLayout(banner_layout)
		# content: poster on left, metadata on right
		content_layout = PySide6.QtWidgets.QHBoxLayout()
		# left side: poster
		self._poster = (
			moviemanager.ui.widgets.image_label.ImageLabel()
		)
		self._poster.setMinimumSize(180, 270)
		self._poster.setText("No poster")
		content_layout.addWidget(self._poster)
		# right side: title + form layout + plot + button
		right_layout = PySide6.QtWidgets.QVBoxLayout()
		# title label (bold, larger font)
		self._title_label = PySide6.QtWidgets.QLabel("")
		title_font = self._title_label.font()
		title_font.setBold(True)
		title_font.setPointSize(title_font.pointSize() + 2)
		self._title_label.setFont(title_font)
		self._title_label.setWordWrap(True)
		right_layout.addWidget(self._title_label)
		# metadata form layout (follows MovieDetailPanel pattern)
		form = PySide6.QtWidgets.QFormLayout()
		self._year_label = PySide6.QtWidgets.QLabel("")
		form.addRow("Year:", self._year_label)
		self._rating_label = PySide6.QtWidgets.QLabel("")
		form.addRow("Rating:", self._rating_label)
		self._director_label = PySide6.QtWidgets.QLabel("")
		form.addRow("Director:", self._director_label)
		self._cert_label = PySide6.QtWidgets.QLabel("")
		form.addRow("Certification:", self._cert_label)
		self._genres_label = PySide6.QtWidgets.QLabel("")
		form.addRow("Genres:", self._genres_label)
		self._runtime_label = PySide6.QtWidgets.QLabel("")
		form.addRow("Runtime:", self._runtime_label)
		self._ids_label = PySide6.QtWidgets.QLabel("")
		form.addRow("IDs:", self._ids_label)
		right_layout.addLayout(form)
		# plot text area (read-only, max height 100px)
		self._plot_text = PySide6.QtWidgets.QTextEdit()
		self._plot_text.setReadOnly(True)
		self._plot_text.setMaximumHeight(100)
		self._plot_text.setFrameShape(
			PySide6.QtWidgets.QFrame.Shape.NoFrame
		)
		right_layout.addWidget(self._plot_text)
		# "Find Different Match" button
		self._rematch_btn = PySide6.QtWidgets.QPushButton(
			"Find Different Match"
		)
		self._rematch_btn.setToolTip(
			"Search for a different match for this movie"
		)
		self._rematch_btn.clicked.connect(
			self.rematch_requested.emit
		)
		right_layout.addWidget(
			self._rematch_btn,
			alignment=(
				PySide6.QtCore.Qt.AlignmentFlag.AlignLeft
			),
		)
		right_layout.addStretch()
		content_layout.addLayout(right_layout, stretch=1)
		outer.addLayout(content_layout, stretch=1)

	#============================================
	def show_movie(self, movie, task_api) -> None:
		"""Populate the card with existing movie metadata.

		Args:
			movie: Movie instance with scraped metadata.
			task_api: TaskAPI for submitting poster download jobs.
		"""
		# format all display fields via shared formatter
		fields = moviemanager.ui.format_movie.format_movie_fields(
			movie
		)
		# populate labels (title falls back to "Unknown")
		self._title_label.setText(fields["title"] or "Unknown")
		self._year_label.setText(fields["year"])
		self._rating_label.setText(fields["rating"])
		self._director_label.setText(fields["director"])
		self._cert_label.setText(fields["certification"])
		self._genres_label.setText(fields["genres"])
		self._runtime_label.setText(fields["runtime"])
		self._ids_label.setText(fields["ids"])
		self._plot_text.setPlainText(fields["plot"])
		# load poster from disk cache or download
		cached_poster = _get_movie_poster_path(movie)
		if cached_poster and os.path.isfile(cached_poster):
			self._poster.set_image(cached_poster)
		elif movie.poster_url:
			self._poster.setText("Loading...")
			cache_path = cached_poster
			task_id = task_api.submit(
				moviemanager.ui.workers.download_image_bytes,
				movie.poster_url,
				_priority=(
					moviemanager.ui.task_api.PRIORITY_BACKGROUND
				),
			)
			worker = task_api.get_worker(task_id)
			worker.signals.finished.connect(
				lambda data, url=movie.poster_url,
				cp=cache_path:
				self._on_poster_downloaded(data, url, cp)
			)
			worker.signals.error.connect(
				lambda _: self._poster.setText("No poster")
			)
		else:
			self._poster.set_image_data(None)

	#============================================
	def _on_poster_downloaded(
		self, data: bytes, source_url: str,
		cache_path: str,
	) -> None:
		"""Display downloaded poster and cache it to disk.

		Args:
			data: Raw image bytes from the download worker.
			source_url: Poster URL for decode-failure diagnostics.
			cache_path: Local path to save the poster.
		"""
		self._poster.set_image_data(
			data, source_url=source_url
		)
		# cache poster to disk for instant load next time
		if data and cache_path:
			parent_dir = os.path.dirname(cache_path)
			if os.path.isdir(parent_dir):
				with open(cache_path, "wb") as f:
					f.write(data)


#============================================
def _get_movie_poster_path(movie) -> str:
	"""Find existing poster or build a movie-specific cache path.

	Checks for an existing poster.jpg first (the standard download
	location), then returns a movie-specific cache path using the
	video file basename plus '.poster.jpg'.

	Args:
		movie: Movie instance with video_file and path.

	Returns:
		Full path to the poster file, or empty string.
	"""
	if not movie.path:
		return ""
	# check for standard poster.jpg first
	standard_poster = os.path.join(movie.path, "poster.jpg")
	if os.path.isfile(standard_poster):
		return standard_poster
	# build movie-specific cache path from video filename
	video = movie.video_file
	if not video or not video.filename:
		return ""
	# strip the video extension and append .poster.jpg
	basename = os.path.splitext(video.filename)[0]
	poster_name = f"{basename}.poster.jpg"
	poster_path = os.path.join(movie.path, poster_name)
	return poster_path
