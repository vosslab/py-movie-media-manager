"""Preview pane for a selected movie search result."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import moviemanager.scraper.types
import moviemanager.ui.task_api
import moviemanager.ui.widgets.image_label
import moviemanager.ui.workers


#============================================
class SearchResultPreview(PySide6.QtWidgets.QWidget):
	"""Display a search result and load its poster in the background."""

	def __init__(
		self,
		task_api: moviemanager.ui.task_api.TaskAPI,
		parent: PySide6.QtWidgets.QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self._task_api = task_api
		self._poster_worker = None
		self._setup_ui()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the poster and metadata layout."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		layout.setContentsMargins(8, 0, 0, 0)
		self._poster_label = moviemanager.ui.widgets.image_label.ImageLabel()
		self._poster_label.setMinimumSize(180, 270)
		self._poster_label.setText("No poster")
		layout.addWidget(
			self._poster_label,
			stretch=3,
			alignment=PySide6.QtCore.Qt.AlignmentFlag.AlignTop,
		)
		self._title_label = PySide6.QtWidgets.QLabel("")
		title_font = self._title_label.font()
		title_font.setBold(True)
		title_font.setPointSize(title_font.pointSize() + 2)
		self._title_label.setFont(title_font)
		self._title_label.setWordWrap(True)
		layout.addWidget(self._title_label)
		self._year_label = PySide6.QtWidgets.QLabel("")
		layout.addWidget(self._year_label)
		self._runtime_label = PySide6.QtWidgets.QLabel("")
		layout.addWidget(self._runtime_label)
		self._overview_text = PySide6.QtWidgets.QTextEdit()
		self._overview_text.setReadOnly(True)
		self._overview_text.setMaximumHeight(150)
		self._overview_text.setFrameShape(
			PySide6.QtWidgets.QFrame.Shape.NoFrame,
		)
		layout.addWidget(self._overview_text, stretch=2)

	#============================================
	def show_result(
		self,
		result: moviemanager.scraper.types.SearchResult | None,
		poster_data: bytes | None = None,
	) -> None:
		"""Update the displayed result and begin its poster download."""
		self.cancel()
		if result is None:
			self._poster_label.setText("No poster")
			self._title_label.clear()
			self._year_label.clear()
			self._runtime_label.clear()
			self._overview_text.clear()
			return
		self._title_label.setText(result.title)
		year_text = f"Year: {result.year}" if result.year else ""
		self._year_label.setText(year_text)
		if result.runtime and result.runtime > 0:
			self._runtime_label.setText(f"Runtime: {result.runtime} min")
		else:
			self._runtime_label.clear()
		self._overview_text.setPlainText(result.overview or "")
		if not result.poster_url:
			self._poster_label.set_image_data(b"")
			return
		if poster_data is not None:
			self._poster_label.set_image_data(poster_data, source_url=result.poster_url)
			return
		self._poster_label.setText("Loading...")
		task_id = self._task_api.submit(
			moviemanager.ui.workers.download_image_bytes,
			result.poster_url,
			_priority=moviemanager.ui.task_api.PRIORITY_BACKGROUND,
		)
		worker = self._task_api.get_worker(task_id)
		worker.signals.finished.connect(
			lambda data, url=result.poster_url: self._show_poster(data, url),
		)
		worker.signals.error.connect(self._show_poster_error)
		self._poster_worker = worker

	#============================================
	def _show_poster(self, data: bytes, source_url: str) -> None:
		"""Display poster bytes returned by the current worker."""
		self._poster_worker = None
		self._poster_label.set_image_data(data, source_url=source_url)

	#============================================
	def _show_poster_error(self, error_text: str) -> None:
		"""Clear the poster after a download failure."""
		self._poster_worker = None
		self._poster_label.setText("No poster")

	#============================================
	def cancel(self) -> None:
		"""Cancel an in-flight poster request."""
		if self._poster_worker is not None:
			self._poster_worker.cancel()
			self._poster_worker = None
