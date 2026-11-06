"""Dialog that coordinates movie-match navigation and metadata scraping."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import moviemanager.api.movie_api
import moviemanager.core.models.movie
import moviemanager.ui.dialogs.batch_navigator
import moviemanager.ui.dialogs.movie_search_prefetch
import moviemanager.ui.task_api
import moviemanager.ui.widgets.movie_search_pane
import moviemanager.ui.widgets.prematch_widget


#============================================
class MovieChooserDialog(PySide6.QtWidgets.QDialog):
	"""Coordinate batch navigation, prematch decisions, and metadata scraping."""

	def __init__(
		self,
		movie: moviemanager.core.models.movie.Movie,
		api: moviemanager.api.movie_api.MovieAPI,
		parent: PySide6.QtWidgets.QWidget | None = None,
		movie_list: list[moviemanager.core.models.movie.Movie] | None = None,
		task_api: moviemanager.ui.task_api.TaskAPI | None = None,
	) -> None:
		super().__init__(parent)
		if task_api is None:
			task_api = moviemanager.ui.task_api.TaskAPI(parent=self)
		self._api = api
		self._task_api = task_api
		self._nav = moviemanager.ui.dialogs.batch_navigator.BatchNavigator(movie, movie_list)
		self._movie = self._nav.current_movie
		self._prefetch = moviemanager.ui.dialogs.movie_search_prefetch.MovieSearchPrefetch(
			api, task_api,
		)
		self._pending_scrape_movie: moviemanager.core.models.movie.Movie | None = None
		self._pending_scrape_kwargs: dict = {}
		self._in_prematch_mode = False
		self._had_prematch = False
		self.resize(900, 550)
		self._setup_ui()
		self._load_movie(self._movie)

	#============================================
	def _setup_ui(self) -> None:
		"""Build the search/prematch surface, batch status, and actions."""
		main_layout = PySide6.QtWidgets.QVBoxLayout(self)
		self._search_pane = moviemanager.ui.widgets.movie_search_pane.MovieSearchPane(
			self._api, self._task_api,
		)
		self._search_pane.accept_requested.connect(self._accept_selection)
		main_layout.addWidget(self._search_pane, stretch=1)

		self._prematch_widget = moviemanager.ui.widgets.prematch_widget.PrematchWidget()
		self._prematch_widget.rematch_requested.connect(self._switch_to_search_mode)
		self._prematch_widget.hide()
		main_layout.addWidget(self._prematch_widget, stretch=1)

		if self._nav.batch_mode:
			progress_layout = PySide6.QtWidgets.QHBoxLayout()
			self._progress_label = PySide6.QtWidgets.QLabel("Movie 1 of " + str(self._nav.total_count))
			progress_layout.addWidget(self._progress_label)
			self._match_count_label = PySide6.QtWidgets.QLabel("0 matched")
			progress_layout.addWidget(self._match_count_label)
			self._progress_bar = PySide6.QtWidgets.QProgressBar()
			self._progress_bar.setMaximum(self._nav.total_count)
			self._progress_bar.setValue(0)
			self._progress_bar.setMaximumHeight(16)
			progress_layout.addWidget(self._progress_bar)
			main_layout.addLayout(progress_layout)

		button_layout = PySide6.QtWidgets.QHBoxLayout()
		button_layout.addStretch()
		if self._nav.batch_mode:
			self._abort_btn = PySide6.QtWidgets.QPushButton("Stop Batch")
			self._abort_btn.clicked.connect(self.reject)
			button_layout.addWidget(self._abort_btn)
			self._back_btn = PySide6.QtWidgets.QPushButton("Back")
			self._back_btn.clicked.connect(self._go_previous)
			button_layout.addWidget(self._back_btn)
			skip_button = PySide6.QtWidgets.QPushButton("Skip")
			skip_button.setToolTip("Skip this movie (Escape)")
		else:
			skip_button = PySide6.QtWidgets.QPushButton("Cancel")
			skip_button.setToolTip("Cancel (Escape)")
		skip_button.clicked.connect(self._skip_current)
		button_layout.addWidget(skip_button)
		self._keep_original_btn = PySide6.QtWidgets.QPushButton("Keep Original Match")
		self._keep_original_btn.clicked.connect(self._return_to_prematch)
		self._keep_original_btn.hide()
		button_layout.addWidget(self._keep_original_btn)
		self._ok_btn = PySide6.QtWidgets.QPushButton("Accept Match")
		self._ok_btn.clicked.connect(self._on_ok_clicked)
		button_layout.addWidget(self._ok_btn)
		main_layout.addLayout(button_layout)

	#============================================
	def _on_ok_clicked(self) -> None:
		"""Keep an existing match or scrape the current search selection."""
		if self._in_prematch_mode:
			self._keep_existing_match()
		else:
			self._accept_selection()

	#============================================
	def _show_prematch_view(self, movie: moviemanager.core.models.movie.Movie) -> None:
		"""Show existing metadata for a matched movie."""
		self._in_prematch_mode = True
		self._search_pane.hide()
		self._prematch_widget.show_movie(movie, self._task_api)
		self._prematch_widget.show()
		self._ok_btn.setText("Keep Match")
		self._ok_btn.setEnabled(True)

	#============================================
	def _show_search_mode(self) -> None:
		"""Show the search surface and hide existing-match details."""
		self._prematch_widget.hide()
		self._search_pane.show()

	#============================================
	def _switch_to_search_mode(self) -> None:
		"""Search a previously matched movie while retaining a way back."""
		self._in_prematch_mode = False
		self._had_prematch = True
		self._show_search_mode()
		self._keep_original_btn.show()
		self._ok_btn.setText("Accept Match")
		self._search_pane.search()

	#============================================
	def _keep_existing_match(self) -> None:
		"""Keep a prematched movie and advance a batch when appropriate."""
		if self._nav.batch_mode:
			self._nav.mark_result(self._movie.path, True)
			self._advance_to_next()
		else:
			self.accept()

	#============================================
	def _return_to_prematch(self) -> None:
		"""Restore the original match after a rematch search."""
		self._in_prematch_mode = True
		self._had_prematch = False
		self._keep_original_btn.hide()
		self._show_prematch_view(self._movie)

	#============================================
	def _skip_current(self) -> None:
		"""Advance a batch or reject the standalone chooser."""
		if self._nav.batch_mode:
			self._advance_to_next()
		else:
			self.reject()

	#============================================
	def _load_movie(self, movie: moviemanager.core.models.movie.Movie) -> None:
		"""Load movie state and display cached next-search results when available."""
		self._movie = movie
		self._search_pane.set_movie_query(movie)
		self._update_navigation_state()
		self._in_prematch_mode = False
		self._had_prematch = False
		self._keep_original_btn.hide()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Accept Match")
		if movie.scraped:
			self._show_prematch_view(movie)
		else:
			self._show_search_mode()
			results = self._prefetch.take_results(movie)
			if results is None:
				self._search_pane.search()
			else:
				self._search_pane.show_prefetched_results(
					results, self._prefetch.take_poster(movie),
				)
		self._prefetch.start(self._nav.get_next_movie())

	#============================================
	def _update_navigation_state(self) -> None:
		"""Render title, progress, and batch outcomes from navigator state."""
		if not self._nav.batch_mode:
			self.setWindowTitle(f"Match - {self._movie.title}")
			return
		position = self._nav.current_index + 1
		self.setWindowTitle(f"Match - {self._movie.title} ({position} of {self._nav.total_count})")
		status = "matched" if self._movie.scraped else "unmatched"
		self._progress_label.setText(f"Movie {position} of {self._nav.total_count} ({status})")
		self._progress_bar.setValue(self._nav.current_index)
		self._back_btn.setEnabled(self._nav.current_index > 0)
		self._update_match_count()

	#============================================
	def _update_match_count(self) -> None:
		"""Display terminal outcomes without counting pending scrapes as matches."""
		if not self._nav.batch_mode:
			return
		label = f"{self._nav.matched_count} matched"
		if self._nav.failed_count:
			label += f", {self._nav.failed_count} failed"
		self._match_count_label.setText(label)

	#============================================
	def _accept_selection(self) -> None:
		"""Submit the selected match for scraping and advance a batch."""
		result = self._search_pane.selected_result
		if result is None:
			PySide6.QtWidgets.QMessageBox.warning(self, "No Selection", "Please select a search result.")
			return
		scrape_kwargs: dict = {}
		if result.tmdb_id:
			scrape_kwargs["tmdb_id"] = result.tmdb_id
		elif result.imdb_id:
			scrape_kwargs["imdb_id"] = result.imdb_id
		self._pending_scrape_movie = self._movie
		self._pending_scrape_kwargs = dict(scrape_kwargs)
		self._nav.mark_result(self._movie.path, "pending")
		self._start_scrape_worker(self._movie, scrape_kwargs)
		if self._nav.batch_mode:
			self._advance_to_next()

	#============================================
	def _start_scrape_worker(
		self, movie: moviemanager.core.models.movie.Movie, scrape_kwargs: dict,
	) -> None:
		"""Run a metadata scrape through the shared task API."""
		movie_path = movie.path
		self._ok_btn.setEnabled(False)
		self._ok_btn.setText("Saving...")
		self.setCursor(PySide6.QtCore.Qt.CursorShape.WaitCursor)
		task_id = self._task_api.submit_job(
			f"Scraping {movie.title or 'Unknown'}", self._api.scrape_movie, movie,
			_priority=moviemanager.ui.task_api.PRIORITY_HIGH,
			**scrape_kwargs,
		)
		self._task_api.task_finished.connect(
			lambda identifier, result, path=movie_path, expected=task_id:
			self._on_scrape_done(result, path) if identifier == expected else None,
		)
		self._task_api.task_error.connect(
			lambda identifier, error, path=movie_path, expected=task_id:
			self._on_scrape_error(error, path) if identifier == expected else None,
		)

	#============================================
	def _on_scrape_done(self, result: object, movie_path: str = "") -> None:
		"""Record a successful scrape and close a standalone chooser."""
		if movie_path:
			self._nav.mark_result(movie_path, True)
		self._update_match_count()
		self.unsetCursor()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Accept Match")
		if not self._nav.batch_mode:
			self.accept()

	#============================================
	def _on_scrape_error(self, error_text: str, movie_path: str = "") -> None:
		"""Record failure and offer an IMDb challenge retry where supported."""
		if movie_path:
			self._nav.mark_result(movie_path, False)
		self._update_match_count()
		self.unsetCursor()
		self._ok_btn.setEnabled(True)
		self._ok_btn.setText("Accept Match")
		if (
			not self._nav.batch_mode
			and "AWS WAF challenge" in error_text
			and self._retry_after_imdb_challenge()
		):
			return
		PySide6.QtWidgets.QMessageBox.critical(
			self, "Scrape Error", f"Failed to scrape movie:\n{error_text}",
		)

	#============================================
	def _retry_after_imdb_challenge(self) -> bool:
		"""Complete an IMDb challenge with the shared profile and retry."""
		if self._pending_scrape_movie is None:
			return False
		imdb_id = self._pending_scrape_kwargs.get("imdb_id", "")
		if not imdb_id:
			return False
		import moviemanager.ui.dialogs.imdb_challenge_dialog
		transport = self._api.get_imdb_transport()
		profile = transport.get_profile() if transport is not None else None
		dialog = moviemanager.ui.dialogs.imdb_challenge_dialog.ImdbChallengeDialog(
			f"https://www.imdb.com/title/{imdb_id}/", self,
			seed_cookies=self._api.get_configured_imdb_browser_cookies(),
			profile=profile,
		)
		if dialog.exec() != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return False
		self._start_scrape_worker(self._pending_scrape_movie, self._pending_scrape_kwargs)
		return True

	#============================================
	def _advance_to_next(self) -> None:
		"""Advance batch state or accept when the final item completes."""
		if not self._nav.advance():
			self.accept()
			return
		self._load_movie(self._nav.current_movie)

	#============================================
	def _go_previous(self) -> None:
		"""Go back one batch item when navigation permits it."""
		if self._nav.go_back():
			self._load_movie(self._nav.current_movie)

	#============================================
	def done(self, result: int) -> None:
		"""Cancel search and prefetch work before this dialog is destroyed."""
		self._search_pane.cancel()
		self._prefetch.cancel()
		super().done(result)

	#============================================
	def keyPressEvent(self, event: PySide6.QtGui.QKeyEvent) -> None:
		"""Use Escape as Skip for batches and normal cancel for one movie."""
		if event.key() == PySide6.QtCore.Qt.Key.Key_Escape:
			self._skip_current()
			return
		super().keyPressEvent(event)

	#============================================
	def get_batch_results(self) -> dict:
		"""Return terminal and pending outcome records by movie path."""
		return self._nav.get_results()
