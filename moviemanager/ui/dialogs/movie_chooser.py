"""TMDB search results chooser dialog."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore


#============================================
class MovieChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for searching TMDB and selecting a match."""

	def __init__(self, movie, api, parent=None):
		super().__init__(parent)
		self._movie = movie
		self._api = api
		self._selected_result = None
		self._results = []
		self.setWindowTitle(f"Scrape - {movie.title}")
		self.resize(700, 500)
		self._setup_ui()
		# auto-search with current title
		self._search_field.setText(movie.title)
		if movie.year:
			self._year_field.setText(movie.year)
		self._do_search()

	#============================================
	def _setup_ui(self):
		"""Build the search bar, results table, and buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# search bar
		search_layout = PySide6.QtWidgets.QHBoxLayout()
		self._search_field = PySide6.QtWidgets.QLineEdit()
		self._search_field.setPlaceholderText("Movie title...")
		search_layout.addWidget(self._search_field)
		self._year_field = PySide6.QtWidgets.QLineEdit()
		self._year_field.setPlaceholderText("Year")
		self._year_field.setMaximumWidth(80)
		search_layout.addWidget(self._year_field)
		search_btn = PySide6.QtWidgets.QPushButton("Search")
		search_btn.clicked.connect(self._do_search)
		search_layout.addWidget(search_btn)
		layout.addLayout(search_layout)
		# results table
		self._results_table = PySide6.QtWidgets.QTableWidget()
		self._results_table.setColumnCount(5)
		self._results_table.setHorizontalHeaderLabels(
			["Title", "Year", "TMDB ID", "Rating", "Overview"]
		)
		self._results_table.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionBehavior.SelectRows
		)
		self._results_table.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView
			.EditTrigger.NoEditTriggers
		)
		self._results_table.horizontalHeader().setStretchLastSection(
			True
		)
		self._results_table.doubleClicked.connect(
			self._on_double_click
		)
		layout.addWidget(self._results_table)
		# buttons
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		ok_btn = PySide6.QtWidgets.QPushButton("Scrape Selected")
		ok_btn.clicked.connect(self._accept_selection)
		btn_layout.addWidget(ok_btn)
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(cancel_btn)
		layout.addLayout(btn_layout)

	#============================================
	def _do_search(self):
		"""Search TMDB with current text."""
		title = self._search_field.text().strip()
		year = self._year_field.text().strip()
		if not title:
			return
		results = self._api.search_movie(title, year)
		self._results = results
		self._results_table.setRowCount(len(results))
		for row, result in enumerate(results):
			self._results_table.setItem(
				row, 0,
				PySide6.QtWidgets.QTableWidgetItem(result.title)
			)
			self._results_table.setItem(
				row, 1,
				PySide6.QtWidgets.QTableWidgetItem(result.year)
			)
			self._results_table.setItem(
				row, 2,
				PySide6.QtWidgets.QTableWidgetItem(
					str(result.tmdb_id)
				)
			)
			score_text = str(result.score) if result.score else ""
			self._results_table.setItem(
				row, 3,
				PySide6.QtWidgets.QTableWidgetItem(score_text)
			)
			# truncate overview for display
			overview = result.overview
			if len(overview) > 100:
				overview = overview[:100] + "..."
			self._results_table.setItem(
				row, 4,
				PySide6.QtWidgets.QTableWidgetItem(overview)
			)
		self._results_table.resizeColumnsToContents()

	#============================================
	def _accept_selection(self):
		"""Accept the selected result and scrape."""
		row = self._results_table.currentRow()
		if row < 0 or row >= len(self._results):
			PySide6.QtWidgets.QMessageBox.warning(
				self, "No Selection",
				"Please select a search result."
			)
			return
		result = self._results[row]
		# scrape the movie with the selected TMDB ID
		self._api.scrape_movie(self._movie, tmdb_id=result.tmdb_id)
		self.accept()

	#============================================
	def _on_double_click(self, index):
		"""Double-click a result to accept it."""
		self._accept_selection()
