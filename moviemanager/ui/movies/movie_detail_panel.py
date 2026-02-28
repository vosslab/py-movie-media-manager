"""Movie detail panel with info, artwork, and media file tabs."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore

# local repo modules
import moviemanager.ui.widgets.image_label


#============================================
class MovieDetailPanel(PySide6.QtWidgets.QTabWidget):
	"""Tabbed panel showing movie details."""

	def __init__(self, parent=None):
		super().__init__(parent)
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
		"""Create the info tab layout with metadata fields."""
		layout = PySide6.QtWidgets.QFormLayout(self._info_widget)
		self._title_label = PySide6.QtWidgets.QLabel()
		self._year_label = PySide6.QtWidgets.QLabel()
		self._rating_label = PySide6.QtWidgets.QLabel()
		self._director_label = PySide6.QtWidgets.QLabel()
		self._certification_label = PySide6.QtWidgets.QLabel()
		self._genres_label = PySide6.QtWidgets.QLabel()
		# plot text area - allow vertical growth (#22)
		self._plot_text = PySide6.QtWidgets.QTextEdit()
		self._plot_text.setReadOnly(True)
		self._plot_text.setMinimumHeight(80)
		self._plot_text.setMaximumHeight(300)
		layout.addRow("Title:", self._title_label)
		layout.addRow("Year:", self._year_label)
		layout.addRow("Rating:", self._rating_label)
		layout.addRow("Director:", self._director_label)
		layout.addRow("Certification:", self._certification_label)
		layout.addRow("Genres:", self._genres_label)
		layout.addRow("Plot:", self._plot_text)

	#============================================
	def _setup_artwork_tab(self):
		"""Create the artwork tab with poster and fanart labels."""
		layout = PySide6.QtWidgets.QHBoxLayout(self._artwork_widget)
		# poster
		self._poster_label = moviemanager.ui.widgets.image_label.ImageLabel()
		self._poster_label.setMinimumSize(200, 300)
		layout.addWidget(self._poster_label)
		# fanart
		self._fanart_label = moviemanager.ui.widgets.image_label.ImageLabel()
		self._fanart_label.setMinimumSize(300, 200)
		layout.addWidget(self._fanart_label)

	#============================================
	def _setup_media_tab(self):
		"""Create the media files tab with a table widget."""
		layout = PySide6.QtWidgets.QVBoxLayout(self._media_widget)
		self._media_table = PySide6.QtWidgets.QTableWidget()
		self._media_table.setColumnCount(4)
		self._media_table.setHorizontalHeaderLabels(
			["Filename", "Type", "Size", "Resolution"]
		)
		self._media_table.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
		)
		layout.addWidget(self._media_table)

	#============================================
	def set_movie(self, movie) -> None:
		"""Display details for the given movie."""
		if movie is None:
			self._clear()
			return
		self._title_label.setText(movie.title)
		self._year_label.setText(movie.year)
		rating_text = f"{movie.rating}/10" if movie.rating else ""
		self._rating_label.setText(rating_text)
		self._director_label.setText(movie.director)
		self._certification_label.setText(movie.certification)
		self._genres_label.setText(", ".join(movie.genres))
		self._plot_text.setText(movie.plot)
		# artwork - look for poster.jpg/fanart.jpg in movie path
		if movie.path:
			poster = os.path.join(movie.path, "poster.jpg")
			fanart = os.path.join(movie.path, "fanart.jpg")
			self._poster_label.set_image(poster)
			self._fanart_label.set_image(fanart)
		else:
			self._poster_label.set_image("")
			self._fanart_label.set_image("")
		# media files
		self._media_table.setRowCount(len(movie.media_files))
		for row, mf in enumerate(movie.media_files):
			self._media_table.setItem(
				row, 0,
				PySide6.QtWidgets.QTableWidgetItem(mf.filename)
			)
			self._media_table.setItem(
				row, 1,
				PySide6.QtWidgets.QTableWidgetItem(mf.file_type.value)
			)
			# calculate size in megabytes
			size_mb = mf.filesize / (1024 * 1024) if mf.filesize else 0
			size_text = f"{size_mb:.1f} MB" if size_mb > 0 else ""
			self._media_table.setItem(
				row, 2,
				PySide6.QtWidgets.QTableWidgetItem(size_text)
			)
			self._media_table.setItem(
				row, 3,
				PySide6.QtWidgets.QTableWidgetItem(mf.resolution_label)
			)

	#============================================
	def _clear(self) -> None:
		"""Clear all detail fields."""
		self._title_label.clear()
		self._year_label.clear()
		self._rating_label.clear()
		self._director_label.clear()
		self._certification_label.clear()
		self._genres_label.clear()
		self._plot_text.clear()
		self._poster_label.set_image("")
		self._fanart_label.set_image("")
		self._media_table.setRowCount(0)
