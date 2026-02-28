"""Main movie panel with table and detail splitter."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore

# local repo modules
import moviemanager.ui.movies.movie_table_model
import moviemanager.ui.movies.movie_detail_panel
import moviemanager.ui.widgets.search_field


#============================================
class MoviePanel(PySide6.QtWidgets.QWidget):
	"""Main movie view with search, table, and detail panel."""

	def __init__(self, parent=None):
		super().__init__(parent)
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# search field
		self._search = moviemanager.ui.widgets.search_field.SearchField()
		layout.addWidget(self._search)
		# splitter: table on left, detail on right
		self._splitter = PySide6.QtWidgets.QSplitter(
			PySide6.QtCore.Qt.Orientation.Horizontal
		)
		# table view
		self._table_view = PySide6.QtWidgets.QTableView()
		self._table_model = (
			moviemanager.ui.movies.movie_table_model.MovieTableModel()
		)
		self._table_view.setModel(self._table_model)
		self._table_view.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
		)
		self._table_view.setSelectionMode(
			PySide6.QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
		)
		self._table_view.setSortingEnabled(True)
		# allow user to manually resize columns (#17)
		header = self._table_view.horizontalHeader()
		header.setStretchLastSection(True)
		header.setSectionResizeMode(
			PySide6.QtWidgets.QHeaderView.ResizeMode.Interactive
		)
		self._splitter.addWidget(self._table_view)
		# detail panel
		self._detail = (
			moviemanager.ui.movies.movie_detail_panel.MovieDetailPanel()
		)
		self._splitter.addWidget(self._detail)
		# set splitter sizes (60% table, 40% detail)
		self._splitter.setSizes([600, 400])
		layout.addWidget(self._splitter)
		# connect signals
		self._search.filter_changed.connect(self._on_filter)
		selection_model = self._table_view.selectionModel()
		selection_model.currentRowChanged.connect(self._on_row_changed)

	#============================================
	def set_movies(self, movies: list) -> None:
		"""Load movies into the table."""
		self._table_model.set_movies(movies)
		# auto-resize columns to fit content
		self._table_view.resizeColumnsToContents()

	#============================================
	def get_selected_movie(self):
		"""Get the currently selected movie."""
		index = self._table_view.currentIndex()
		if index.isValid():
			movie = self._table_model.get_movie(index.row())
			return movie
		return None

	#============================================
	def _on_filter(self, text: str) -> None:
		"""Apply search filter."""
		self._table_model.set_filter(text)

	#============================================
	def _on_row_changed(self, current, previous) -> None:
		"""Update detail panel when selection changes."""
		movie = self._table_model.get_movie(current.row())
		self._detail.set_movie(movie)
