"""Main movie panel with table and detail splitter."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import PySide6.QtCore

# local repo modules
import moviemanager.ui.movies.movie_table_model
import moviemanager.ui.movies.movie_detail_panel
import moviemanager.ui.widgets.search_field


#============================================
class MoviePanel(PySide6.QtWidgets.QWidget):
	"""Main movie view with search, table, and detail panel."""

	# signal emitted when the Open Folder button on empty state is clicked
	open_folder_requested = PySide6.QtCore.Signal()
	# signal emitted on double-click of a movie row
	movie_double_clicked = PySide6.QtCore.Signal()
	# signal emitted for context menu actions (action_name, movie)
	context_action = PySide6.QtCore.Signal(str, object)

	def __init__(self, parent=None):
		super().__init__(parent)
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# stacked widget to swap between empty state and content
		self._stack = PySide6.QtWidgets.QStackedWidget()
		# page 0: empty state
		self._empty_widget = self._build_empty_state()
		self._stack.addWidget(self._empty_widget)
		# page 1: content (search + splitter)
		self._content_widget = PySide6.QtWidgets.QWidget()
		self._build_content()
		self._stack.addWidget(self._content_widget)
		# show empty state by default
		self._stack.setCurrentIndex(0)
		layout.addWidget(self._stack)

	#============================================
	def _build_empty_state(self) -> PySide6.QtWidgets.QWidget:
		"""Create centered empty state with icon, label, and button."""
		widget = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QVBoxLayout(widget)
		layout.addStretch()
		# folder icon
		icon_label = PySide6.QtWidgets.QLabel()
		icon_label.setAlignment(
			PySide6.QtCore.Qt.AlignmentFlag.AlignCenter
		)
		style = self.style()
		folder_icon = style.standardIcon(
			PySide6.QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon
		)
		icon_label.setPixmap(folder_icon.pixmap(64, 64))
		layout.addWidget(icon_label)
		# instruction label
		text_label = PySide6.QtWidgets.QLabel(
			"Open a movie folder to get started"
		)
		text_label.setAlignment(
			PySide6.QtCore.Qt.AlignmentFlag.AlignCenter
		)
		# make the text slightly larger
		font = text_label.font()
		font.setPointSizeF(font.pointSizeF() * 1.3)
		text_label.setFont(font)
		layout.addWidget(text_label)
		# open folder button
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		open_btn = PySide6.QtWidgets.QPushButton("Open Folder...")
		open_btn.setIcon(folder_icon)
		open_btn.clicked.connect(self.open_folder_requested.emit)
		btn_layout.addWidget(open_btn)
		btn_layout.addStretch()
		layout.addLayout(btn_layout)
		layout.addStretch()
		return widget

	#============================================
	def _build_content(self) -> None:
		"""Build the search + table/detail splitter content page."""
		layout = PySide6.QtWidgets.QVBoxLayout(self._content_widget)
		# search field
		self._search = moviemanager.ui.widgets.search_field.SearchField()
		layout.addWidget(self._search)
		# splitter: table on left, detail on right
		self._splitter = PySide6.QtWidgets.QSplitter(
			PySide6.QtCore.Qt.Orientation.Horizontal
		)
		# table view
		self._table_view = PySide6.QtWidgets.QTableView()
		self._table_model = (
			moviemanager.ui.movies.movie_table_model.MovieTableModel()
		)
		self._table_view.setModel(self._table_model)
		self._table_view.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionBehavior.SelectRows
		)
		self._table_view.setSelectionMode(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionMode.ExtendedSelection
		)
		self._table_view.setSortingEnabled(True)
		# hide row numbers and fix row heights
		v_header = self._table_view.verticalHeader()
		v_header.setVisible(False)
		v_header.setSectionResizeMode(
			PySide6.QtWidgets.QHeaderView.ResizeMode.Fixed
		)
		# derive fixed row height from font metrics + padding
		font_height = self._table_view.fontMetrics().height()
		v_header.setDefaultSectionSize(font_height + 8)
		# allow user to manually resize columns (#17)
		header = self._table_view.horizontalHeader()
		header.setStretchLastSection(True)
		header.setSectionResizeMode(
			PySide6.QtWidgets.QHeaderView.ResizeMode.Interactive
		)
		# right-click context menu
		self._table_view.setContextMenuPolicy(
			PySide6.QtCore.Qt.ContextMenuPolicy.CustomContextMenu
		)
		self._table_view.customContextMenuRequested.connect(
			self._show_context_menu
		)
		# double-click to edit
		self._table_view.doubleClicked.connect(
			self._on_double_click
		)
		self._splitter.addWidget(self._table_view)
		# detail panel
		self._detail = (
			moviemanager.ui.movies.movie_detail_panel.MovieDetailPanel()
		)
		self._splitter.addWidget(self._detail)
		# set splitter sizes (60% table, 40% detail)
		self._splitter.setSizes([600, 400])
		layout.addWidget(self._splitter)
		# connect signals
		self._search.filter_changed.connect(self._on_filter)
		selection_model = self._table_view.selectionModel()
		selection_model.currentRowChanged.connect(
			self._on_row_changed
		)

	#============================================
	def set_movies(self, movies: list) -> None:
		"""Load movies into the table and switch to content view."""
		self._table_model.set_movies(movies)
		# auto-resize columns to fit content
		self._table_view.resizeColumnsToContents()
		# switch from empty state to content
		self._stack.setCurrentIndex(1)

	#============================================
	def get_selected_movie(self):
		"""Get the currently selected movie."""
		index = self._table_view.currentIndex()
		if index.isValid():
			movie = self._table_model.get_movie(index.row())
			return movie
		return None

	#============================================
	def check_all(self) -> None:
		"""Check all movies in the table."""
		self._table_model.check_all()

	#============================================
	def uncheck_all(self) -> None:
		"""Uncheck all movies in the table."""
		self._table_model.uncheck_all()

	#============================================
	def check_unscraped(self) -> None:
		"""Check only unscraped movies."""
		self._table_model.check_unscraped()

	#============================================
	def get_checked_movies(self) -> list:
		"""Return list of checked Movie objects."""
		return self._table_model.get_checked_movies()

	#============================================
	def get_checked_count(self) -> int:
		"""Return number of checked rows."""
		return self._table_model.get_checked_count()

	#============================================
	def focus_search(self) -> None:
		"""Set focus to the search/filter field."""
		if self._stack.currentIndex() == 1:
			self._search.setFocus()
			self._search.selectAll()

	#============================================
	def clear_filter(self) -> None:
		"""Clear the search filter text."""
		if self._stack.currentIndex() == 1:
			self._search.clear()

	#============================================
	def _on_filter(self, text: str) -> None:
		"""Apply search filter."""
		self._table_model.set_filter(text)

	#============================================
	def _on_row_changed(self, current, previous) -> None:
		"""Update detail panel when selection changes."""
		movie = self._table_model.get_movie(current.row())
		self._detail.set_movie(movie)

	#============================================
	def _on_double_click(self, index) -> None:
		"""Emit double-click signal for editing."""
		if index.isValid():
			self.movie_double_clicked.emit()

	#============================================
	def _show_context_menu(self, pos) -> None:
		"""Show right-click context menu on the table."""
		index = self._table_view.indexAt(pos)
		if not index.isValid():
			return
		movie = self._table_model.get_movie(index.row())
		if not movie:
			return
		menu = PySide6.QtWidgets.QMenu(self)
		# workflow actions
		scrape_action = menu.addAction("Scrape")
		edit_action = menu.addAction("Edit")
		rename_action = menu.addAction("Rename")
		menu.addSeparator()
		finder_action = menu.addAction("Show in Finder")
		# execute menu and handle result
		action = menu.exec(
			self._table_view.viewport().mapToGlobal(pos)
		)
		if action == scrape_action:
			self.context_action.emit("scrape", movie)
		elif action == edit_action:
			self.context_action.emit("edit", movie)
		elif action == rename_action:
			self.context_action.emit("rename", movie)
		elif action == finder_action:
			# open movie directory in system file manager
			if movie.path:
				PySide6.QtGui.QDesktopServices.openUrl(
					PySide6.QtCore.QUrl.fromLocalFile(movie.path)
				)

	#============================================
	def save_table_state(self, settings) -> None:
		"""Save column widths and sort state to QSettings."""
		header = self._table_view.horizontalHeader()
		settings.setValue("movieTable/headerState", header.saveState())
		settings.setValue(
			"movieTable/sortColumn",
			header.sortIndicatorSection()
		)
		settings.setValue(
			"movieTable/sortOrder",
			int(header.sortIndicatorOrder())
		)

	#============================================
	def restore_table_state(self, settings) -> None:
		"""Restore column widths and sort state from QSettings."""
		header_state = settings.value("movieTable/headerState")
		if header_state:
			self._table_view.horizontalHeader().restoreState(
				header_state
			)
		sort_col = settings.value("movieTable/sortColumn")
		sort_order = settings.value("movieTable/sortOrder")
		if sort_col is not None and sort_order is not None:
			self._table_view.horizontalHeader().setSortIndicator(
				int(sort_col),
				PySide6.QtCore.Qt.SortOrder(int(sort_order))
			)
