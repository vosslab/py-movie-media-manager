"""Table model for the movie list."""

# PIP3 modules
import PySide6.QtCore


COLUMNS = ["Title", "Year", "Rating", "NFO", "Scraped"]


#============================================
class MovieTableModel(PySide6.QtCore.QAbstractTableModel):
	"""Table model displaying movie list data."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self._movies = []
		self._filtered = []
		self._filter_text = ""

	#============================================
	def set_movies(self, movies: list) -> None:
		"""Replace the movie list."""
		self.beginResetModel()
		self._movies = list(movies)
		self._apply_filter()
		self.endResetModel()

	#============================================
	def set_filter(self, text: str) -> None:
		"""Filter movies by title substring."""
		self.beginResetModel()
		self._filter_text = text.lower()
		self._apply_filter()
		self.endResetModel()

	#============================================
	def _apply_filter(self) -> None:
		"""Apply current filter to movie list."""
		if not self._filter_text:
			self._filtered = list(self._movies)
		else:
			self._filtered = [
				m for m in self._movies
				if self._filter_text in m.title.lower()
			]

	#============================================
	def get_movie(self, row: int):
		"""Get Movie object at row index."""
		if 0 <= row < len(self._filtered):
			return self._filtered[row]
		return None

	#============================================
	def rowCount(self, parent=None) -> int:
		"""Return number of rows."""
		return len(self._filtered)

	#============================================
	def columnCount(self, parent=None) -> int:
		"""Return number of columns."""
		return len(COLUMNS)

	#============================================
	def headerData(self, section, orientation, role=None):
		"""Return header data for the given section."""
		if role is None:
			role = PySide6.QtCore.Qt.ItemDataRole.DisplayRole
		if orientation == PySide6.QtCore.Qt.Orientation.Horizontal:
			if role == PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
				return COLUMNS[section]
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
		movie = self._filtered[index.row()]
		col = index.column()
		if col == 0:
			return movie.title
		if col == 1:
			return movie.year
		if col == 2:
			return str(movie.rating) if movie.rating else ""
		if col == 3:
			return "Yes" if movie.has_nfo else "No"
		if col == 4:
			return "Yes" if movie.scraped else "No"
		return None
