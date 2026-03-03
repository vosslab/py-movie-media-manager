"""Main movie panel with table and detail splitter."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import PySide6.QtCore

# local repo modules
import moviemanager.ui.movies.movie_table_model
import moviemanager.ui.movies.movie_detail_panel
import moviemanager.ui.movies.status_delegate
import moviemanager.ui.widgets.search_field

# full display names for column chooser menu items
_COLUMN_DISPLAY_NAMES = {
	"Title": "Title",
	"Year": "Year",
	"Rating": "Rating",
	"Mtch": "Matched",
	"Org": "Organized",
	"Art": "Artwork",
	"Sub": "Subtitles",
	"Trl": "Trailer",
	"S&N": "Sex & Nudity",
	"V&G": "Violence & Gore",
	"Prof": "Profanity",
	"A&D": "Alcohol, Drugs & Smoking",
	"F&I": "Frightening & Intense Scenes",
}


#============================================
class MoviePanel(PySide6.QtWidgets.QWidget):
	"""Main movie view with search, table, and detail panel."""

	# signal emitted when the Open Folder button on empty state is clicked
	open_folder_requested = PySide6.QtCore.Signal()
	# signal emitted on double-click of a movie row
	movie_double_clicked = PySide6.QtCore.Signal()
	# signal emitted for context menu actions (action_name, movie)
	context_action = PySide6.QtCore.Signal(str, object)
	# signal emitted when check state changes (checked, total)
	checked_changed = PySide6.QtCore.Signal(int, int)

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
		# selection buttons row
		sel_layout = PySide6.QtWidgets.QHBoxLayout()
		sel_all_btn = PySide6.QtWidgets.QPushButton("Select All")
		sel_all_btn.setMaximumWidth(100)
		sel_all_btn.clicked.connect(self.check_all)
		sel_layout.addWidget(sel_all_btn)
		sel_none_btn = PySide6.QtWidgets.QPushButton("Select None")
		sel_none_btn.setMaximumWidth(100)
		sel_none_btn.clicked.connect(self.uncheck_all)
		sel_layout.addWidget(sel_none_btn)
		sel_unmatched_btn = PySide6.QtWidgets.QPushButton(
			"Select Unmatched"
		)
		sel_unmatched_btn.setMaximumWidth(130)
		sel_unmatched_btn.clicked.connect(self.check_unscraped)
		sel_layout.addWidget(sel_unmatched_btn)
		sel_layout.addStretch()
		layout.addLayout(sel_layout)
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
		# install icon delegates on status columns 4-8 (D, N, A, S, T)
		for col in range(4, 9):
			icon_del = moviemanager.ui.movies.status_delegate.StatusIconDelegate(
				self._table_view
			)
			self._table_view.setItemDelegateForColumn(col, icon_del)
		# install severity delegates on PG columns 9-13 (SN, VG, Pr, AD, FI)
		for col in range(9, 14):
			sev_del = moviemanager.ui.movies.status_delegate.SeverityDelegate(
				self._table_view
			)
			self._table_view.setItemDelegateForColumn(col, sev_del)
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
		# column sizing: Title stretches, all others resize to contents
		header = self._table_view.horizontalHeader()
		header.setStretchLastSection(False)
		header.setSectionResizeMode(
			PySide6.QtWidgets.QHeaderView.ResizeMode.Interactive
		)
		# checkbox column: fit to contents
		header.setSectionResizeMode(
			0, PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents
		)
		# Title column absorbs remaining space
		header.setSectionResizeMode(
			1, PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch
		)
		# Year and Rating: fit to contents
		header.setSectionResizeMode(
			2, PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents
		)
		header.setSectionResizeMode(
			3, PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents
		)
		# status icon columns 4-8 and PG columns 9-13: fit to contents
		for col_idx in range(4, 14):
			header.setSectionResizeMode(
				col_idx,
				PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
			)
		# right-click context menu on header for column chooser
		header.setContextMenuPolicy(
			PySide6.QtCore.Qt.ContextMenuPolicy.CustomContextMenu
		)
		header.customContextMenuRequested.connect(
			self._show_header_context_menu
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
		# forward checked_changed from model to panel signal
		self._table_model.checked_changed.connect(
			self.checked_changed.emit
		)

	#============================================
	def set_movies(self, movies: list) -> None:
		"""Load movies into the table and switch to content view."""
		was_empty = self._table_model.rowCount() == 0
		self._table_model.set_movies(movies)
		# switch from empty state to content
		self._stack.setCurrentIndex(1)
		# auto-select first row only on initial load (not refresh)
		if movies and was_empty:
			first_index = self._table_model.index(0, 1)
			self._table_view.setCurrentIndex(first_index)

	#============================================
	def refresh_data(self) -> None:
		"""Refresh displayed data without resetting the model.

		Preserves selection, scroll position, and checked state.
		Use after metadata updates (scrape, edit, rename, download).
		"""
		self._table_model.refresh()
		# refresh the detail panel for the current selection
		current = self._table_view.currentIndex()
		if current.isValid():
			movie = self._table_model.get_movie(current.row())
			self._detail.set_movie(movie)

	#============================================
	def append_movies(self, movies: list) -> None:
		"""Append movies incrementally without resetting the table.

		Switches from empty state to content view on first batch.

		Args:
			movies: List of Movie objects to append.
		"""
		self._table_model.append_movies(movies)
		# switch to content view on first batch
		if self._stack.currentIndex() == 0:
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
	def get_selected_movies(self) -> list:
		"""Return list of Movie objects for all selected rows.

		Uses the table view's selection model to find rows selected
		via Shift-click or Cmd-click (ExtendedSelection mode).

		Returns:
			List of Movie objects for all selected rows.
		"""
		selection = self._table_view.selectionModel()
		selected_rows = selection.selectedRows()
		movies = []
		for index in selected_rows:
			movie = self._table_model.get_movie(index.row())
			if movie:
				movies.append(movie)
		return movies

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
		# workflow actions (3-step pipeline)
		match_action = menu.addAction("Match")
		edit_action = menu.addAction("Edit")
		organize_action = menu.addAction("Organize")
		download_action = menu.addAction("Download")
		menu.addSeparator()
		finder_action = menu.addAction("Show in Finder")
		# execute menu and handle result
		action = menu.exec(
			self._table_view.viewport().mapToGlobal(pos)
		)
		if action == match_action:
			self.context_action.emit("scrape", movie)
		elif action == edit_action:
			self.context_action.emit("edit", movie)
		elif action == organize_action:
			self.context_action.emit("rename", movie)
		elif action == download_action:
			self.context_action.emit("download", movie)
		elif action == finder_action:
			# open movie directory in system file manager
			if movie.path:
				PySide6.QtGui.QDesktopServices.openUrl(
					PySide6.QtCore.QUrl.fromLocalFile(movie.path)
				)

	#============================================
	def _show_header_context_menu(self, pos) -> None:
		"""Show column chooser context menu on header right-click."""
		header = self._table_view.horizontalHeader()
		menu = PySide6.QtWidgets.QMenu(self)
		columns = moviemanager.ui.movies.movie_table_model.COLUMNS
		# columns that cannot be hidden (Title + status indicators)
		locked_columns = {1, 4, 5, 6, 7, 8}
		# skip col 0 (checkbox) -- always visible
		for col_idx in range(1, len(columns)):
			if col_idx in locked_columns:
				continue
			col_key = columns[col_idx]
			display_name = _COLUMN_DISPLAY_NAMES.get(col_key, col_key)
			action = menu.addAction(display_name)
			action.setCheckable(True)
			# column is visible when not hidden
			is_visible = not header.isSectionHidden(col_idx)
			action.setChecked(is_visible)
			# connect toggle to show/hide the column
			action.toggled.connect(
				lambda checked, c=col_idx: self._toggle_column(c, checked)
			)
		menu.exec(header.mapToGlobal(pos))

	#============================================
	def _toggle_column(self, col_idx: int, visible: bool) -> None:
		"""Show or hide a table column.

		Args:
			col_idx: Column index to toggle.
			visible: True to show, False to hide.
		"""
		self._table_view.setColumnHidden(col_idx, not visible)

	#============================================
	def save_table_state(self, settings) -> None:
		"""Save column widths, sort state, and visibility to QSettings."""
		header = self._table_view.horizontalHeader()
		settings.setValue("movieTable/headerState", header.saveState())
		settings.setValue(
			"movieTable/sortColumn",
			header.sortIndicatorSection()
		)
		settings.setValue(
			"movieTable/sortOrder",
			header.sortIndicatorOrder().value,
		)
		# save visible columns list
		columns = moviemanager.ui.movies.movie_table_model.COLUMNS
		visible = []
		for col_idx in range(1, len(columns)):
			if not header.isSectionHidden(col_idx):
				visible.append(columns[col_idx])
		settings.setValue("movieTable/visibleColumns", visible)

	#============================================
	def restore_table_state(self, settings) -> None:
		"""Restore column widths, sort state, and visibility from QSettings."""
		# columns that must always be visible (Title + status indicators)
		locked_columns = {1, 4, 5, 6, 7, 8}
		header_state = settings.value("movieTable/headerState")
		if header_state:
			self._table_view.horizontalHeader().restoreState(
				header_state
			)
			# re-apply resize modes after restoring state to prevent
			# stale QSettings from giving flex size to wrong columns
			header = self._table_view.horizontalHeader()
			header.setSectionResizeMode(
				0, PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents
			)
			header.setSectionResizeMode(
				1, PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch
			)
			for fix_col in range(2, header.count()):
				header.setSectionResizeMode(
					fix_col,
					PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
				)
			# force locked columns visible after restoreState in case
			# stale QSettings hid columns that were renamed
			for col_idx in locked_columns:
				self._table_view.setColumnHidden(col_idx, False)
		sort_col = settings.value("movieTable/sortColumn")
		sort_order = settings.value("movieTable/sortOrder")
		if sort_col is not None and sort_order is not None:
			self._table_view.horizontalHeader().setSortIndicator(
				int(sort_col),
				PySide6.QtCore.Qt.SortOrder(int(sort_order))
			)
		# restore column visibility from saved settings
		visible_cols = settings.value("movieTable/visibleColumns")
		if visible_cols is not None:
			columns = moviemanager.ui.movies.movie_table_model.COLUMNS
			for col_idx in range(1, len(columns)):
				# locked columns are always shown regardless of saved state
				if col_idx in locked_columns:
					self._table_view.setColumnHidden(col_idx, False)
					continue
				col_key = columns[col_idx]
				is_visible = col_key in visible_cols
				self._table_view.setColumnHidden(col_idx, not is_visible)
