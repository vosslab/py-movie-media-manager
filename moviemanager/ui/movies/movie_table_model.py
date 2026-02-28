"""Table model for the movie list."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui


# column 0 is the checkbox (empty header), then data columns
COLUMNS = ["", "Title", "Year", "Rating", "Status"]

# status indicator labels and descriptions
STATUS_STEPS = ["Scraped", "NFO", "Artwork"]


#============================================
class MovieTableModel(PySide6.QtCore.QAbstractTableModel):
	"""Table model displaying movie list data with checkbox column."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self._movies = []
		self._filtered = []
		self._filter_text = ""
		# set of row indices that are checked
		self._checked = set()

	#============================================
	def set_movies(self, movies: list) -> None:
		"""Replace the movie list."""
		self.beginResetModel()
		self._movies = list(movies)
		self._checked.clear()
		self._apply_filter()
		self.endResetModel()

	#============================================
	def set_filter(self, text: str) -> None:
		"""Filter movies by substring match (#10)."""
		self.beginResetModel()
		self._filter_text = text.lower()
		self._apply_filter()
		self.endResetModel()

	#============================================
	def _apply_filter(self) -> None:
		"""Apply current filter to movie list.

		Matches against title, year, genres, and director (#10).
		"""
		if not self._filter_text:
			self._filtered = list(self._movies)
			return
		filtered = []
		for m in self._movies:
			# check title
			if self._filter_text in m.title.lower():
				filtered.append(m)
				continue
			# check year
			if self._filter_text in m.year.lower():
				filtered.append(m)
				continue
			# check genres (joined as comma-separated string)
			genres_str = ", ".join(m.genres).lower()
			if self._filter_text in genres_str:
				filtered.append(m)
				continue
			# check director
			if self._filter_text in m.director.lower():
				filtered.append(m)
				continue
		self._filtered = filtered

	#============================================
	def get_movie(self, row: int):
		"""Get Movie object at row index."""
		if 0 <= row < len(self._filtered):
			return self._filtered[row]
		return None

	#============================================
	def check_all(self) -> None:
		"""Check all visible rows."""
		self._checked = set(range(len(self._filtered)))
		# notify views the checkbox column changed
		top = self.index(0, 0)
		bottom = self.index(self.rowCount() - 1, 0)
		self.dataChanged.emit(top, bottom)

	#============================================
	def uncheck_all(self) -> None:
		"""Uncheck all rows."""
		self._checked.clear()
		top = self.index(0, 0)
		bottom = self.index(self.rowCount() - 1, 0)
		self.dataChanged.emit(top, bottom)

	#============================================
	def check_unscraped(self) -> None:
		"""Check only rows where movie is not yet scraped."""
		self._checked.clear()
		for row, movie in enumerate(self._filtered):
			if not movie.scraped:
				self._checked.add(row)
		top = self.index(0, 0)
		bottom = self.index(self.rowCount() - 1, 0)
		self.dataChanged.emit(top, bottom)

	#============================================
	def get_checked_movies(self) -> list:
		"""Return list of checked Movie objects."""
		checked = []
		for row in sorted(self._checked):
			if 0 <= row < len(self._filtered):
				checked.append(self._filtered[row])
		return checked

	#============================================
	def get_checked_count(self) -> int:
		"""Return number of checked rows."""
		return len(self._checked)

	#============================================
	def _get_status_flags(self, movie) -> dict:
		"""Return dict of workflow status booleans for a movie.

		Args:
			movie: The Movie object to check.

		Returns:
			Dict with keys: scraped, nfo, artwork.
		"""
		flags = {
			"scraped": movie.scraped,
			"nfo": movie.has_nfo,
			"artwork": movie.has_poster,
		}
		return flags

	#============================================
	def _get_status_text(self, movie) -> str:
		"""Return compact status string with colored dot indicators.

		Args:
			movie: The Movie object to check.

		Returns:
			String like 'S N A' where each letter is present if done.
		"""
		flags = self._get_status_flags(movie)
		parts = []
		if flags["scraped"]:
			parts.append("S")
		else:
			parts.append("-")
		if flags["nfo"]:
			parts.append("N")
		else:
			parts.append("-")
		if flags["artwork"]:
			parts.append("A")
		else:
			parts.append("-")
		status_text = " ".join(parts)
		return status_text

	#============================================
	def _get_status_tooltip(self, movie) -> str:
		"""Return detailed tooltip text for the status column.

		Args:
			movie: The Movie object to check.

		Returns:
			Multi-line tooltip describing each workflow step.
		"""
		flags = self._get_status_flags(movie)
		yes_no = {True: "Yes", False: "No"}
		lines = [
			f"Scraped: {yes_no[flags['scraped']]}",
			f"NFO: {yes_no[flags['nfo']]}",
			f"Artwork: {yes_no[flags['artwork']]}",
		]
		tooltip = "\n".join(lines)
		return tooltip

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
	def flags(self, index):
		"""Return item flags; checkbox column is user-checkable."""
		base_flags = super().flags(index)
		if index.column() == 0:
			# checkbox column is checkable and enabled
			return (
				base_flags
				| PySide6.QtCore.Qt.ItemFlag.ItemIsUserCheckable
			)
		return base_flags

	#============================================
	def data(self, index, role=None):
		"""Return data for the given index and role."""
		if role is None:
			role = PySide6.QtCore.Qt.ItemDataRole.DisplayRole
		if not index.isValid():
			return None
		row = index.row()
		col = index.column()
		# checkbox column (col 0)
		if col == 0:
			if role == PySide6.QtCore.Qt.ItemDataRole.CheckStateRole:
				if row in self._checked:
					return PySide6.QtCore.Qt.CheckState.Checked
				return PySide6.QtCore.Qt.CheckState.Unchecked
			return None
		movie = self._filtered[row]
		# status column (col 4)
		if col == 4:
			if role == PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
				return self._get_status_text(movie)
			if role == PySide6.QtCore.Qt.ItemDataRole.ToolTipRole:
				return self._get_status_tooltip(movie)
			# color the status text based on completion
			if role == PySide6.QtCore.Qt.ItemDataRole.ForegroundRole:
				flags = self._get_status_flags(movie)
				all_done = all(flags.values())
				none_done = not any(flags.values())
				if all_done:
					return PySide6.QtGui.QColor("green")
				if none_done:
					return PySide6.QtGui.QColor("gray")
				return PySide6.QtGui.QColor("orange")
			return None
		# data columns use DisplayRole only
		if role != PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
			return None
		if col == 1:
			return movie.title
		if col == 2:
			return movie.year
		if col == 3:
			return str(movie.rating) if movie.rating else ""
		return None

	#============================================
	def setData(self, index, value, role=None):
		"""Handle checkbox toggle."""
		if role is None:
			role = PySide6.QtCore.Qt.ItemDataRole.EditRole
		if index.column() == 0:
			if role == PySide6.QtCore.Qt.ItemDataRole.CheckStateRole:
				row = index.row()
				if value == PySide6.QtCore.Qt.CheckState.Checked:
					self._checked.add(row)
				else:
					self._checked.discard(row)
				self.dataChanged.emit(index, index)
				return True
		return False
