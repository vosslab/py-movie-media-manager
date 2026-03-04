"""Search results chooser dialog with poster preview pane."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.dialogs.batch_navigator
import moviemanager.ui.task_api
import moviemanager.ui.workers
import moviemanager.ui.widgets.image_label
import moviemanager.ui.widgets.prematch_widget


#============================================
class MovieChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for searching and selecting a movie match.

	Shows a split-pane layout with search results on the left
	and a poster preview with detail labels on the right.

	Supports single-movie and batch modes. In batch mode, shows
	Abort Queue/Back/Cancel/OK buttons for navigating a list of movies.
	"""

	def __init__(self, movie, api, parent=None, movie_list=None,
				task_api=None):
		"""Initialize the movie chooser dialog.

		Args:
			movie: Movie instance to search for.
			api: MovieAPI instance for search and scrape.
			parent: Parent widget.
			movie_list: Optional list of movies for batch navigation.
			task_api: Optional TaskAPI for submitting background scrape jobs.
		"""
		super().__init__(parent)
		self._api = api
		self._task_api = task_api
		self._selected_result = None
		self._results = []
		# track in-flight poster download worker for cancellation
		self._poster_worker = None
		# prefetch cache for next movie search results
		self._prefetch_cache = {}
		# prefetch cache for next movie poster image data
		self._prefetch_poster_cache = {}
		# track the prefetch worker for cancellation
		self._prefetch_worker = None
		self._prefetch_poster_worker = None
		# batch navigation state
		self._nav = (
			moviemanager.ui.dialogs.batch_navigator
			.BatchNavigator(movie, movie_list)
		)
		self._movie = self._nav.current_movie
		self._pending_scrape_movie = None
		self._pending_scrape_kwargs = {}
		# pre-match mode: show existing match instead of search
		self._in_prematch_mode = False
		# tracks whether user came from prematch view (for return path)
		self._had_prematch = False
		self.resize(900, 550)
		self._setup_ui()
		# load the first movie
		self._load_movie(self._movie)

	#============================================
	def _setup_ui(self) -> None:
		"""Build the split-pane layout with search, preview, and buttons."""
		main_layout = PySide6.QtWidgets.QVBoxLayout(self)

		# --- search bar at top (wrapped in widget for show/hide) ---
		self._search_widget = PySide6.QtWidgets.QWidget()
		search_layout = PySide6.QtWidgets.QHBoxLayout(
			self._search_widget
		)
		search_layout.setContentsMargins(0, 0, 0, 0)
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
		main_layout.addWidget(self._search_widget)

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

		# --- pre-match widget (hidden by default) ---
		self._prematch_widget = (
			moviemanager.ui.widgets.prematch_widget
			.PrematchWidget()
		)
		self._prematch_widget.rematch_requested.connect(
			self._switch_to_search_mode
		)
		self._prematch_widget.hide()
		main_layout.addWidget(self._prematch_widget, stretch=1)

		# --- horizontal splitter: results table | preview pane ---
		self._splitter = PySide6.QtWidgets.QSplitter(
			PySide6.QtCore.Qt.Orientation.Horizontal
		)

		# left side: results table (3 columns)
		self._results_table = PySide6.QtWidgets.QTableWidget()
		self._results_table.setColumnCount(4)
		self._results_table.setHorizontalHeaderLabels(
			["Title", "Year", "Min", "Match"]
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

		self._runtime_label = PySide6.QtWidgets.QLabel("")
		preview_layout.addWidget(self._runtime_label)

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

		# --- batch progress bar (visible only in batch mode) ---
		if self._nav.batch_mode:
			progress_layout = PySide6.QtWidgets.QHBoxLayout()
			self._progress_label = PySide6.QtWidgets.QLabel(
				"Movie 1 of "
				+ str(self._nav.total_count)
			)
			progress_layout.addWidget(self._progress_label)
			self._match_count_label = PySide6.QtWidgets.QLabel(
				"0 matched"
			)
			progress_layout.addWidget(self._match_count_label)
			self._progress_bar = PySide6.QtWidgets.QProgressBar()
			self._progress_bar.setMaximum(
				self._nav.total_count
			)
			self._progress_bar.setValue(0)
			self._progress_bar.setMaximumHeight(16)
			progress_layout.addWidget(self._progress_bar)
			main_layout.addLayout(progress_layout)

		# --- button row (all buttons right-aligned) ---
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		if self._nav.batch_mode:
			# batch: spacer | Stop Batch | Back | Skip | Accept Match
			self._abort_btn = PySide6.QtWidgets.QPushButton(
				"Stop Batch"
			)
			self._abort_btn.clicked.connect(self.reject)
			btn_layout.addWidget(self._abort_btn)
			self._back_btn = PySide6.QtWidgets.QPushButton("Back")
			self._back_btn.clicked.connect(self._go_previous)
			btn_layout.addWidget(self._back_btn)
		# in batch mode "Skip" advances; in single mode "Cancel" closes
		if self._nav.batch_mode:
			skip_btn = PySide6.QtWidgets.QPushButton("Skip")
			skip_btn.setToolTip("Skip this movie (Escape)")
		else:
			skip_btn = PySide6.QtWidgets.QPushButton("Cancel")
			skip_btn.setToolTip("Cancel (Escape)")
		skip_btn.clicked.connect(self._skip_current)
		btn_layout.addWidget(skip_btn)
		# "Keep Original Match" button (hidden until user clicks rematch)
		self._keep_original_btn = PySide6.QtWidgets.QPushButton(
			"Keep Original Match"
		)
		self._keep_original_btn.setToolTip(
			"Return to the original match"
		)
		self._keep_original_btn.clicked.connect(
			self._return_to_prematch
		)
		self._keep_original_btn.hide()
		btn_layout.addWidget(self._keep_original_btn)
		self._ok_btn = PySide6.QtWidgets.QPushButton("Accept Match")
		self._ok_btn.clicked.connect(self._on_ok_clicked)
		btn_layout.addWidget(self._ok_btn)
		main_layout.addLayout(btn_layout)

	#============================================
	def _on_ok_clicked(self) -> None:
		"""Context-aware OK button handler.

		In prematch mode, keeps the existing match. In search mode,
		accepts the selected search result and scrapes.
		"""
		if self._in_prematch_mode:
			self._keep_existing_match()
		else:
			self._accept_selection()

	#============================================
	def _show_prematch_view(self, movie) -> None:
		"""Show existing match data for an already-scraped movie.

		Args:
			movie: Movie instance with scraped metadata.
		"""
		self._in_prematch_mode = True
		# hide search-mode UI elements
		self._search_widget.hide()
		self._splitter.hide()
		self._no_results_widget.hide()
		# delegate to the prematch widget
		self._prematch_widget.show_movie(movie, self._task_api)
		self._prematch_widget.show()
		# update OK button text
		self._ok_btn.setText("Keep Match")
		self._ok_btn.setEnabled(True)

	#============================================
	def _switch_to_search_mode_ui(self) -> None:
		"""Show search-mode UI elements and hide prematch widget."""
		self._prematch_widget.hide()
		self._search_widget.show()
		self._splitter.show()

	#============================================
	def _switch_to_search_mode(self) -> None:
		"""Switch from prematch view to search mode.

		Hides the prematch widget, shows search bar and results,
		and triggers a new search for the current movie.
		Shows "Keep Original Match" button so user can return.
		"""
		self._in_prematch_mode = False
		self._had_prematch = True
		self._switch_to_search_mode_ui()
		self._keep_original_btn.show()
		self._ok_btn.setText("Accept Match")
		self._do_search()

	#============================================
	def _keep_existing_match(self) -> None:
		"""Keep the existing match for a pre-matched movie.

		In batch mode, marks the movie as matched and advances.
		In single mode, accepts the dialog.
		"""
		if self._nav.batch_mode:
			self._nav.mark_result(self._movie.path, True)
			self._advance_to_next()
		else:
			self.accept()

	#============================================
	def _return_to_prematch(self) -> None:
		"""Return to the prematch view after searching for a different match.

		Restores the prematch card with the original movie metadata
		and hides the "Keep Original Match" button.
		"""
		self._in_prematch_mode = True
		self._had_prematch = False
		self._keep_original_btn.hide()
		self._show_prematch_view(self._movie)

	#============================================
	def _skip_current(self) -> None:
		"""Skip the current movie (cancel in single, advance in batch)."""
		if self._nav.batch_mode:
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
			self._runtime_label.setText("")
			self._overview_text.clear()
			return

		result = self._results[row]

		# update detail labels
		self._title_label.setText(result.title)
		year_text = f"Year: {result.year}" if result.year else ""
		self._year_label.setText(year_text)
		# show runtime in minutes if available
		if result.runtime and result.runtime > 0:
			self._runtime_label.setText(
				f"Runtime: {result.runtime} min"
			)
		else:
			self._runtime_label.setText("")
		self._overview_text.setPlainText(result.overview or "")

		# download poster if URL is available
		if result.poster_url:
			# check prefetch poster cache for the first result (row 0)
			if (row == 0
					and self._movie.path in self._prefetch_poster_cache):
				cached_data = self._prefetch_poster_cache.pop(
					self._movie.path
				)
				self._poster_label.set_image_data(
					cached_data, source_url=result.poster_url
				)
			else:
				self._poster_label.setText("Loading...")
				task_id = self._task_api.submit(
					moviemanager.ui.workers.download_image_bytes,
					result.poster_url,
					_priority=moviemanager.ui.task_api.PRIORITY_BACKGROUND,
				)
				worker = self._task_api.get_worker(task_id)
				worker.signals.finished.connect(
					lambda data, url=result.poster_url:
					self._on_poster_downloaded(data, url)
				)
				worker.signals.error.connect(self._on_poster_error)
				self._poster_worker = worker
		else:
			# no poster URL available
			self._poster_label.set_image_data(None)

	#============================================
	def _on_poster_downloaded(
		self, data: bytes, source_url: str = ""
	) -> None:
		"""Display the downloaded poster image.

		Args:
			data: Raw image bytes from the download worker.
			source_url: Poster URL for decode-failure diagnostics.
		"""
		self._poster_worker = None
		self._poster_label.set_image_data(data, source_url=source_url)

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
		if self._nav.batch_mode:
			pos = self._nav.current_index + 1
			total = self._nav.total_count
			self.setWindowTitle(
				f"Match - {movie.title} ({pos} of {total})"
			)
			# update batch progress bar
			matched = self._nav.matched_count
			failed = self._nav.failed_count
			# show matched/unmatched indicator for current movie
			status = "matched" if movie.scraped else "unmatched"
			self._progress_label.setText(
				f"Movie {pos} of {total} ({status})"
			)
			# show matched and failed counts
			label_text = f"{matched} matched"
			if failed:
				label_text += f", {failed} failed"
			self._match_count_label.setText(label_text)
			self._progress_bar.setValue(self._nav.current_index)
		else:
			self.setWindowTitle(f"Match - {movie.title}")
		# update search fields
		self._search_field.setText(movie.title)
		if movie.year:
			self._year_field.setText(movie.year)
		else:
			self._year_field.clear()
		# update navigation button states
		if self._nav.batch_mode:
			self._back_btn.setEnabled(
				self._nav.current_index > 0
			)
		# reset buttons and prematch mode
		self._in_prematch_mode = False
		self._had_prematch = False
		self._keep_original_btn.hide()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Accept Match")
		# clear the preview pane
		self._on_result_selected(-1)
		# show prematch view or start search
		if movie.scraped:
			self._show_prematch_view(movie)
		else:
			self._switch_to_search_mode_ui()
			self._do_search()
		# prefetch next movie search results
		self._prefetch_next()

	#============================================
	def _do_search(self) -> None:
		"""Search with current text in a background thread.

		Checks the prefetch cache first; if the search fields match
		the current movie's original title/year, uses cached results
		immediately instead of making a network call.
		"""
		title = self._search_field.text().strip()
		year = self._year_field.text().strip()
		if not title:
			return
		# check prefetch cache (only when fields match original movie)
		if self._movie.path in self._prefetch_cache:
			cache_title = self._movie.title.strip()
			cache_year = self._movie.year or ""
			if title == cache_title and year == cache_year:
				results = self._prefetch_cache.pop(self._movie.path)
				self._on_search_done(results)
				return
		# disable search button while working
		self._search_btn.setEnabled(False)
		self._search_btn.setText("Searching...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# pass local movie runtime for proximity scoring
		runtime = getattr(self._movie, "runtime", 0) or 0
		# run search in background thread
		task_id = self._task_api.submit(
			self._api.search_movie, title, year,
			query_runtime=runtime,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(self._on_search_done)
		worker.signals.error.connect(self._on_search_error)

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
		# pass local movie runtime for proximity scoring
		runtime = getattr(self._movie, "runtime", 0) or 0
		task_id = self._task_api.submit(
			self._api.search_movie_with_fallback, title, year,
			query_runtime=runtime,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(self._on_broader_search_done)
		worker.signals.error.connect(self._on_search_error)

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
			# show runtime in minutes if available
			runtime_text = ""
			if result.runtime and result.runtime > 0:
				runtime_text = str(result.runtime)
			self._results_table.setItem(
				row, 2,
				PySide6.QtWidgets.QTableWidgetItem(runtime_text)
			)
			# show match confidence as percentage with color coding
			conf = result.match_confidence
			if conf > 0:
				confidence_text = f"{conf:.0%}"
			else:
				confidence_text = ""
			conf_item = PySide6.QtWidgets.QTableWidgetItem(
				confidence_text
			)
			# color-code background and use dark text for readability
			dark_text = PySide6.QtGui.QColor(0, 0, 0)
			if conf >= 0.7:
				conf_item.setBackground(
					PySide6.QtGui.QColor(200, 255, 200)
				)
				conf_item.setForeground(dark_text)
			elif conf >= 0.4:
				conf_item.setBackground(
					PySide6.QtGui.QColor(255, 255, 200)
				)
				conf_item.setForeground(dark_text)
			elif conf > 0:
				conf_item.setBackground(
					PySide6.QtGui.QColor(255, 200, 200)
				)
				conf_item.setForeground(dark_text)
			self._results_table.setItem(row, 3, conf_item)
		self._results_table.resizeColumnsToContents()
		# auto-select first result to populate preview
		if results:
			self._results_table.setCurrentCell(0, 0)
			# force preview update in case currentCellChanged did not fire
			# (happens when cell index was already 0,0 from previous search)
			self._on_result_selected(0)

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
		"""Accept the selected result and scrape in background.

		Submits the scrape as a background job so the UI stays
		responsive. In batch mode, advances to the next movie
		after the scrape callback fires.
		"""
		row = self._results_table.currentRow()
		if row < 0 or row >= len(self._results):
			PySide6.QtWidgets.QMessageBox.warning(
				self, "No Selection",
				"Please select a search result."
			)
			return
		result = self._results[row]
		# pass imdb_id when using IMDB provider (tmdb_id will be 0)
		scrape_kwargs = {}
		if result.tmdb_id:
			scrape_kwargs["tmdb_id"] = result.tmdb_id
		elif result.imdb_id:
			scrape_kwargs["imdb_id"] = result.imdb_id
		# capture current movie for scrape and possible retry
		movie_to_scrape = self._movie
		self._pending_scrape_movie = movie_to_scrape
		self._pending_scrape_kwargs = dict(scrape_kwargs)
		# mark as pending (not yet confirmed by scrape callback)
		self._nav.mark_result(
			movie_to_scrape.path, "pending"
		)
		# run scrape in background worker
		self._start_scrape_worker(movie_to_scrape, scrape_kwargs)
		# in batch mode, advance immediately (scrape continues in background)
		if self._nav.batch_mode:
			self._advance_to_next()

	#============================================
	def _start_scrape_worker(self, movie, scrape_kwargs: dict) -> None:
		"""Run scrape in a background worker thread.

		Submits the scrape as a named job through TaskAPI (if available)
		so it appears in the status bar jobs indicator. Falls back to
		a plain Worker on the dialog's thread pool otherwise.
		"""
		movie_path = movie.path
		movie_title = movie.title or "Unknown"
		# disable button and show wait cursor during scrape
		self._ok_btn.setEnabled(False)
		self._ok_btn.setText("Saving...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		# submit through TaskAPI for job tracking in status bar
		job_name = f"Scraping {movie_title}"
		task_id = self._task_api.submit_job(
			job_name, self._api.scrape_movie, movie,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
			**scrape_kwargs,
		)
		# connect TaskAPI signals filtered by this task_id
		self._task_api.task_finished.connect(
			lambda tid, res, mp=movie_path, expected=task_id:
			self._on_scrape_done(res, mp) if tid == expected else None
		)
		self._task_api.task_error.connect(
			lambda tid, err, mp=movie_path, expected=task_id:
			self._on_scrape_error(err, mp) if tid == expected else None
		)

	#============================================
	def _on_scrape_done(self, result, movie_path: str = "") -> None:
		"""Handle scrape completion.

		Marks the movie as scraped, updates batch counts, and restores
		button state. The caller (_accept_selection) handles advancing
		or closing the dialog.
		"""
		# mark movie as successfully scraped
		if movie_path:
			self._nav.mark_result(movie_path, True)
		# update batch progress with matched and failed counts
		if self._nav.batch_mode:
			matched = self._nav.matched_count
			failed = self._nav.failed_count
			label_text = f"{matched} matched"
			if failed:
				label_text += f", {failed} failed"
			self._match_count_label.setText(label_text)
		# restore button and cursor state
		self.unsetCursor()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Accept Match")
		# in single mode, close the dialog after successful scrape
		if not self._nav.batch_mode:
			self.accept()

	#============================================
	def _on_scrape_error(
		self, error_text: str, movie_path: str = ""
	) -> None:
		"""Handle scrape error.

		Marks the movie as failed in batch results, updates count labels,
		and shows an error popup. In single mode with an AWS WAF challenge,
		offers to retry after the user completes the CAPTCHA.
		"""
		# mark movie as failed in batch results
		if movie_path:
			self._nav.mark_result(movie_path, False)
		# update batch count label
		if self._nav.batch_mode:
			matched = self._nav.matched_count
			failed = self._nav.failed_count
			label_text = f"{matched} matched"
			if failed:
				label_text += f", {failed} failed"
			self._match_count_label.setText(label_text)
		# restore button and cursor state
		self.unsetCursor()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Accept Match")
		# in single mode, offer WAF challenge retry if applicable
		if (
			not self._nav.batch_mode
			and "AWS WAF challenge" in error_text
			and self._retry_after_imdb_challenge()
		):
			return
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Scrape Error",
			f"Failed to scrape movie:\n{error_text}"
		)

	#============================================
	def _retry_after_imdb_challenge(self) -> bool:
		"""Open challenge dialog with shared transport profile and retry scrape.

		Uses the transport's QWebEngineProfile so the challenge dialog
		shares cookies and WAF immunity with the browser transport.

		Returns:
			bool: True if retry was started, False otherwise.
		"""
		if self._pending_scrape_movie is None:
			return False
		imdb_id = self._pending_scrape_kwargs.get("imdb_id", "")
		if not imdb_id:
			return False
		import moviemanager.ui.dialogs.imdb_challenge_dialog
		url = f"https://www.imdb.com/title/{imdb_id}/"
		# use the shared transport profile so cookies persist
		transport = self._api.get_imdb_transport()
		shared_profile = None
		if transport is not None:
			shared_profile = transport.get_profile()
		seed_cookies = self._api.get_configured_imdb_browser_cookies()
		dialog = moviemanager.ui.dialogs.imdb_challenge_dialog.ImdbChallengeDialog(
			url, self, seed_cookies=seed_cookies, profile=shared_profile,
		)
		if dialog.exec() != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return False
		# with shared profile, cookies are already in the transport
		# no need to manually apply cookies
		self._ok_btn.setEnabled(False)
		self._ok_btn.setText("Saving...")
		self.setCursor(
			PySide6.QtCore.Qt.CursorShape.WaitCursor
		)
		self._start_scrape_worker(
			self._pending_scrape_movie,
			self._pending_scrape_kwargs,
		)
		return True

	#============================================
	def _on_double_click(self, index) -> None:
		"""Double-click a result to accept it."""
		self._accept_selection()

	#============================================
	def _advance_to_next(self) -> None:
		"""Advance to the next movie in the batch list."""
		if not self._nav.advance():
			# at end of list, accept to close
			self.accept()
			return
		self._load_movie(self._nav.current_movie)

	#============================================
	def _go_previous(self) -> None:
		"""Go back to the previous movie in the batch list."""
		if not self._nav.go_back():
			return
		self._load_movie(self._nav.current_movie)

	#============================================
	def done(self, result: int) -> None:
		"""Cancel in-flight workers before dialog is destroyed.

		Prevents "Signal source has been deleted" errors when
		background prefetch or poster workers outlive the dialog.

		Args:
			result: Dialog result code (Accepted or Rejected).
		"""
		# cancel any in-flight workers
		if self._prefetch_worker is not None:
			self._prefetch_worker.cancel()
			self._prefetch_worker = None
		if self._prefetch_poster_worker is not None:
			self._prefetch_poster_worker.cancel()
			self._prefetch_poster_worker = None
		if self._poster_worker is not None:
			self._poster_worker.cancel()
			self._poster_worker = None
		super().done(result)

	#============================================
	def _prefetch_next(self) -> None:
		"""Start background search for the next movie in the batch.

		Prefetches search results so advancing to the next movie
		feels instant. Also prefetches the poster for the top result.
		"""
		if not self._nav.batch_mode:
			return
		next_movie = self._nav.get_next_movie()
		if next_movie is None:
			return
		# skip if already cached
		if next_movie.path in self._prefetch_cache:
			return
		# cancel existing prefetch
		if self._prefetch_worker is not None:
			self._prefetch_worker.cancel()
		# run search in background
		title = next_movie.title
		year = next_movie.year or ""
		runtime = getattr(next_movie, "runtime", 0) or 0
		# capture movie path for the lambda closure
		path = next_movie.path
		task_id = self._task_api.submit(
			self._api.search_movie, title, year,
			query_runtime=runtime,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(
			lambda results, p=path: self._on_prefetch_done(p, results)
		)
		# silently ignore prefetch errors
		worker.signals.error.connect(lambda _: None)
		self._prefetch_worker = worker

	#============================================
	def _on_prefetch_done(self, movie_path: str, results: list) -> None:
		"""Cache prefetched search results and start poster prefetch.

		Args:
			movie_path: Path key for the prefetched movie.
			results: Search results from the background search.
		"""
		self._prefetch_cache[movie_path] = results
		self._prefetch_worker = None
		# also prefetch poster for the top result
		if results and results[0].poster_url:
			if self._prefetch_poster_worker is not None:
				self._prefetch_poster_worker.cancel()
			path = movie_path
			poster_task_id = self._task_api.submit(
				moviemanager.ui.workers.download_image_bytes,
				results[0].poster_url,
				_priority=moviemanager.ui.task_api.PRIORITY_BACKGROUND,
			)
			poster_worker = self._task_api.get_worker(poster_task_id)
			poster_worker.signals.finished.connect(
				lambda data, p=path: self._on_prefetch_poster_done(p, data)
			)
			poster_worker.signals.error.connect(lambda _: None)
			self._prefetch_poster_worker = poster_worker

	#============================================
	def _on_prefetch_poster_done(self, movie_path: str, data: bytes) -> None:
		"""Cache prefetched poster image data.

		Args:
			movie_path: Path key for the prefetched movie.
			data: Raw poster image bytes.
		"""
		self._prefetch_poster_cache[movie_path] = data
		self._prefetch_poster_worker = None

	#============================================
	def keyPressEvent(self, event) -> None:
		"""Override key handling for batch-friendly shortcuts.

		Escape skips in batch mode (instead of closing the dialog).
		Default QDialog behavior is preserved for single mode.

		Args:
			event: The key press event.
		"""
		if event.key() == PySide6.QtCore.Qt.Key.Key_Escape:
			# in batch mode, Escape means skip; in single mode, cancel
			self._skip_current()
			return
		super().keyPressEvent(event)

	#============================================
	def get_batch_results(self) -> dict:
		"""Return the batch scrape results.

		Returns:
			dict: Mapping of movie path -> bool (True if scraped).
		"""
		return self._nav.get_results()
