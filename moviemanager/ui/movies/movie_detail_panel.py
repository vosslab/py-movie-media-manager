"""Movie detail panel with info, artwork, and media file tabs."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import PySide6.QtCore

# local repo modules
import moviemanager.ui.format_movie
import moviemanager.ui.task_api
import moviemanager.ui.workers
import moviemanager.ui.widgets.image_label


MEDIA_COLUMNS = ["Filename", "Type", "Size", "Resolution"]


#============================================
class MediaFileTableModel(PySide6.QtCore.QAbstractTableModel):
	"""Table model for the media files list."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self._files = []

	#============================================
	def set_files(self, media_files: list) -> None:
		"""Replace the media file list."""
		self.beginResetModel()
		self._files = list(media_files)
		self.endResetModel()

	#============================================
	def rowCount(self, parent=None) -> int:
		"""Return number of rows."""
		return len(self._files)

	#============================================
	def columnCount(self, parent=None) -> int:
		"""Return number of columns."""
		return len(MEDIA_COLUMNS)

	#============================================
	def headerData(self, section, orientation, role=None):
		"""Return header data for the given section."""
		if role is None:
			role = PySide6.QtCore.Qt.ItemDataRole.DisplayRole
		if orientation == PySide6.QtCore.Qt.Orientation.Horizontal:
			if role == PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
				return MEDIA_COLUMNS[section]
		return None

	#============================================
	def data(self, index, role=None):
		"""Return data for the given index and role."""
		if role is None:
			role = PySide6.QtCore.Qt.ItemDataRole.DisplayRole
		if not index.isValid():
			return None
		if role != PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
			return None
		mf = self._files[index.row()]
		col = index.column()
		if col == 0:
			return mf.filename
		if col == 1:
			return mf.file_type.value
		if col == 2:
			# calculate size in megabytes
			size_mb = mf.filesize / (1024 * 1024) if mf.filesize else 0
			if size_mb > 0:
				return f"{size_mb:.1f} MB"
			return ""
		if col == 3:
			return mf.resolution_label
		return None


