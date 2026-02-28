"""Search results chooser dialog with poster preview pane."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.workers
import moviemanager.ui.widgets.image_label


#============================================
class MovieChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for searching and selecting a movie match.

	Shows a split-pane layout with search results on the left
	and a poster preview with detail labels on the right.

	Supports single-movie and batch modes. In batch mode, shows
	Abort Queue/Back/Cancel/OK buttons for navigating a list of movies.
	"""

	def __init__(self, movie, api, parent=None, movie_list=None):
		"""Initialize the movie chooser dialog.

		Args:
			movie: Movie instance to search for.
			api: MovieAPI instance for search and scrape.
			parent: Parent widget.
			movie_list: Optional list of movies for batch navigation.
		"""
		super().__init__(parent)
		self._api = api
		self._selected_result = None
		self._results = []
		self._pool = PySide6.QtCore.QThreadPool()
		# track in-flight poster download worker for cancellation
		self._poster_worker = None
		# batch mode state
		self._movie_list = movie_list or [movie]
		self._current_index = 0
		# find the starting movie in the list
		if movie_list:
			for i, m in enumerate(movie_list):
				if m is movie:
					self._current_index = i
					break
		self._movie = self._movie_list[self._current_index]
		# track batch results: dict of movie -> scraped bool
		self._batch_results = {}
		self._batch_mode = movie_list is not None and len(movie_list) > 1
		self.resize(900, 550)
		self._setup_ui()
		# load the first movie
		self._load_movie(self._movie)

	#============================================
	def _setup_ui(self) -> None:
		"""Build the split-pane layout with search, preview, and buttons."""
		main_layout = PySide6.QtWidgets.QVBoxLayout(self)

		# --- search bar at top ---
		search_layout = PySide6.QtWidgets.QHBoxLayout()
		self._search_field = PySide6.QtWidgets.QLineEdit()
		self._search_field.setPlaceholderText("Movie title...")
		# enter key triggers search
		self._search_field.returnPressed.connect(self._do_search)
		search_layout.addWidget(self._search_field)
		self._year_field = PySide6.QtWidgets.QLineEdit()
		self._year_field.setPlaceholderText("Year")
		self._year_field.setMaximumWidth(80)
		# enter key on year field also triggers search
		self._year_field.returnPressed.connect(self._do_search)
		search_layout.addWidget(self._year_field)
		self._search_btn = PySide6.QtWidgets.QPushButton("Search")
		self._search_btn.clicked.connect(self._do_search)
		search_layout.addWidget(self._search_btn)
		main_layout.addLayout(search_layout)

		# --- no-results widget with broader search button (hidden) ---
		self._no_results_widget = PySide6.QtWidgets.QWidget()
		no_results_layout = PySide6.QtWidgets.QVBoxLayout(
			self._no_results_widget
		)
		self._no_results_label = PySide6.QtWidgets.QLabel(
			"No results found."
		)
		self._no_results_label.setAlignment(
			PySide6.QtCore.Qt.AlignmentFlag.AlignCenter
		)
		no_results_layout.addWidget(self._no_results_label)
		# broader search button
		self._broader_search_btn = PySide6.QtWidgets.QPushButton(
			"Try broader search"
		)
		self._broader_search_btn.clicked.connect(self._do_broader_search)
		no_results_layout.addWidget(
			self._broader_search_btn,
			alignment=PySide6.QtCore.Qt.AlignmentFlag.AlignCenter,
		)
		self._no_results_widget.hide()
		main_layout.addWidget(self._no_results_widget)

		# --- horizontal splitter: results table | preview pane ---
		self._splitter = PySide6.QtWidgets.QSplitter(
			PySide6.QtCore.Qt.Orientation.Horizontal
		)

		# left side: results table (3 columns)
		self._results_table = PySide6.QtWidgets.QTableWidget()
		self._results_table.setColumnCount(3)
		self._results_table.setHorizontalHeaderLabels(
			["Title", "Year", "Rating"]
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
		self._results_table.setWordWrap(False)
		# double-click accepts selection
		self._results_table.doubleClicked.connect(
			self._on_double_click
		)
		# selection change triggers poster preview update
		# currentCellChanged emits (row, col, prev_row, prev_col)
		self._results_table.currentCellChanged.connect(
			lambda row, _col, _prev_row, _prev_col: self._on_result_selected(row)
		)
		self._splitter.addWidget(self._results_table)

		# right side: preview pane with poster and details
		preview_widget = PySide6.QtWidgets.QWidget()
		preview_layout = PySide6.QtWidgets.QVBoxLayout(preview_widget)
		preview_layout.setContentsMargins(8, 0, 0, 0)

		# poster image label
		self._poster_label = (
			moviemanager.ui.widgets.image_label.ImageLabel()
		)
		self._poster_label.setMinimumSize(180, 270)
		self._poster_label.setText("No poster")
		preview_layout.addWidget(
			self._poster_label,
			stretch=3,
			alignment=PySide6.QtCore.Qt.AlignmentFlag.AlignTop
		)

		# detail labels below poster
		self._title_label = PySide6.QtWidgets.QLabel("")
		# bold larger font for movie title
		title_font = self._title_label.font()
		title_font.setBold(True)
		title_font.setPointSize(title_font.pointSize() + 2)
		self._title_label.setFont(title_font)
		self._title_label.setWordWrap(True)
		preview_layout.addWidget(self._title_label)

		self._year_label = PySide6.QtWidgets.QLabel("")
		preview_layout.addWidget(self._year_label)

		# overview text with word wrap in a read-only text edit
		self._overview_text = PySide6.QtWidgets.QTextEdit()
		self._overview_text.setReadOnly(True)
		self._overview_text.setMaximumHeight(150)
		# style to blend with dialog background
		self._overview_text.setFrameShape(
			PySide6.QtWidgets.QFrame.Shape.NoFrame
		)
		preview_layout.addWidget(self._overview_text, stretch=2)

		self._splitter.addWidget(preview_widget)

		# set initial splitter ratio to roughly 60/40
		self._splitter.setSizes([540, 360])
		main_layout.addWidget(self._splitter, stretch=1)

		# --- button row ---
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		if self._batch_mode:
			# batch mode: Abort Queue | Back | spacer | Cancel | OK
			self._abort_btn = PySide6.QtWidgets.QPushButton(
				"Abort Queue"
			)
			self._abort_btn.clicked.connect(self.reject)
			btn_layout.addWidget(self._abort_btn)
			self._back_btn = PySide6.QtWidgets.QPushButton("Back")
			self._back_btn.clicked.connect(self._go_previous)
			btn_layout.addWidget(self._back_btn)
		btn_layout.addStretch()
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self._skip_current)
		btn_layout.addWidget(cancel_btn)
		self._ok_btn = PySide6.QtWidgets.QPushButton("OK")
		self._ok_btn.clicked.connect(self._accept_selection)
		btn_layout.addWidget(self._ok_btn)
		main_layout.addLayout(btn_layout)

	#============================================
	def _skip_current(self) -> None:
		"""Skip the current movie (cancel in single, advance in batch)."""
		if self._batch_mode:
			self._advance_to_next()
		else:
			self.reject()

	#============================================
	def _on_result_selected(self, row: int) -> None:
		"""Update preview pane when a result row is selected.

		Downloads the poster image in a background thread and
		updates the detail labels with the selected result info.

		Args:
			row: The row index of the selected result.
		"""
		# cancel any in-flight poster download
		if self._poster_worker is not None:
			self._poster_worker.cancel()
			self._poster_worker = None

		# clear preview if no valid selection
		if row < 0 or row >= len(self._results):
			self._poster_label.setText("No poster")
			self._title_label.setText("")
			self._year_label.setText("")
			self._overview_text.clear()
			return

		result = self._results[row]

		# update detail labels
		self._title_label.setText(result.title)
		year_text = f"Year: {result.year}" if result.year else ""
		self._year_label.setText(year_text)
		self._overview_text.setPlainText(result.overview or "")

		# download poster if URL is available
		if result.poster_url:
			self._poster_label.setText("Loading...")
			worker = moviemanager.ui.workers.ImageDownloadWorker(
				result.poster_url
			)
			worker.signals.finished.connect(
				self._on_poster_downloaded
			)
			worker.signals.error.connect(self._on_poster_error)
			self._poster_worker = worker
			self._pool.start(worker)
		else:
			# no poster URL available
			self._poster_label.set_image_data(None)

	#============================================
	def _on_poster_downloaded(self, data: bytes) -> None:
		"""Display the downloaded poster image.

		Args:
			data: Raw image bytes from the download worker.
		"""
		self._poster_worker = None
		self._poster_label.set_image_data(data)

	#============================================
	def _on_poster_error(self, error_text: str) -> None:
		"""Handle poster download failure.

		Args:
			error_text: Description of what went wrong.
		"""
		self._poster_worker = None
		self._poster_label.setText("No poster")

	#============================================
	def _load_movie(self, movie) -> None:
		"""Load a movie into the dialog and start search.

		Args:
			movie: Movie instance to load.
		"""
		self._movie = movie
		# update window title with position indicator
		if self._batch_mode:
			pos = self._current_index + 1
			total = len(self._movie_list)
			self.setWindowTitle(
				f"Scrape - {movie.title} ({pos}/{total})"
			)
		else:
			self.setWindowTitle(f"Scrape - {movie.title}")
		# update search fields
		self._search_field.setText(movie.title)
		if movie.year:
			self._year_field.setText(movie.year)
		else:
			self._year_field.clear()
		# update navigation button states
		if self._batch_mode:
			self._back_btn.setEnabled(self._current_index > 0)
		# reset buttons
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("OK")
		# clear the preview pane
		self._on_result_selected(-1)
		# start search
		self._do_search()

	#============================================
	def _do_search(self) -> None:
		"""Search with current text in a background thread."""
		title = self._search_field.text().strip()
		year = self._year_field.text().strip()
		if not title:
			return
		# disable search button while working
		self._search_btn.setEnabled(False)
		self._search_btn.setText("Searching...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# run search in background thread
		worker = moviemanager.ui.workers.Worker(
			self._api.search_movie, title, year
		)
		worker.signals.finished.connect(self._on_search_done)
		worker.signals.error.connect(self._on_search_error)
		self._pool.start(worker)

	#============================================
	def _do_broader_search(self) -> None:
		"""Try fallback search strategies for broader matching."""
		title = self._search_field.text().strip()
		year = self._year_field.text().strip()
		if not title:
			return
		self._broader_search_btn.setEnabled(False)
		self._broader_search_btn.setText("Searching...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		worker = moviemanager.ui.workers.Worker(
			self._api.search_movie_with_fallback, title, year
		)
		worker.signals.finished.connect(self._on_broader_search_done)
		worker.signals.error.connect(self._on_search_error)
		self._pool.start(worker)

	#============================================
	def _on_broader_search_done(self, result) -> None:
		"""Handle fallback search results.

		Args:
			result: Tuple of (results list, strategy string).
		"""
		results, strategy = result
		self.unsetCursor()
		self._broader_search_btn.setEnabled(True)
		self._broader_search_btn.setText("Try broader search")
		self._search_btn.setEnabled(True)
		self._search_btn.setText("Search")
		if results:
			self._no_results_widget.hide()
			self._results_table.show()
			# show which strategy worked
			self._no_results_label.setText(
				f"Found via: {strategy}"
			)
		self._results = results
		self._populate_results_table(results)

	#============================================
	def _on_search_done(self, results) -> None:
		"""Handle search results from background thread."""
		self.unsetCursor()
		self._search_btn.setEnabled(True)
		self._search_btn.setText("Search")
		self._results = results
		# show/hide no-results widget
		if not results:
			self._no_results_widget.show()
			self._no_results_label.setText("No results found.")
			self._broader_search_btn.setEnabled(True)
			self._broader_search_btn.setText("Try broader search")
			self._results_table.hide()
			# clear the preview pane
			self._on_result_selected(-1)
			return
		self._no_results_widget.hide()
		self._results_table.show()
		self._populate_results_table(results)

	#============================================
	def _populate_results_table(self, results: list) -> None:
		"""Fill the results table with search results.

		Args:
			results: List of SearchResult dataclasses.
		"""
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
			score_text = str(result.score) if result.score else ""
			self._results_table.setItem(
				row, 2,
				PySide6.QtWidgets.QTableWidgetItem(score_text)
			)
		self._results_table.resizeColumnsToContents()
		# auto-select first result to populate preview
		if results:
			self._results_table.setCurrentCell(0, 0)

	#============================================
	def _on_search_error(self, error_text: str) -> None:
		"""Handle search error from background thread."""
		self.unsetCursor()
		self._search_btn.setEnabled(True)
		self._search_btn.setText("Search")
		self._broader_search_btn.setEnabled(True)
		self._broader_search_btn.setText("Try broader search")
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Search Error",
			f"Search failed:\n{error_text}"
		)

	#============================================
	def _accept_selection(self) -> None:
		"""Accept the selected result and scrape."""
		row = self._results_table.currentRow()
		if row < 0 or row >= len(self._results):
			PySide6.QtWidgets.QMessageBox.warning(
				self, "No Selection",
				"Please select a search result."
			)
			return
		result = self._results[row]
		# scrape in background thread
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
		# record success for this movie
		# use path as key since Movie is not hashable
		self._batch_results[self._movie.path] = True
		# in batch mode, auto-advance to next movie
		if self._batch_mode:
			if self._current_index < len(self._movie_list) - 1:
				self._advance_to_next()
				return
		# last movie or single mode: accept
		self.accept()

	#============================================
	def _on_scrape_error(self, error_text: str) -> None:
		"""Handle scrape error."""
		self.unsetCursor()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("OK")
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Scrape Error",
			f"Failed to scrape movie:\n{error_text}"
		)

	#============================================
	def _on_double_click(self, index) -> None:
		"""Double-click a result to accept it."""
		self._accept_selection()

	#============================================
	def _advance_to_next(self) -> None:
		"""Advance to the next movie in the batch list."""
		if self._current_index >= len(self._movie_list) - 1:
			# at end of list, accept to close
			self.accept()
			return
		self._current_index += 1
		next_movie = self._movie_list[self._current_index]
		self._load_movie(next_movie)

	#============================================
	def _go_previous(self) -> None:
		"""Go back to the previous movie in the batch list."""
		if self._current_index <= 0:
			return
		self._current_index -= 1
		prev_movie = self._movie_list[self._current_index]
		self._load_movie(prev_movie)

	#============================================
	def get_batch_results(self) -> dict:
		"""Return the batch scrape results.

		Returns:
			dict: Mapping of movie path -> bool (True if scraped).
		"""
		return self._batch_results
