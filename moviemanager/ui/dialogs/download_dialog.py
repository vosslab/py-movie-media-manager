"""Batch download dialog for artwork, trailers, and subtitles."""

# Standard Library
import time
import random

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.ui.workers


#============================================
def _run_batch_download(
	movies: list, api, settings,
	download_artwork: bool, download_trailers: bool,
	download_subs: bool, worker=None,
) -> dict:
	"""Execute batch download loop in a background thread.

	Downloads artwork, trailers, and subtitles for each movie
	respecting rate limits and cancellation.

	Args:
		movies: List of scraped Movie instances.
		api: MovieAPI instance for download methods.
		settings: Application Settings instance.
		download_artwork: Whether to download artwork.
		download_trailers: Whether to download trailers.
		download_subs: Whether to download subtitles.
		worker: Worker instance for cancellation checks.

	Returns:
		dict with counts: art_count, trailer_count, sub_count,
		errors list, and cancelled flag.
	"""
	art_count = 0
	trailer_count = 0
	sub_count = 0
	errors = []
	cancelled = False
	for i, movie in enumerate(movies):
		# check for cancellation
		if worker and worker.is_cancelled:
			cancelled = True
			break
		# emit progress via worker signals
		if worker:
			progress_msg = (
				f"Processing: {movie.title}"
				f" ({i + 1}/{len(movies)})"
			)
			worker.signals.progress.emit(
				i, len(movies), progress_msg
			)
		# download artwork
		if download_artwork and not movie.has_poster:
			try:
				downloaded = api.download_artwork(movie)
				if downloaded:
					art_count += len(downloaded)
			except Exception as exc:
				errors.append(
					f"Artwork for {movie.title}: {exc}"
				)
			# rate limit between downloads
			time.sleep(random.random())
		# download trailer
		if (download_trailers
				and not movie.has_trailer
				and movie.trailer_url):
			try:
				result = api.download_trailer(movie)
				if result:
					trailer_count += 1
			except Exception as exc:
				errors.append(
					f"Trailer for {movie.title}: {exc}"
				)
			time.sleep(random.random())
		# download subtitles
		if (download_subs
				and not movie.has_subtitle
				and movie.imdb_id):
			try:
				languages = settings.subtitle_languages
				downloaded = api.download_subtitles(
					movie, languages
				)
				if downloaded:
					sub_count += len(downloaded)
			except Exception as exc:
				errors.append(
					f"Subtitles for {movie.title}: {exc}"
				)
			time.sleep(random.random())
	result = {
		"art_count": art_count,
		"trailer_count": trailer_count,
		"sub_count": sub_count,
		"errors": errors,
		"cancelled": cancelled,
	}
	return result


