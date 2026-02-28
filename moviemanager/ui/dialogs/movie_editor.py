"""Movie metadata editor dialog."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import moviemanager.core.nfo.writer


#============================================
class MovieEditorDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for editing movie metadata."""

	def __init__(self, movie, parent=None):
		super().__init__(parent)
		self._movie = movie
		self.setWindowTitle(f"Edit - {movie.title}")
		self.resize(600, 700)
		self._setup_ui()
		self._load_movie()
		# snapshot of original values for dirty checking (#7)
		self._original_values = self._get_field_values()

	#============================================
	def _setup_ui(self):
		"""Build the scrollable form and buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# scroll area for form
		scroll = PySide6.QtWidgets.QScrollArea()
		scroll.setWidgetResizable(True)
		form_widget = PySide6.QtWidgets.QWidget()
		form_layout = PySide6.QtWidgets.QFormLayout(form_widget)
		# text fields
		self._title_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Title:", self._title_edit)
		self._original_title_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow(
			"Original Title:", self._original_title_edit
		)
		self._sort_title_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Sort Title:", self._sort_title_edit)
		self._year_edit = PySide6.QtWidgets.QLineEdit()
		self._year_edit.setMaximumWidth(80)
		form_layout.addRow("Year:", self._year_edit)
		self._imdb_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("IMDB ID:", self._imdb_edit)
		# use QSpinBox for TMDB ID to prevent non-numeric input (#14)
		self._tmdb_edit = PySide6.QtWidgets.QSpinBox()
		self._tmdb_edit.setRange(0, 999999999)
		self._tmdb_edit.setSpecialValueText("")
		self._tmdb_edit.setMaximumWidth(120)
		form_layout.addRow("TMDB ID:", self._tmdb_edit)
		self._tagline_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Tagline:", self._tagline_edit)
		self._plot_edit = PySide6.QtWidgets.QTextEdit()
		self._plot_edit.setMaximumHeight(120)
		form_layout.addRow("Plot:", self._plot_edit)
		self._runtime_edit = PySide6.QtWidgets.QSpinBox()
		self._runtime_edit.setRange(0, 999)
		self._runtime_edit.setSuffix(" min")
		form_layout.addRow("Runtime:", self._runtime_edit)
		self._rating_edit = PySide6.QtWidgets.QDoubleSpinBox()
		self._rating_edit.setRange(0.0, 10.0)
		self._rating_edit.setSingleStep(0.1)
		form_layout.addRow("Rating:", self._rating_edit)
		self._certification_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow(
			"Certification:", self._certification_edit
		)
		self._director_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Director:", self._director_edit)
		self._writer_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Writer:", self._writer_edit)
		self._studio_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Studio:", self._studio_edit)
		self._genres_edit = PySide6.QtWidgets.QLineEdit()
		self._genres_edit.setPlaceholderText(
			"Comma-separated genres"
		)
		form_layout.addRow("Genres:", self._genres_edit)
		self._tags_edit = PySide6.QtWidgets.QLineEdit()
		self._tags_edit.setPlaceholderText(
			"Comma-separated tags"
		)
		form_layout.addRow("Tags:", self._tags_edit)
		self._country_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Country:", self._country_edit)
		self._languages_edit = PySide6.QtWidgets.QLineEdit()
		form_layout.addRow("Languages:", self._languages_edit)
		# watched checkbox
		self._watched_check = PySide6.QtWidgets.QCheckBox(
			"Watched"
		)
		form_layout.addRow("", self._watched_check)
		scroll.setWidget(form_widget)
		layout.addWidget(scroll)
		# buttons
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		save_btn = PySide6.QtWidgets.QPushButton("Save")
		save_btn.clicked.connect(self._save)
		btn_layout.addWidget(save_btn)
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(cancel_btn)
		layout.addLayout(btn_layout)

	#============================================
	def _get_field_values(self) -> dict:
		"""Snapshot current form values for dirty checking (#7)."""
		values = {
			"title": self._title_edit.text(),
			"original_title": self._original_title_edit.text(),
			"sort_title": self._sort_title_edit.text(),
			"year": self._year_edit.text(),
			"imdb_id": self._imdb_edit.text(),
			"tmdb_id": self._tmdb_edit.value(),
			"tagline": self._tagline_edit.text(),
			"plot": self._plot_edit.toPlainText(),
			"runtime": self._runtime_edit.value(),
			"rating": self._rating_edit.value(),
			"certification": self._certification_edit.text(),
			"director": self._director_edit.text(),
			"writer": self._writer_edit.text(),
			"studio": self._studio_edit.text(),
			"genres": self._genres_edit.text(),
			"tags": self._tags_edit.text(),
			"country": self._country_edit.text(),
			"languages": self._languages_edit.text(),
			"watched": self._watched_check.isChecked(),
		}
		return values

	#============================================
	def _is_dirty(self) -> bool:
		"""Check if any field has been modified since load (#7)."""
		current = self._get_field_values()
		return current != self._original_values

	#============================================
	def reject(self) -> None:
		"""Override reject to warn about unsaved changes (#7)."""
		if self._is_dirty():
			reply = PySide6.QtWidgets.QMessageBox.question(
				self, "Discard Changes?",
				"You have unsaved changes.\n"
				"Are you sure you want to discard them?",
				PySide6.QtWidgets.QMessageBox.StandardButton.Yes
				| PySide6.QtWidgets.QMessageBox.StandardButton.No,
			)
			yes_btn = PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			if reply != yes_btn:
				return
		super().reject()

	#============================================
	def _load_movie(self):
		"""Populate form fields from movie."""
		m = self._movie
		self._title_edit.setText(m.title)
		self._original_title_edit.setText(m.original_title)
		self._sort_title_edit.setText(m.sort_title)
		self._year_edit.setText(m.year)
		self._imdb_edit.setText(m.imdb_id)
		# set TMDB ID via spinbox (#14)
		self._tmdb_edit.setValue(m.tmdb_id if m.tmdb_id else 0)
		self._tagline_edit.setText(m.tagline)
		self._plot_edit.setText(m.plot)
		self._runtime_edit.setValue(m.runtime)
		self._rating_edit.setValue(m.rating)
		self._certification_edit.setText(m.certification)
		self._director_edit.setText(m.director)
		self._writer_edit.setText(m.writer)
		self._studio_edit.setText(m.studio)
		self._genres_edit.setText(", ".join(m.genres))
		self._tags_edit.setText(", ".join(m.tags))
		self._country_edit.setText(m.country)
		self._languages_edit.setText(m.spoken_languages)
		self._watched_check.setChecked(m.watched)

	#============================================
	def _save(self):
		"""Save edited fields back to movie and write NFO."""
		m = self._movie
		m.title = self._title_edit.text()
		m.original_title = self._original_title_edit.text()
		m.sort_title = self._sort_title_edit.text()
		m.year = self._year_edit.text()
		m.imdb_id = self._imdb_edit.text()
		# TMDB ID is now a QSpinBox, always an int (#14)
		m.tmdb_id = self._tmdb_edit.value()
		m.tagline = self._tagline_edit.text()
		m.plot = self._plot_edit.toPlainText()
		m.runtime = self._runtime_edit.value()
		m.rating = self._rating_edit.value()
		m.certification = self._certification_edit.text()
		m.director = self._director_edit.text()
		m.writer = self._writer_edit.text()
		m.studio = self._studio_edit.text()
		# parse comma-separated genres
		genres_text = self._genres_edit.text()
		m.genres = [
			g.strip() for g in genres_text.split(",") if g.strip()
		]
		# parse comma-separated tags
		tags_text = self._tags_edit.text()
		m.tags = [
			t.strip() for t in tags_text.split(",") if t.strip()
		]
		m.country = self._country_edit.text()
		m.spoken_languages = self._languages_edit.text()
		m.watched = self._watched_check.isChecked()
		# write NFO immediately (write-on-change)
		if m.nfo_path:
			nfo_path = m.nfo_path
		elif m.path:
			# derive NFO path from movie path and title
			safe_title = m.title.replace("/", "_")
			safe_title = safe_title.replace("\\", "_")
			nfo_path = os.path.join(m.path, f"{safe_title}.nfo")
		else:
			nfo_path = ""
		if nfo_path:
			moviemanager.core.nfo.writer.write_nfo(m, nfo_path)
			m.nfo_path = nfo_path
		self.accept()
