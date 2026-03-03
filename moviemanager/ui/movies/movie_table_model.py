"""Table model for the movie list."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui


# column 0 is the checkbox (empty header), then data columns
COLUMNS = ["", "Title", "Year", "Rating", "Mtch", "Org", "Art", "Sub", "Trl",
	"S&N", "V&G", "Prof", "A&D", "F&I"]

# status column indices and their movie attribute + full label
STATUS_COLUMNS = {
	4: ("scraped", "Matched"),
	5: ("is_organized", "Organized"),
	6: ("has_poster", "Artwork"),
	7: ("has_subtitle", "Subtitles"),
	8: ("has_trailer", "Trailer"),
}

# parental guide column indices, full category name, and short header
PG_COLUMNS = {
	9:  ("Sex & Nudity", "SN"),
	10: ("Violence & Gore", "VG"),
	11: ("Profanity", "Pr"),
	12: ("Alcohol, Drugs & Smoking", "AD"),
	13: ("Frightening & Intense Scenes", "FI"),
}

# severity ordinal mapping for sorting parental guide columns
SEVERITY_ORDER = {"None": 0, "Mild": 1, "Moderate": 2, "Severe": 3}


#============================================
class MovieTableModel(PySide6.QtCore.QAbstractTableModel):
	"""Table model displaying movie list data with checkbox column."""

	# emitted when check state changes (checked_count, total_count)
	checked_changed = PySide6.QtCore.Signal(int, int)

	def __init__(self, parent=None):
		super().__init__(parent)
		self._movies = []
		self._filtered = []
		self._filter_text = ""
		# set of movie ids that are checked (survives sorting)
		self._checked = set()
		# sort state
		self._sort_column = None
		self._sort_order = PySide6.QtCore.Qt.SortOrder.AscendingOrder

	#============================================
	def set_movies(self, movies: list) -> None:
		"""Replace the movie list."""
		self.beginResetModel()
		self._movies = list(movies)
		self._checked.clear()
		self._apply_filter()
		self.endResetModel()

	#============================================
	def refresh(self) -> None:
		"""Notify views that data changed without resetting the model.

		Use after metadata updates (scrape, edit, rename) when the
		movie list itself has not changed. Preserves selection,
		scroll position, and checked state.
		"""
		if not self._filtered:
			return
		top = self.index(0, 0)
		bottom = self.index(
			len(self._filtered) - 1, len(COLUMNS) - 1
		)
		self.dataChanged.emit(top, bottom)

	#============================================
	def append_movies(self, new_movies: list) -> None:
		"""Append movies incrementally without resetting the model.

		Adds new movies to the backing list and inserts matching rows
		into the filtered view so the table updates progressively.

		Args:
			new_movies: List of Movie objects to append.
		"""
		if not new_movies:
			return
		self._movies.extend(new_movies)
		# find which new movies pass the current filter
		matching = [m for m in new_movies if self._matches_filter(m)]
		if not matching:
			return
		# insert new rows at the end of the filtered list
		start = len(self._filtered)
		end = start + len(matching) - 1
		self.beginInsertRows(PySide6.QtCore.QModelIndex(), start, end)
		self._filtered.extend(matching)
		self.endInsertRows()

	#============================================
	def _matches_filter(self, movie) -> bool:
		"""Check if a movie matches the current filter text.

		Args:
			movie: Movie object to test.

		Returns:
			True if the movie matches or no filter is active.
		"""
		if not self._filter_text:
			return True
		# check title
		if self._filter_text in movie.title.lower():
			return True
		# check year
		if self._filter_text in movie.year.lower():
			return True
		# check genres
		genres_str = ", ".join(movie.genres).lower()
		if self._filter_text in genres_str:
			return True
		# check director
		if self._filter_text in movie.director.lower():
			return True
		return False

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
		else:
			self._filtered = [
				m for m in self._movies if self._matches_filter(m)
			]
		# re-apply sort after filtering
		if self._sort_column is not None:
			self._do_sort()

	#============================================
	def _do_sort(self) -> None:
		"""Sort self._filtered by current sort column and order."""
		col = self._sort_column
		reverse = (self._sort_order == PySide6.QtCore.Qt.SortOrder.DescendingOrder)
		if col == 0:
			# no sorting on checkbox column
			return
		if col == 1:
			key_func = lambda m: m.title.lower()
		elif col == 2:
			key_func = lambda m: m.year.lower()
		elif col == 3:
			key_func = lambda m: float(m.rating) if m.rating else 0.0
		elif col in STATUS_COLUMNS:
			attr_name = STATUS_COLUMNS[col][0]
			key_func = lambda m, a=attr_name: getattr(m, a, False)
		elif col in PG_COLUMNS:
			# sort by severity ordinal; missing data sorts to -1
			cat_name = PG_COLUMNS[col][0]
			key_func = lambda m, c=cat_name: SEVERITY_ORDER.get(
				m.parental_guide.get(c, ""), -1
			)
		else:
			return
		self._filtered.sort(key=key_func, reverse=reverse)

	#============================================
	def sort(self, column: int, order=None) -> None:
		"""Sort by the given column and order.

		Args:
			column: Column index to sort by.
			order: Qt.SortOrder (AscendingOrder or DescendingOrder).
		"""
		if order is None:
			order = PySide6.QtCore.Qt.SortOrder.AscendingOrder
		self._sort_column = column
		self._sort_order = order
		self.beginResetModel()
		self._do_sort()
		self.endResetModel()

	#============================================
	def get_movie(self, row: int):
		"""Get Movie object at row index."""
		if 0 <= row < len(self._filtered):
			return self._filtered[row]
		return None

	#============================================
	def check_all(self) -> None:
		"""Check all visible rows."""
		self._checked = {id(m) for m in self._filtered}
		# notify views the checkbox column changed
		top = self.index(0, 0)
		bottom = self.index(self.rowCount() - 1, 0)
		self.dataChanged.emit(top, bottom)
		self.checked_changed.emit(
			len(self._checked), len(self._filtered)
		)

	#============================================
	def uncheck_all(self) -> None:
		"""Uncheck all rows."""
		self._checked.clear()
		top = self.index(0, 0)
		bottom = self.index(self.rowCount() - 1, 0)
		self.dataChanged.emit(top, bottom)
		self.checked_changed.emit(0, len(self._filtered))

	#============================================
	def check_unscraped(self) -> None:
		"""Check only rows where movie is not yet scraped."""
		self._checked.clear()
		for movie in self._filtered:
			if not movie.scraped:
				self._checked.add(id(movie))
		top = self.index(0, 0)
		bottom = self.index(self.rowCount() - 1, 0)
		self.dataChanged.emit(top, bottom)
		self.checked_changed.emit(
			len(self._checked), len(self._filtered)
		)

	#============================================
	def get_checked_movies(self) -> list:
		"""Return list of checked Movie objects."""
		checked = []
		for movie in self._filtered:
			if id(movie) in self._checked:
				checked.append(movie)
		return checked

	#============================================
	def get_checked_count(self) -> int:
		"""Return number of checked rows."""
		return len(self._checked)

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
			# tooltip for status columns shows full name
			if role == PySide6.QtCore.Qt.ItemDataRole.ToolTipRole:
				if section in STATUS_COLUMNS:
					label = STATUS_COLUMNS[section][1]
					return label
				if section in PG_COLUMNS:
					full_name = PG_COLUMNS[section][0]
					return full_name
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
		movie = self._filtered[row]
		# checkbox column (col 0)
		if col == 0:
			if role == PySide6.QtCore.Qt.ItemDataRole.CheckStateRole:
				if id(movie) in self._checked:
					return PySide6.QtCore.Qt.CheckState.Checked
				return PySide6.QtCore.Qt.CheckState.Unchecked
			return None
		# status indicator columns (cols 4-8)
		if col in STATUS_COLUMNS:
			attr_name, label = STATUS_COLUMNS[col]
			flag_value = getattr(movie, attr_name, False)
			if role == PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
				# delegate paints the icon, no text needed
				return ""
			if role == PySide6.QtCore.Qt.ItemDataRole.UserRole:
				return flag_value
			if role == PySide6.QtCore.Qt.ItemDataRole.ToolTipRole:
				yes_no = "Yes" if flag_value else "No"
				tooltip = f"{label}: {yes_no}"
				return tooltip
			return None
		# parental guide columns (cols 9-13)
		if col in PG_COLUMNS:
			cat_name = PG_COLUMNS[col][0]
			severity = movie.parental_guide.get(cat_name, "")
			if role == PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
				# delegate paints the circle, no text needed
				return ""
			if role == PySide6.QtCore.Qt.ItemDataRole.UserRole:
				return severity
			if role == PySide6.QtCore.Qt.ItemDataRole.ToolTipRole:
				if severity:
					tooltip = f"{cat_name}: {severity}"
				else:
					tooltip = f"{cat_name}: No data"
				return tooltip
			return None
		# data columns use DisplayRole only
		if role != PySide6.QtCore.Qt.ItemDataRole.DisplayRole:
			return None
		if col == 1:
			return movie.title
		if col == 2:
			return movie.year
		if col == 3:
			if movie.rating:
				# show one decimal place for cleaner display
				formatted = f"{float(movie.rating):.1f}"
				return formatted
			return ""
		return None

	#============================================
	def setData(self, index, value, role=None):
		"""Handle checkbox toggle."""
		if role is None:
			role = PySide6.QtCore.Qt.ItemDataRole.EditRole
		if index.column() == 0:
			if role == PySide6.QtCore.Qt.ItemDataRole.CheckStateRole:
				movie = self._filtered[index.row()]
				if value == PySide6.QtCore.Qt.CheckState.Checked:
					self._checked.add(id(movie))
				else:
					self._checked.discard(id(movie))
				self.dataChanged.emit(index, index)
				self.checked_changed.emit(
					len(self._checked), len(self._filtered)
				)
				return True
		return False