#============================================
class DownloadDialog(PySide6.QtWidgets.QDialog):
	"""Batch download dialog showing a checklist per movie.

	Displays what content is available vs missing for each movie
	(artwork, trailer, subtitles) and downloads missing items
	in a background thread.

	Args:
		movies: List of scraped Movie instances to process.
		api: MovieAPI instance for download methods.
		settings: Application Settings instance.
		parent: Parent widget.
	"""

	def __init__(self, movies: list, api, settings, parent=None):
		super().__init__(parent)
		self._movies = movies
		self._api = api
		self._settings = settings
		self._worker = None
		self._pool = PySide6.QtCore.QThreadPool()
		self.setWindowTitle(
			f"Download Content - {len(movies)} movies"
		)
		self.resize(700, 500)
		self._setup_ui()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the download options, checklist table, and buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)

		# download options checkboxes
		options_group = PySide6.QtWidgets.QGroupBox(
			"Download Options"
		)
		options_layout = PySide6.QtWidgets.QHBoxLayout(
			options_group
		)
		self._artwork_check = PySide6.QtWidgets.QCheckBox(
			"Artwork (poster, fanart)"
		)
		self._artwork_check.setChecked(True)
		options_layout.addWidget(self._artwork_check)
		self._trailer_check = PySide6.QtWidgets.QCheckBox(
			"Trailers"
		)
		self._trailer_check.setChecked(
			self._settings.download_trailer
		)
		options_layout.addWidget(self._trailer_check)
		self._subs_check = PySide6.QtWidgets.QCheckBox(
			"Subtitles"
		)
		self._subs_check.setChecked(
			self._settings.download_subtitles
		)
		options_layout.addWidget(self._subs_check)
		layout.addWidget(options_group)

		# movie checklist table
		self._table = PySide6.QtWidgets.QTableWidget()
		self._table.setColumnCount(4)
		self._table.setHorizontalHeaderLabels(
			["Movie", "Artwork", "Trailer", "Subtitles"]
		)
		self._table.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView
			.EditTrigger.NoEditTriggers
		)
		self._table.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionBehavior.SelectRows
		)
		# stretch columns to fill
		header = self._table.horizontalHeader()
		header.setStretchLastSection(True)
		header.setSectionResizeMode(
			0,
			PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch,
		)
		self._populate_table()
		layout.addWidget(self._table)

		# progress bar (hidden until download starts)
		self._progress = PySide6.QtWidgets.QProgressBar()
		self._progress.hide()
		layout.addWidget(self._progress)

		# status label
		self._status_label = PySide6.QtWidgets.QLabel("")
		layout.addWidget(self._status_label)

		# buttons: Cancel | Download Missing
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		self._cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		self._cancel_btn.clicked.connect(self._on_cancel)
		btn_layout.addWidget(self._cancel_btn)
		self._start_btn = PySide6.QtWidgets.QPushButton(
			"Download Missing"
		)
		self._start_btn.clicked.connect(self._start_download)
		btn_layout.addWidget(self._start_btn)
		layout.addLayout(btn_layout)

	#============================================
	def _populate_table(self) -> None:
		"""Fill the table with movie status rows.

		Shows OK when content exists and Needed when missing.
		"""
		self._table.setRowCount(len(self._movies))
		for row, movie in enumerate(self._movies):
			# movie title
			self._table.setItem(
				row, 0,
				PySide6.QtWidgets.QTableWidgetItem(movie.title),
			)
			# artwork status
			art_status = "OK" if movie.has_poster else "Needed"
			self._table.setItem(
				row, 1,
				PySide6.QtWidgets.QTableWidgetItem(art_status),
			)
			# trailer status
			if movie.has_trailer:
				trailer_status = "OK"
			elif movie.trailer_url:
				trailer_status = "Needed"
			else:
				trailer_status = "No URL"
			self._table.setItem(
				row, 2,
				PySide6.QtWidgets.QTableWidgetItem(trailer_status),
			)
			# subtitle status
			sub_status = "OK" if movie.has_subtitle else "Needed"
			self._table.setItem(
				row, 3,
				PySide6.QtWidgets.QTableWidgetItem(sub_status),
			)

	#============================================
	def _on_cancel(self) -> None:
		"""Handle cancel/stop button click."""
		if self._worker:
			self._worker.cancel()
		else:
			self.reject()

	#============================================
	def _start_download(self) -> None:
		"""Start batch download in a background worker thread.

		Disables controls and runs the download loop off the main
		thread so the UI stays responsive.
		"""
		self._start_btn.setEnabled(False)
		self._artwork_check.setEnabled(False)
		self._trailer_check.setEnabled(False)
		self._subs_check.setEnabled(False)
		self._cancel_btn.setText("Stop")
		self._progress.show()
		self._progress.setMaximum(len(self._movies))
		# create background worker for the download loop
		worker = moviemanager.ui.workers.Worker(
			_run_batch_download,
			self._movies, self._api, self._settings,
			self._artwork_check.isChecked(),
			self._trailer_check.isChecked(),
			self._subs_check.isChecked(),
		)
		# pass worker reference so the loop can check cancellation
		worker.kwargs["worker"] = worker
		# connect signals
		worker.signals.progress.connect(self._on_progress)
		worker.signals.finished.connect(self._on_finished)
		worker.signals.error.connect(self._on_error)
		self._worker = worker
		self._pool.start(worker)

	#============================================
	def _on_progress(self, current: int, total: int, message: str) -> None:
		"""Update progress bar and status label from worker thread.

		Args:
			current: Current movie index.
			total: Total number of movies.
			message: Status message to display.
		"""
		self._progress.setValue(current)
		self._status_label.setText(message)

	#============================================
	def _on_finished(self, result: dict) -> None:
		"""Handle download worker completion.

		Updates the table, shows summary, and re-enables buttons.

		Args:
			result: Dict with art_count, trailer_count, sub_count,
				errors list, and cancelled flag.
		"""
		self._worker = None
		# update progress to complete
		self._progress.setValue(len(self._movies))
		# build summary text
		parts = []
		if result["art_count"]:
			parts.append(f"{result['art_count']} artwork files")
		if result["trailer_count"]:
			parts.append(f"{result['trailer_count']} trailers")
		if result["sub_count"]:
			parts.append(f"{result['sub_count']} subtitle files")
		if parts:
			summary = "Downloaded: " + ", ".join(parts)
		elif result["cancelled"]:
			summary = "Download cancelled"
		else:
			summary = "Nothing to download -- all content present"
		if result["errors"]:
			error_count = len(result["errors"])
			summary += f" ({error_count} errors)"
		self._status_label.setText(summary)
		# update table to reflect new status
		self._populate_table()
		# re-enable buttons for closing
		self._start_btn.setEnabled(True)
		self._start_btn.setText("Done")
		self._start_btn.clicked.disconnect()
		self._start_btn.clicked.connect(self.accept)
		self._cancel_btn.setText("Close")
		self._artwork_check.setEnabled(True)
		self._trailer_check.setEnabled(True)
		self._subs_check.setEnabled(True)

	#============================================
	def _on_error(self, error_text: str) -> None:
		"""Handle download worker error.

		Args:
			error_text: Full traceback text.
		"""
		self._worker = None
		self._status_label.setText(f"Error: {error_text[:200]}")
		self._start_btn.setEnabled(True)
		self._cancel_btn.setText("Close")
		self._artwork_check.setEnabled(True)
		self._trailer_check.setEnabled(True)
		self._subs_check.setEnabled(True)