#============================================
class MovieDetailPanel(PySide6.QtWidgets.QTabWidget):
	"""Tabbed panel showing movie details."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self._pool = PySide6.QtCore.QThreadPool()
		# track in-flight image workers for cancellation
		self._poster_worker = None
		self._fanart_worker = None
		# Info tab
		self._info_widget = PySide6.QtWidgets.QWidget()
		self._setup_info_tab()
		self.addTab(self._info_widget, "Info")
		# Artwork tab
		self._artwork_widget = PySide6.QtWidgets.QWidget()
		self._setup_artwork_tab()
		self.addTab(self._artwork_widget, "Artwork")
		# Media Files tab
		self._media_widget = PySide6.QtWidgets.QWidget()
		self._setup_media_tab()
		self.addTab(self._media_widget, "Media Files")

	#============================================
	def _setup_info_tab(self):
		"""Create the info tab with poster on top and compact info below."""
		layout = PySide6.QtWidgets.QVBoxLayout(self._info_widget)
		# poster image at the top
		self._info_poster_label = moviemanager.ui.widgets.image_label.ImageLabel()
		self._info_poster_label.setMinimumSize(200, 300)
		self._info_poster_label.setMaximumWidth(250)
		layout.addWidget(
			self._info_poster_label,
			alignment=PySide6.QtCore.Qt.AlignmentFlag.AlignHCenter,
		)
		# compact form with key fields below the poster
		form = PySide6.QtWidgets.QFormLayout()
		self._title_label = PySide6.QtWidgets.QLabel()
		self._title_label.setWordWrap(True)
		self._year_label = PySide6.QtWidgets.QLabel()
		self._rating_label = PySide6.QtWidgets.QLabel()
		self._director_label = PySide6.QtWidgets.QLabel()
		self._director_label.setWordWrap(True)
		self._certification_label = PySide6.QtWidgets.QLabel()
		self._genres_label = PySide6.QtWidgets.QLabel()
		self._genres_label.setWordWrap(True)
		form.addRow("Title:", self._title_label)
		form.addRow("Year:", self._year_label)
		form.addRow("Rating:", self._rating_label)
		form.addRow("Director:", self._director_label)
		form.addRow("Cert:", self._certification_label)
		form.addRow("Genres:", self._genres_label)
		layout.addLayout(form)
		# plot text area at the bottom, fills remaining space
		self._plot_text = PySide6.QtWidgets.QTextEdit()
		self._plot_text.setReadOnly(True)
		self._plot_text.setMinimumHeight(60)
		self._plot_text.setPlaceholderText("No plot available")
		layout.addWidget(self._plot_text, stretch=1)
		# show empty state placeholder
		self._title_label.setText("No movie selected")

	#============================================
	def _setup_artwork_tab(self):
		"""Create the artwork tab with fanart label."""
		layout = PySide6.QtWidgets.QHBoxLayout(self._artwork_widget)
		# fanart only (poster is now on the Info tab)
		self._fanart_label = moviemanager.ui.widgets.image_label.ImageLabel()
		self._fanart_label.setMinimumSize(300, 200)
		layout.addWidget(self._fanart_label)

	#============================================
	def _setup_media_tab(self):
		"""Create the media files tab with a QTableView and model (#21)."""
		layout = PySide6.QtWidgets.QVBoxLayout(self._media_widget)
		self._media_model = MediaFileTableModel()
		self._media_view = PySide6.QtWidgets.QTableView()
		self._media_view.setModel(self._media_model)
		self._media_view.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionBehavior.SelectRows
		)
		self._media_view.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView
			.EditTrigger.NoEditTriggers
		)
		# stretch the last column
		header = self._media_view.horizontalHeader()
		header.setStretchLastSection(True)
		layout.addWidget(self._media_view)

	#============================================
	def set_movie(self, movie) -> None:
		"""Display details for the given movie."""
		if movie is None:
			self._clear()
			return
		# cancel any in-flight image loads
		self._cancel_image_workers()
		# format all display fields via shared formatter
		fields = moviemanager.ui.format_movie.format_movie_fields(movie)
		self._title_label.setText(fields["title"])
		self._year_label.setText(fields["year"])
		self._rating_label.setText(fields["rating"])
		self._director_label.setText(fields["director"])
		self._certification_label.setText(fields["certification"])
		self._genres_label.setText(fields["genres"])
		self._plot_text.setText(fields["plot"])
		# artwork - load async to avoid blocking the main thread
		if movie.path:
			poster = os.path.join(movie.path, "poster.jpg")
			fanart = os.path.join(movie.path, "fanart.jpg")
			# poster goes on Info tab now
			self._load_image_async(
				poster, self._info_poster_label, "poster"
			)
			self._load_image_async(
				fanart, self._fanart_label, "fanart"
			)
		else:
			self._info_poster_label.set_image("")
			self._fanart_label.set_image("")
		# media files via model
		self._media_model.set_files(movie.media_files)

	#============================================
	def _load_image_async(
		self, path: str,
		label: moviemanager.ui.widgets.image_label.ImageLabel,
		tag: str,
	) -> None:
		"""Load an image from disk in a background thread.

		Args:
			path: File path to load.
			label: ImageLabel widget to display the image.
			tag: "poster" or "fanart" for worker tracking.
		"""
		if not path or not os.path.exists(path):
			label.set_image("")
			return
		# read file bytes in background thread
		worker = moviemanager.ui.workers.Worker(
			self._read_file_bytes, path,
		)
		worker.signals.finished.connect(
			lambda data, lbl=label: lbl.set_image_data(data)
		)
		worker.signals.error.connect(
			lambda _err, lbl=label: lbl.set_image("")
		)
		# track worker for cancellation
		if tag == "poster":
			self._poster_worker = worker
		else:
			self._fanart_worker = worker
		self._pool.start(worker, moviemanager.ui.task_api.PRIORITY_BACKGROUND)

	#============================================
	@staticmethod
	def _read_file_bytes(path: str) -> bytes:
		"""Read a file into bytes (runs in worker thread).

		Args:
			path: Absolute file path to read.

		Returns:
			Raw file bytes.
		"""
		with open(path, "rb") as f:
			data = f.read()
		return data

	#============================================
	def _cancel_image_workers(self) -> None:
		"""Cancel any in-flight image loading workers."""
		if self._poster_worker is not None:
			self._poster_worker.cancel()
			self._poster_worker = None
		if self._fanart_worker is not None:
			self._fanart_worker.cancel()
			self._fanart_worker = None

	#============================================
	def _clear(self) -> None:
		"""Clear all detail fields and show empty state."""
		self._title_label.setText("No movie selected")
		self._year_label.clear()
		self._rating_label.clear()
		self._director_label.clear()
		self._certification_label.clear()
		self._genres_label.clear()
		self._plot_text.clear()
		self._info_poster_label.set_image("")
		self._fanart_label.set_image("")
		self._media_model.set_files([])
