"""Batch download dialog for artwork, trailers, and subtitles."""

# Standard Library
import time
import random

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules


#============================================
class DownloadDialog(PySide6.QtWidgets.QDialog):
	"""Batch download dialog showing a checklist per movie.

	Displays what content is available vs missing for each movie
	(artwork, trailer, subtitles) and downloads missing items.

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
		self._cancelled = False
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
		self._cancelled = True
		self.reject()

	#============================================
	def _start_download(self) -> None:
		"""Run batch download for missing content.

		Downloads artwork, trailers, and subtitles sequentially
		for each movie, respecting rate limits and user options.
		"""
		self._start_btn.setEnabled(False)
		self._cancel_btn.setText("Stop")
		self._progress.show()
		self._progress.setMaximum(len(self._movies))
		self._cancelled = False
		# track download counts for summary
		art_count = 0
		trailer_count = 0
		sub_count = 0
		errors = []
		for i, movie in enumerate(self._movies):
			if self._cancelled:
				break
			self._progress.setValue(i)
			self._status_label.setText(
				f"Processing: {movie.title} ({i + 1}/{len(self._movies)})"
			)
			# process Qt events to keep UI responsive
			PySide6.QtWidgets.QApplication.processEvents()
			# download artwork
			if self._artwork_check.isChecked() and not movie.has_poster:
				try:
					downloaded = self._api.download_artwork(movie)
					if downloaded:
						art_count += len(downloaded)
				except Exception as exc:
					errors.append(
						f"Artwork for {movie.title}: {exc}"
					)
				# rate limit between downloads
				time.sleep(random.random())
			# download trailer
			if (self._trailer_check.isChecked()
					and not movie.has_trailer
					and movie.trailer_url):
				try:
					result = self._api.download_trailer(movie)
					if result:
						trailer_count += 1
				except Exception as exc:
					errors.append(
						f"Trailer for {movie.title}: {exc}"
					)
				time.sleep(random.random())
			# download subtitles
			if (self._subs_check.isChecked()
					and not movie.has_subtitle
					and movie.imdb_id):
				try:
					languages = self._settings.subtitle_languages
					downloaded = self._api.download_subtitles(
						movie, languages
					)
					if downloaded:
						sub_count += len(downloaded)
				except Exception as exc:
					errors.append(
						f"Subtitles for {movie.title}: {exc}"
					)
				time.sleep(random.random())
		# update progress to complete
		self._progress.setValue(len(self._movies))
		# show summary
		parts = []
		if art_count:
			parts.append(f"{art_count} artwork files")
		if trailer_count:
			parts.append(f"{trailer_count} trailers")
		if sub_count:
			parts.append(f"{sub_count} subtitle files")
		if parts:
			summary = "Downloaded: " + ", ".join(parts)
		elif self._cancelled:
			summary = "Download cancelled"
		else:
			summary = "Nothing to download -- all content present"
		if errors:
			summary += f" ({len(errors)} errors)"
		self._status_label.setText(summary)
		# update table to reflect new status
		self._populate_table()
		# re-enable buttons
		self._start_btn.setEnabled(True)
		self._start_btn.setText("Done")
		self._start_btn.clicked.disconnect()
		self._start_btn.clicked.connect(self.accept)
		self._cancel_btn.setText("Close")
