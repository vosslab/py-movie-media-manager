"""Search and select movie metadata results."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.models.movie
import moviemanager.scraper.types
import moviemanager.ui.task_api
import moviemanager.ui.widgets.search_result_preview


#============================================
class MovieSearchPane(PySide6.QtWidgets.QWidget):
	"""Own the query controls, result table, and preview for one movie."""

	result_selected = PySide6.QtCore.Signal(object)
	accept_requested = PySide6.QtCore.Signal()

	def __init__(
		self,
		api: moviemanager.api.movie_api.MovieAPI,
		task_api: moviemanager.ui.task_api.TaskAPI,
		parent: PySide6.QtWidgets.QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self._api = api
		self._task_api = task_api
		self._movie: moviemanager.core.models.movie.Movie | None = None
		self._results: list[moviemanager.scraper.types.SearchResult] = []
		self._search_worker: object | None = None
		self._setup_ui()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the existing query, results, and preview layout."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		search_layout = PySide6.QtWidgets.QHBoxLayout()
		self._title_field = PySide6.QtWidgets.QLineEdit()
		self._title_field.setPlaceholderText("Movie title...")
		self._title_field.returnPressed.connect(self.search)
		search_layout.addWidget(self._title_field)
		self._year_field = PySide6.QtWidgets.QLineEdit()
		self._year_field.setPlaceholderText("Year")
		self._year_field.setMaximumWidth(80)
		self._year_field.returnPressed.connect(self.search)
		search_layout.addWidget(self._year_field)
		self._search_btn = PySide6.QtWidgets.QPushButton("Search")
		self._search_btn.clicked.connect(self.search)
		search_layout.addWidget(self._search_btn)
		layout.addLayout(search_layout)

		self._no_results_widget = PySide6.QtWidgets.QWidget()
		no_results_layout = PySide6.QtWidgets.QVBoxLayout(self._no_results_widget)
		self._no_results_label = PySide6.QtWidgets.QLabel("No results found.")
		self._no_results_label.setAlignment(PySide6.QtCore.Qt.AlignmentFlag.AlignCenter)
		no_results_layout.addWidget(self._no_results_label)
		self._broader_search_btn = PySide6.QtWidgets.QPushButton("Try broader search")
		self._broader_search_btn.clicked.connect(self.search_with_fallback)
		no_results_layout.addWidget(
			self._broader_search_btn,
			alignment=PySide6.QtCore.Qt.AlignmentFlag.AlignCenter,
		)
		self._no_results_widget.hide()
		layout.addWidget(self._no_results_widget)

		self._splitter = PySide6.QtWidgets.QSplitter(PySide6.QtCore.Qt.Orientation.Horizontal)
		self._results_table = PySide6.QtWidgets.QTableWidget()
		self._results_table.setColumnCount(4)
		self._results_table.setHorizontalHeaderLabels(["Title", "Year", "Min", "Match"])
		self._results_table.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows,
		)
		self._results_table.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers,
		)
		self._results_table.horizontalHeader().setStretchLastSection(True)
		self._results_table.setWordWrap(False)
		self._results_table.doubleClicked.connect(self._request_accept)
		self._results_table.currentCellChanged.connect(
			lambda row, _col, _previous_row, _previous_col: self._select_row(row),
		)
		self._splitter.addWidget(self._results_table)
		self._preview = moviemanager.ui.widgets.search_result_preview.SearchResultPreview(
			self._task_api,
		)
		self._splitter.addWidget(self._preview)
		self._splitter.setSizes([540, 360])
		layout.addWidget(self._splitter, stretch=1)

	#============================================
	@property
	def selected_result(self) -> moviemanager.scraper.types.SearchResult | None:
		"""Return the selected result, if its table row remains valid."""
		row = self._results_table.currentRow()
		if row < 0 or row >= len(self._results):
			return None
		return self._results[row]

	#============================================
	def set_movie_query(self, movie: moviemanager.core.models.movie.Movie) -> None:
		"""Set the movie whose title, year, and runtime drive searching."""
		self.cancel()
		self._movie = movie
		self._title_field.setText(movie.title)
		self._year_field.setText(movie.year)
		self._results = []
		self._results_table.setRowCount(0)
		self._no_results_widget.hide()
		self._results_table.show()
		self._preview.show_result(None)

	#============================================
	def show_prefetched_results(
		self,
		results: list[moviemanager.scraper.types.SearchResult],
		poster_data: bytes | None = None,
	) -> None:
		"""Render cached results for the current movie without another request."""
		self._show_results(results, poster_data)

	#============================================
	def search(self) -> None:
		"""Submit a normal metadata search for the displayed query."""
		if self._movie is None:
			return
		title = self._title_field.text().strip()
		if not title:
			return
		self._begin_search(False)
		year = self._year_field.text().strip()
		task_id = self._task_api.submit(
			self._api.search_movie, title, year,
			query_runtime=self._movie.runtime,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(self._on_search_done)
		worker.signals.error.connect(self._on_search_error)
		self._search_worker = worker

	#============================================
	def search_with_fallback(self) -> None:
		"""Submit the provider's broader fallback search for the query."""
		if self._movie is None:
			return
		title = self._title_field.text().strip()
		if not title:
			return
		self._begin_search(True)
		year = self._year_field.text().strip()
		task_id = self._task_api.submit(
			self._api.search_movie_with_fallback, title, year,
			query_runtime=self._movie.runtime,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(self._on_fallback_done)
		worker.signals.error.connect(self._on_search_error)
		self._search_worker = worker

	#============================================
	def _begin_search(self, broader: bool) -> None:
		"""Show the busy state while one search worker is active."""
		self.cancel()
		if broader:
			self._broader_search_btn.setEnabled(False)
			self._broader_search_btn.setText("Searching...")
		else:
			self._search_btn.setEnabled(False)
			self._search_btn.setText("Searching...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)

	#============================================
	def _on_search_done(self, results: list[moviemanager.scraper.types.SearchResult]) -> None:
		"""Render normal search results from the task worker."""
		self._finish_search()
		self._show_results(results)

	#============================================
	def _on_fallback_done(self, result: tuple[list[moviemanager.scraper.types.SearchResult], str]) -> None:
		"""Render fallback results and retain the strategy label when useful."""
		results, strategy = result
		self._finish_search()
		self._show_results(results)
		if results:
			self._no_results_label.setText(f"Found via: {strategy}")

	#============================================
	def _show_results(
		self,
		results: list[moviemanager.scraper.types.SearchResult],
		poster_data: bytes | None = None,
	) -> None:
		"""Populate the table and select its first result when present."""
		self._results = results
		if not results:
			self._no_results_label.setText("No results found.")
			self._no_results_widget.show()
			self._results_table.hide()
			self._preview.show_result(None)
			return
		self._no_results_widget.hide()
		self._results_table.show()
		self._results_table.setRowCount(len(results))
		for row, result in enumerate(results):
			self._set_result_row(row, result)
		self._results_table.resizeColumnsToContents()
		self._results_table.blockSignals(True)
		self._results_table.setCurrentCell(0, 0)
		self._results_table.blockSignals(False)
		self._select_row(0, poster_data)

	#============================================
	def _set_result_row(
		self, row: int, result: moviemanager.scraper.types.SearchResult,
	) -> None:
		"""Write one result row, including its match-confidence color."""
		self._results_table.setItem(row, 0, PySide6.QtWidgets.QTableWidgetItem(result.title))
		self._results_table.setItem(row, 1, PySide6.QtWidgets.QTableWidgetItem(result.year))
		runtime_text = str(result.runtime) if result.runtime > 0 else ""
		self._results_table.setItem(row, 2, PySide6.QtWidgets.QTableWidgetItem(runtime_text))
		confidence_text = f"{result.match_confidence:.0%}" if result.match_confidence > 0 else ""
		confidence_item = PySide6.QtWidgets.QTableWidgetItem(confidence_text)
		dark_text = PySide6.QtGui.QColor(0, 0, 0)
		if result.match_confidence >= 0.7:
			confidence_item.setBackground(PySide6.QtGui.QColor(200, 255, 200))
			confidence_item.setForeground(dark_text)
		elif result.match_confidence >= 0.4:
			confidence_item.setBackground(PySide6.QtGui.QColor(255, 255, 200))
			confidence_item.setForeground(dark_text)
		elif result.match_confidence > 0:
			confidence_item.setBackground(PySide6.QtGui.QColor(255, 200, 200))
			confidence_item.setForeground(dark_text)
		self._results_table.setItem(row, 3, confidence_item)

	#============================================
	def _select_row(self, row: int, poster_data: bytes | None = None) -> None:
		"""Update the preview and emit the semantic selected-result signal."""
		if row < 0 or row >= len(self._results):
			self._preview.show_result(None)
			return
		result = self._results[row]
		self._preview.show_result(result, poster_data)
		self.result_selected.emit(result)

	#============================================
	def _request_accept(self, index: PySide6.QtCore.QModelIndex) -> None:
		"""Request selection acceptance from a double-clicked table row."""
		self.accept_requested.emit()

	#============================================
	def _on_search_error(self, error_text: str) -> None:
		"""Restore controls and show a recoverable search failure."""
		self._finish_search()
		PySide6.QtWidgets.QMessageBox.critical(self, "Search Error", f"Search failed:\n{error_text}")

	#============================================
	def _finish_search(self) -> None:
		"""Restore normal controls after either result or error."""
		self._search_worker = None
		self.unsetCursor()
		self._search_btn.setEnabled(True)
		self._search_btn.setText("Search")
		self._broader_search_btn.setEnabled(True)
		self._broader_search_btn.setText("Try broader search")

	#============================================
	def cancel(self) -> None:
		"""Cancel the active search and preview download, if any."""
		if self._search_worker is not None:
			self._search_worker.cancel()
		self._finish_search()
		self._preview.cancel()
