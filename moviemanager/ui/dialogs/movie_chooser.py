"""TMDB search results chooser dialog."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore

# local repo modules
import moviemanager.ui.workers


#============================================
class MovieChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for searching TMDB and selecting a match."""

	def __init__(self, movie, api, parent=None):
		super().__init__(parent)
		self._movie = movie
		self._api = api
		self._selected_result = None
		self._results = []
		self._pool = PySide6.QtCore.QThreadPool()
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
		# connect Enter key to search (#4)
		self._search_field.returnPressed.connect(self._do_search)
		search_layout.addWidget(self._search_field)
		self._year_field = PySide6.QtWidgets.QLineEdit()
		self._year_field.setPlaceholderText("Year")
		self._year_field.setMaximumWidth(80)
		# connect Enter key on year field too (#4)
		self._year_field.returnPressed.connect(self._do_search)
		search_layout.addWidget(self._year_field)
		self._search_btn = PySide6.QtWidgets.QPushButton("Search")
		self._search_btn.clicked.connect(self._do_search)
		search_layout.addWidget(self._search_btn)
		layout.addLayout(search_layout)
		# no-results label (hidden by default) (#11)
		self._no_results_label = PySide6.QtWidgets.QLabel(
			"No results found. Try a different search."
		)
		self._no_results_label.setAlignment(
			PySide6.QtCore.Qt.AlignmentFlag.AlignCenter
		)
		self._no_results_label.hide()
		layout.addWidget(self._no_results_label)
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
		# elide overview text and show full text in tooltip
		self._results_table.setWordWrap(False)
		self._results_table.doubleClicked.connect(
			self._on_double_click
		)
		layout.addWidget(self._results_table)
		# buttons
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		self._ok_btn = PySide6.QtWidgets.QPushButton("Scrape Selected")
		self._ok_btn.clicked.connect(self._accept_selection)
		btn_layout.addWidget(self._ok_btn)
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(cancel_btn)
		layout.addLayout(btn_layout)

	#============================================
	def _do_search(self):
		"""Search TMDB with current text in a background thread."""
		title = self._search_field.text().strip()
		year = self._year_field.text().strip()
		if not title:
			return
		# disable search button while working
		self._search_btn.setEnabled(False)
		self._search_btn.setText("Searching...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# run search in background thread (#1)
		worker = moviemanager.ui.workers.Worker(
			self._api.search_movie, title, year
		)
		worker.signals.finished.connect(self._on_search_done)
		worker.signals.error.connect(self._on_search_error)
		self._pool.start(worker)

	#============================================
	def _on_search_done(self, results) -> None:
		"""Handle search results from background thread."""
		self.unsetCursor()
		self._search_btn.setEnabled(True)
		self._search_btn.setText("Search")
		self._results = results
		self._results_table.setRowCount(len(results))
		# show/hide no-results label (#11)
		if not results:
			self._no_results_label.show()
			self._results_table.hide()
			return
		self._no_results_label.hide()
		self._results_table.show()
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
			# show truncated overview with full text in tooltip
			overview = result.overview
			overview_item = PySide6.QtWidgets.QTableWidgetItem(
				overview
			)
			overview_item.setToolTip(overview)
			self._results_table.setItem(row, 4, overview_item)
		self._results_table.resizeColumnsToContents()

	#============================================
	def _on_search_error(self, error_text: str) -> None:
		"""Handle search error from background thread (#2)."""
		self.unsetCursor()
		self._search_btn.setEnabled(True)
		self._search_btn.setText("Search")
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Search Error",
			f"TMDB search failed:\n{error_text}"
		)

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
		# scrape in background thread (#1)
		self._ok_btn.setEnabled(False)
		self._ok_btn.setText("Scraping...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# pass imdb_id when using IMDB provider (tmdb_id will be 0)
		scrape_kwargs = {}
		if result.tmdb_id:
			scrape_kwargs["tmdb_id"] = result.tmdb_id
		elif result.imdb_id:
			scrape_kwargs["imdb_id"] = result.imdb_id
		worker = moviemanager.ui.workers.Worker(
			self._api.scrape_movie,
			self._movie, **scrape_kwargs
		)
		worker.signals.finished.connect(self._on_scrape_done)
		worker.signals.error.connect(self._on_scrape_error)
		self._pool.start(worker)

	#============================================
	def _on_scrape_done(self, result) -> None:
		"""Handle scrape completion."""
		self.unsetCursor()
		self.accept()

	#============================================
	def _on_scrape_error(self, error_text: str) -> None:
		"""Handle scrape error (#2)."""
		self.unsetCursor()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Scrape Selected")
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Scrape Error",
			f"Failed to scrape movie:\n{error_text}"
		)

	#============================================
	def _on_double_click(self, index):
		"""Double-click a result to accept it."""
		self._accept_selection()
